//> using scala 2.12.18
//> using dep org.scorexfoundation::sigma-state:6.0.7

// Probe for the EKB page "Settled semantics at tree version 3 (Sigma 6.0)".
//
// Each case is a small script compiled with the sigma-state 6.0.7 compiler and reduced with the stock 6.0.7
// interpreter (fullReduction, the reduction a node runs). The spent box has no data inputs and one output, so
// `CONTEXT.dataInputs(0)` throws whenever it is evaluated. A case prints what happened; nothing is inferred.
//
// The path selector is always in R4, so registers stay densely packed; the register under test is R5.
//
// Every hoisting case runs twice: activated version 3 with a version 3 tree, and activated version 2 with a
// version 0 tree (the control: the settings the earlier fleet-sdk results were taken under).
//
// Run:  scala-cli --power run --server=false Probe.scala -- [ergo headers file] [yolo headers file]
// Header files hold one header per line: "<height> <id hex> <header bytes hex> ...". They are optional.

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

  var agree = 0; var differ = 0
  // `rule` is what the version 0/1 page says should happen: "runs" (the bad read is evaluated, so the script
  // throws) or "skipped" (it is not, so the script returns a value).
  def hoist(name: String, rule: String, src: String, regs: Regs): Unit = {
    val v3 = run(src, regs, 3, 3); val v0 = run(src, regs, 2, 0)
    def seen(r: String) = if (r.startsWith("THROWS")) "runs" else "skipped"
    val ok = seen(v3) == rule
    if (ok) agree += 1 else differ += 1
    println(f"${if (ok) "AGREES " else "DIFFERS"} | $name%-64s | rule: $rule%-7s | v3: ${seen(v3)}%-7s ($v3) | v0: ${seen(v0)}%-7s ($v0)")
  }
  def fact(name: String, got: String): Unit = println(f"FACT    | $name%-64s | $got")

  def main(args: Array[String]): Unit = {
    val B = "CONTEXT.dataInputs(0).value"   // throws when evaluated: the transaction has no data inputs
    def c(n: Int): Regs = Map(R4 -> IntConstant(n))
    val pk = SigmaPropConstant(ProveDlog(CryptoConstants.dlogGroup.generator))

    println("== 1. Not evaluated unless reached ==")
    hoist("if arm not taken (run-time condition)", "skipped", s"{ sigmaProp(if (SELF.R4[Int].get == 1) $B > 0L else true) }", c(0))
    hoist("if arm taken (control: the read does throw)", "runs", s"{ sigmaProp(if (SELF.R4[Int].get == 1) $B > 0L else true) }", c(1))
    hoist("if arm not taken (constant condition)", "skipped", s"{ sigmaProp(if (false) $B > 0L else true) }", c(0))
    hoist("&& right side, left is false", "skipped", s"{ sigmaProp(SELF.R4[Int].get == 1 && $B > 0L) }", c(0))
    hoist("|| right side, left is true", "skipped", s"{ sigmaProp(SELF.R4[Int].get == 0 || $B > 0L) }", c(0))
    hoist("def body, function not called on this path", "skipped", s"{ def f(x: Long) = $B > x; sigmaProp(if (SELF.R4[Int].get == 1) f(0L) else true) }", c(0))
    hoist("lambda body, lambda not called on this path", "skipped", s"{ val f = { (x: Long) => $B > x }; sigmaProp(if (SELF.R4[Int].get == 1) f(0L) else true) }", c(0))

    println("\n== 2. Where a val lands ==")
    hoist("val outside, used in two if arms, neither taken", "runs",
      s"{ val d = $B; val k = SELF.R4[Int].get; sigmaProp(if (k == 1) d > 0L else if (k == 2) d > 1L else true) }", c(3))
    hoist("val outside, used in an if arm and a || right side", "runs",
      s"{ val d = $B; val k = SELF.R4[Int].get; sigmaProp((if (k == 1) d > 0L else true) && (k == 3 || d > 1L)) }", c(3))
    hoist("val outside, used on both sides of && inside one arm", "runs",
      s"{ val d = $B; sigmaProp(if (SELF.R4[Int].get == 1) (d > 0L && d < 10L) else true) }", c(0))
    hoist("  same, both uses through the same sub-expression", "skipped",
      s"{ val b = CONTEXT.dataInputs(0); sigmaProp(if (SELF.R4[Int].get == 1) (b.value > 0L && b.value < 10L) else true) }", c(0))
    hoist("val outside, used once, in an arm not taken", "skipped",
      s"{ val d = $B; sigmaProp(if (SELF.R4[Int].get == 1) d > 0L else true) }", c(0))
    hoist("val declared inside the arm, used twice there", "skipped",
      s"{ sigmaProp(if (SELF.R4[Int].get == 1) { val d = $B; d > 0L && d < 10L } else true) }", c(0))
    hoist("val never used", "skipped", s"{ val d = $B; sigmaProp(SELF.R4[Int].get == 0) }", c(0))
    hoist("same read written inline in two arms, neither taken", "skipped",
      s"{ val k = SELF.R4[Int].get; sigmaProp(if (k == 1) $B > 0L else if (k == 2) $B > 1L else true) }", c(3))

    println("\n== 3. Only the hoisted part runs ==")
    val optSrc = "{ val o = SELF.R5[Int]; val k = SELF.R4[Int].get; sigmaProp(if (k == 1) o.get > 0 else if (k == 2) o.get > 1 else true) }"
    val getSrc = "{ val r = SELF.R5[Int].get; val k = SELF.R4[Int].get; sigmaProp(if (k == 1) r > 0 else if (k == 2) r > 1 else true) }"
    hoist("hoisted `val o = SELF.R5[Int]`, R5 absent", "skipped", optSrc, c(3))
    hoist("hoisted `val o = SELF.R5[Int]`, R5 holds a Long", "runs", optSrc, c(3) + (R5 -> LongConstant(7L)))
    hoist("hoisted `val r = SELF.R5[Int].get`, R5 absent", "runs", getSrc, c(3))
    hoist("hoisted `val r = SELF.R5[Int].get`, R5 holds a Long", "runs", getSrc, c(3) + (R5 -> LongConstant(7L)))

    println("\n== 4. anyOf / allOf ==")
    hoist("anyOf(Coll(true, bad read))", "runs", s"{ sigmaProp(anyOf(Coll(SELF.R4[Int].get == 0, $B > 0L))) }", c(0))
    hoist("allOf(Coll(false, bad read))", "runs", s"{ sigmaProp(allOf(Coll(SELF.R4[Int].get == 1, $B > 0L))) }", c(0))

    println("\n== 6. Sigma-level OR ==")
    hoist("key || sigmaProp(bad read)", "runs", s"{ SELF.R5[SigmaProp].get || sigmaProp($B > 0L) }", c(0) + (R5 -> pk))
    hoist("key || sigmaProp(if (not taken) bad read else true)", "skipped",
      s"{ SELF.R5[SigmaProp].get || sigmaProp(if (SELF.R4[Int].get == 1) $B > 0L else true) }", c(0) + (R5 -> pk))

    println("\n== Fail-closed arithmetic and register reads (\"runs\" = throws) ==")
    hoist("Coll index out of range", "runs", "{ sigmaProp(SELF.tokens(0)._2 > 0L) }", c(0))
    hoist("  same behind a tokens.size guard", "skipped", "{ sigmaProp(SELF.tokens.size > 0 && SELF.tokens(0)._2 > 0L) }", c(0))
    hoist("Long * Long overflow", "runs", "{ sigmaProp(SELF.R5[Long].get * SELF.R5[Long].get > 0L) }", c(0) + (R5 -> LongConstant(Long.MaxValue)))
    hoist("  same product taken .toBigInt first", "skipped", "{ sigmaProp(SELF.R5[Long].get.toBigInt * SELF.R5[Long].get.toBigInt > 0.toBigInt) }", c(0) + (R5 -> LongConstant(Long.MaxValue)))
    hoist("BigInt division by zero", "runs", "{ sigmaProp(SELF.R5[Long].get.toBigInt / (SELF.R4[Int].get.toBigInt) > 0.toBigInt) }", c(0) + (R5 -> LongConstant(5L)))
    hoist("R5[Int].getOrElse(0), R5 absent", "skipped", "{ sigmaProp(SELF.R5[Int].getOrElse(0) == 0) }", c(0))
    hoist("R5[Int].getOrElse(0), R5 holds a Long", "runs", "{ sigmaProp(SELF.R5[Int].getOrElse(0) == 0) }", c(0) + (R5 -> LongConstant(7L)))
    println(s"\nagrees with the version 0/1 rule at version 3: $agree; differs: $differ")

    println("\n== Sigma 6.0 methods (activated version 3, tree version 3) ==")
    val nb = 104330148L
    val d = NBitsUtils.decodeCompactBits(nb)
    fact(s"Global.decodeNbits($nb) == $d (the difficulty)",
      run("{ sigmaProp(Global.decodeNbits(" + nb + "L) == bigInt(\"" + d + "\")) }", Map(), 3, 3))
    fact("a 6.0 method in a version 0 tree under activated version 2", run(s"{ sigmaProp(Global.decodeNbits(${nb}L) > 0.toBigInt) }", Map(), 2, 0))
    def headers(path: String) = Source.fromFile(path).getLines().filter(_.trim.nonEmpty).map(_.trim.split(" ")).map(a => (a(0), a(1), a(2))).toVector.distinct
    def headerFacts(label: String, path: String): Unit = for ((h, id, bytes) <- headers(path)) {
      val vars = Map[Byte, EvaluatedValue[_ <: SType]](1.toByte -> ByteArrayConstant(unhex(bytes)), 2.toByte -> ByteArrayConstant(unhex(id)))
      fact(s"$label header $h: deserializeTo[Header](bytes).checkPow",
        run("{ sigmaProp(Global.deserializeTo[Header](getVar[Coll[Byte]](1).get).checkPow) }", Map(), 3, 3, vars))
      fact(s"$label header $h: blake2b256(bytes) == stated id == header.id",
        run("{ val b = getVar[Coll[Byte]](1).get; val i = getVar[Coll[Byte]](2).get; sigmaProp(blake2b256(b) == i && Global.deserializeTo[Header](b).id == i) }", Map(), 3, 3, vars))
    }
    if (args.length > 0) headerFacts("Ergo mainnet", args(0))
    if (args.length > 1) headerFacts("YOLO test chain", args(1))
  }
}
