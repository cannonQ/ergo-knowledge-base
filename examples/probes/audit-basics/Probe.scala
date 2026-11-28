//> using scala 2.12.18
//> using dep org.scorexfoundation::sigma-state:6.0.7

// Probe for three points in the EKB audit context: positional box indexes out of range, a literal
// `sigmaProp(true)`, and the library's box and script size constants.
//
// Each case is a small script compiled with the sigma-state 6.0.7 compiler and reduced with the stock 6.0.7
// interpreter (fullReduction, the reduction a node runs). The transaction has ONE input (SELF), ONE output and
// no data inputs. R4 holds an Int selector and R5 a public key. A case prints what happened; nothing is inferred.
//
// Every case runs twice: activated version 3 with a version 3 tree, and activated version 2 with a version 0 tree.
// Results: "true" (spendable by anyone), "false", "sigma" (a signature is still needed), "THROWS ..." (script fails).
//
// Run:  scala-cli --power run --server=false Probe.scala

import org.ergoplatform._
import org.ergoplatform.ErgoBox.{NonMandatoryRegisterId, R4, R5}
import scorex.crypto.hash.Blake2b256
import sigma.{Coll, Colls, Header, VersionContext}
import sigma.ast._
import sigma.ast.syntax._
import sigma.compiler.SigmaCompiler
import sigma.compiler.ir.CompiletimeIRContext
import sigma.crypto.CryptoConstants
import sigma.data.{AvlTreeData, CSigmaDslBuilder, ProveDlog, TrivialProp}
import sigma.interpreter.ContextExtension
import sigma.util.NBitsUtils
import sigmastate.eval.CPreHeader
import scala.io.Source
import scala.util.{Failure, Success, Try}

object Probe {
  type Regs = Map[NonMandatoryRegisterId, EvaluatedValue[_ <: SType]]
  val G = CSigmaDslBuilder
  def unhex(s: String): Array[Byte] = s.grouped(2).map(Integer.parseInt(_, 16).toByte).toArray
  def coll(b: Array[Byte]): Coll[Byte] = Colls.fromArray(b)

  def compile(src: String, treeVersion: Int): ErgoTree = {
    val compiler = SigmaCompiler(ErgoAddressEncoder.TestnetNetworkPrefix)
    implicit val ir: CompiletimeIRContext = new CompiletimeIRContext
    val prop = compiler.compile(Map.empty, src).buildTree.asSigmaProp
    ErgoTree.fromProposition(ErgoTree.headerWithVersion(ErgoTree.ZeroHeader, treeVersion.toByte), prop)
  }

  // Compile and reduce one script. Returns "true", "false", "sigma" (needs a signature) or "THROWS <why>".
  def run(src: String, regs: Regs, activated: Int, treeVersion: Int,
          vars: Map[Byte, EvaluatedValue[_ <: SType]] = Map.empty): String =
    VersionContext.withVersions(activated.toByte, treeVersion.toByte) {
      Try {
        val tree = compile(src, treeVersion)
        val txId = scorex.util.bytesToId(Blake2b256("probe tx".getBytes))
        val none = Colls.emptyColl[(sigma.data.Digest32Coll, Long)]
        val self = new ErgoBox(1000000000L, tree, none, regs, txId, 0.toShort, 100)
        val ext = ContextExtension(vars)
        val out = new ErgoBoxCandidate(self.value, tree, 1000, none, Map())
        val tx = new UnsignedErgoLikeTransaction(IndexedSeq(new UnsignedInput(self.id, ext)), IndexedSeq(), IndexedSeq(out))
        val pre = CPreHeader(4.toByte, coll(new Array[Byte](32)), 1700000000000L, 100000000L, 1000,
          G.groupGenerator, coll(new Array[Byte](3)))
        val ctx = new ErgoLikeContext(AvlTreeData.dummy, Colls.emptyColl[Header](sigma.HeaderRType), pre, IndexedSeq(),
          IndexedSeq(self), tx, 0, ext, org.ergoplatform.validation.ValidationRules.currentSettings, 1000000L, 0L, activated.toByte)
        val interp = new ErgoLikeInterpreter() { override type CTX = ErgoLikeContext }
        interp.fullReduction(tree, ctx).value
      } match {
        case Success(TrivialProp.TrueProp) => "true"
        case Success(TrivialProp.FalseProp) => "false"
        case Success(_) => "sigma"
        case Failure(e) =>
          val root = Iterator.iterate[Throwable](e)(_.getCause).takeWhile(_ != null).toList.last
          "THROWS " + root.getClass.getSimpleName + " " + Option(root.getMessage).getOrElse("").replace('\n', ' ').take(60)
      }
    }


  def both(name: String, src: String, regs: Regs): Unit =
    println(f"$name%-66s | v3: ${run(src, regs, 3, 3)}%-58s | v0: ${run(src, regs, 2, 0)}")

  def main(args: Array[String]): Unit = {
    val pk = SigmaPropConstant(ProveDlog(CryptoConstants.dlogGroup.generator))
    def r(n: Int): Regs = Map(R4 -> IntConstant(n), R5 -> pk)

    println("== 1. Positional box index out of range (one input, one output, no data inputs) ==")
    both("OUTPUTS(0) (control: exists)", "{ sigmaProp(OUTPUTS(0).value > 0L) }", r(0))
    both("OUTPUTS(1)", "{ sigmaProp(OUTPUTS(1).value > 0L) }", r(0))
    both("INPUTS(1)", "{ sigmaProp(INPUTS(1).value > 0L) }", r(0))
    both("CONTEXT.dataInputs(0)", "{ sigmaProp(CONTEXT.dataInputs(0).value > 0L) }", r(0))
    both("OUTPUTS.size > 1 && OUTPUTS(1) ...", "{ sigmaProp(OUTPUTS.size > 1 && OUTPUTS(1).value > 0L) }", r(0))
    both("key || sigmaProp(OUTPUTS(1) ...)", "{ SELF.R5[SigmaProp].get || sigmaProp(OUTPUTS(1).value > 0L) }", r(0))
    both("key || sigmaProp(OUTPUTS.size > 1 && OUTPUTS(1) ...)", "{ SELF.R5[SigmaProp].get || sigmaProp(OUTPUTS.size > 1 && OUTPUTS(1).value > 0L) }", r(0))

    println("\n== 2. Literal sigmaProp(true) and sigmaProp(false) ==")
    both("key alone (control)", "{ SELF.R5[SigmaProp].get }", r(0))
    both("sigmaProp(true)", "{ sigmaProp(true) }", r(0))
    both("key || sigmaProp(true)", "{ SELF.R5[SigmaProp].get || sigmaProp(true) }", r(0))
    both("key && sigmaProp(true)", "{ SELF.R5[SigmaProp].get && sigmaProp(true) }", r(0))
    both("key || sigmaProp(false)", "{ SELF.R5[SigmaProp].get || sigmaProp(false) }", r(0))
    both("key && sigmaProp(false)", "{ SELF.R5[SigmaProp].get && sigmaProp(false) }", r(0))
    both("key || sigmaProp(R4 == 0), R4 is 0", "{ SELF.R5[SigmaProp].get || sigmaProp(SELF.R4[Int].get == 0) }", r(0))
    both("key || sigmaProp(R4 == 0), R4 is 1", "{ SELF.R5[SigmaProp].get || sigmaProp(SELF.R4[Int].get == 0) }", r(1))
    both("if (R4 == 0) sigmaProp(true) else key, R4 is 0", "{ if (SELF.R4[Int].get == 0) sigmaProp(true) else SELF.R5[SigmaProp].get }", r(0))

    println("\n== 3. Size constants in sigma-state 6.0.7 (read from the library, not enforced by this probe) ==")
    println("SigmaConstants.MaxBoxSize            = " + sigma.data.SigmaConstants.MaxBoxSize.value)
    println("SigmaConstants.MaxPropositionBytes   = " + sigma.data.SigmaConstants.MaxPropositionBytes.value)
    println("SigmaConstants.MaxTokens             = " + sigma.data.SigmaConstants.MaxTokens.value)
    println("SigmaConstants.MaxBoxSizeWithoutRefs = " + sigma.data.SigmaConstants.MaxBoxSizeWithoutRefs.value)
  }
}
