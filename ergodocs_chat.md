## Below is a “working vocabulary” of the most common terms you’ll see in the Ergo ecosystem, grouped by theme, with why each matters. I’m focusing on concepts that show up repeatedly in Ergo docs and in real dApp / wallet / node usage.

1) Ledger & state model (how Ergo represents value and contract state)
eUTXO (Extended UTXO)

    What it is: Ergo uses the extended UTXO model , where each unspent output (a “box”) can carry arbitrary data and be protected by an arbitrary spending predicate (script).
    Why it matters: This is the foundation for Ergo’s smart contracts while keeping UTXO benefits like parallel validation , clear state transitions, and strong composability via transaction chaining.
    Docs: https://docs.ergoplatform.com/dev/protocol/eutxo/

Box

    What it is: Ergo’s UTXO object. Transactions consume existing boxes and create new boxes.
    Why it matters: In Ergo, “state” for contracts and tokens is represented as boxes. If you understand boxes, you understand how Ergo dApps “store” and “update” state.
    Docs: https://docs.ergoplatform.com/dev/data-model/box/

Registers (R0–R9)

    What it is: A box is “made of registers.” Key ones:
        R0: nanoERG value
        R1: guarding script (contract)
        R2: tokens (tokenId → amount pairs)
        R3: creation info (height, tx id, output index)
        R4–R9: optional, arbitrary user-defined data
    Why it matters: Registers are how contracts carry parameters, identifiers, oracle values, pool state, etc., without needing global mutable storage.
    Docs: https://docs.ergoplatform.com/dev/data-model/box/registers/

Transaction (Tx)

    What it is: An atomic state transition: consumes input boxes, produces output boxes, and must satisfy each input’s guarding script.
    Why it matters: All contract “execution” happens by spending boxes; there’s no background process or global contract storage like account-based chains.
    Docs: https://docs.ergoplatform.com/dev/protocol/transactions/

Data Inputs (read-only inputs)

    What it is: Boxes referenced by a transaction without being spent , used as read-only data sources.
    Why it matters: This is a key enabler for efficient patterns like oracle pools , shared configuration boxes, and referencing state without contention.
    Docs: https://docs.ergoplatform.com/dev/protocol/tx/read-only-inputs/

2) Smart contracts & scripting (how spending conditions are expressed)
ErgoScript

    What it is: Ergo’s high-level smart contract language used to define a box’s spending condition.
    Why it matters: It’s the primary way developers express contract logic; it’s designed to be predictable and safe in a UTXO setting.
    Docs: https://docs.ergoplatform.com/dev/scs/ergoscript/

ErgoTree

    What it is: The lower-level serialized form of a contract that nodes actually store and evaluate (ErgoScript compiles to ErgoTree).
    Why it matters: When you interact with addresses, scripts, and on-chain validation, you’re often dealing with ErgoTree under the hood.
    Docs: https://docs.ergoplatform.com/dev/scs/ergotree/

Sigma protocols / SigmaProp

    What it is: The cryptographic foundation for many spending conditions (proofs of knowledge, signature-like statements, and composable logic).
    Why it matters: Enables expressive authorization (multisig, threshold, complex conditions) and underpins privacy-oriented constructions.
    Docs: https://docs.ergoplatform.com/dev/scs/sigma/

Multi-stage contracts (multi-stage transactions)

    What it is: A design pattern where complex behavior is achieved by chaining transactions and evolving boxes across stages.
    Why it matters: This is how Ergo can implement very sophisticated applications while keeping the base scripting model constrained and verifiable.
    Docs: https://docs.ergoplatform.com/dev/scs/multi/

3) Consensus, mining, and monetary mechanics
Autolykos (PoW)

    What it is: Ergo’s Proof-of-Work consensus algorithm (Autolykos), designed to be efficient and ASIC-resistant (GPU-friendly).
    Why it matters: It defines how blocks are produced and how the network stays decentralized in mining participation.
    Docs: https://docs.ergoplatform.com/mining/autolykos/

Difficulty adjustment

    What it is: The mechanism that adjusts mining difficulty to target ~2 minute blocks.
    Why it matters: Stabilizes block production and network operation under changing hash rate.
    Docs: https://docs.ergoplatform.com/mining/difficulty/

Emission schedule (monetary emission)

    What it is: How new ERG enters circulation via block rewards.
    Why it matters: It’s central to long-term economics and miner incentives. When discussing emission changes or tail emission, the key reference is EIP-27 .
    Docs (emission overview): https://docs.ergoplatform.com/mining/emission/
    Reference for emission model changes: EIP-27 (mentioned here as required context)

Storage Rent (demurrage / on-chain “garbage collection”)

    What it is: A protocol mechanism that charges a nominal fee on boxes that remain unmoved for a long period (designed to mitigate state bloat).
    Why it matters: Encourages efficient use of on-chain storage and supports long-term sustainability of the UTXO set.
    Docs: https://docs.ergoplatform.com/mining/rent/
    (and overview: https://docs.ergoplatform.com/dev/protocol/storage-rent/ )

4) Light clients & scalability primitives
NiPoPoWs

    What it is: Non-Interactive Proofs of Proof-of-Work—compact proofs that allow verification of chain events with much less data than full headers/state.
    Why it matters: Supports more capable light clients and is part of Ergo’s approach to usability without centralized intermediaries.
    Docs: https://docs.ergoplatform.com/dev/protocol/nipopows/

Authenticated state / AVL+ trees / state digest

    What it is: Ergo commits to the UTXO set using authenticated data structures (AVL+ tree), with a digest in block headers.
    Why it matters: Enables efficient proofs about UTXO membership/non-membership and supports stateless verification ideas.
    Docs (AVL): https://docs.ergoplatform.com/dev/protocol/avl/

5) Assets, tokens, and identifiers
Native tokens (first-class assets)

    What it is: Tokens are supported at the protocol level and live in R2 of boxes.
    Why it matters: Many dApps (DEXes, stablecoins, NFTs, DAOs) are built from native tokens plus scripts—no separate “token contract” is required in the same way as account-based chains.
    Docs: https://docs.ergoplatform.com/dev/data-model/box/tokens/

Token ID rule / NFT pattern

    What it is: A transaction can mint at most one new token type; the token id is derived from the first input box id of the minting transaction. An NFT is typically a token with supply 1.
    Why it matters: This is widely used to uniquely identify boxes (state boxes, pool boxes, config boxes) and to anchor “singleton” state in eUTXO designs.
    (Covered in Ergo box/token docs above)

6) Wallets & user-facing basics (practical ecosystem terms)
Addresses

    What it is: Encodings of spending conditions (scripts), not “accounts with balances.”
    Why it matters: Multiple boxes can share the same address; your “balance” is the sum of boxes you can spend.
    Docs: https://docs.ergoplatform.com/dev/wallet/address/

Wallet recommendations

    Note: Yoroi for Ergo is no longer supported. Use Nautilus (browser) or a mobile wallet from the official list:
    https://ergoplatform.org/en/get-erg/#Wallets

7) “Meta” terms you’ll see in dev discussions
dApp state as boxes

    What it is: Instead of mutable contract storage, dApps model state as one or more boxes (often identified by an NFT) that get consumed and recreated.
    Why it matters: This mental model is essential for understanding Ergo DEX pools, stablecoin designs, DAOs, auctions, and oracle mechanisms.

Guard script / spending predicate

    What it is: The logic in R1 that must evaluate to true for a box to be spent.
    Why it matters: It’s the enforcement point for all contract rules.

If you want, I can tailor this into a “one-page cheat sheet”

Tell me which angle you care about most:

    User/investor vocabulary (wallets, tokens, mining, storage rent, emission/EIP-27), or
    Developer vocabulary (boxes/registers, ErgoScript/ErgoTree, data inputs, multi-stage patterns), or
    DeFi vocabulary (oracles, pool boxes, NFTs as identifiers, etc.).


8) Node, networking, and validation (what “running Ergo” means)
Full node

    What it is: A node that downloads and validates blocks/transactions and maintains the UTXO set (boxes).
    Why it matters: Full nodes enforce consensus rules and independently verify scripts, token rules, and PoW.
    Docs: https://docs.ergoplatform.com/node/

Mempool

    What it is: The set of valid, unconfirmed transactions a node is holding before they’re mined.
    Why it matters: For dApps and wallets, mempool behavior affects UX (e.g., double-spend attempts, transaction chaining, fee bumping patterns).
    Docs: https://docs.ergoplatform.com/node/mempool/

Context variables (HEIGHT, SELF, INPUTS, OUTPUTS, etc.)

    What it is: The data a script can “see” when it is evaluated (current height, the box being spent, other inputs/outputs, etc.).
    Why it matters: This is how ErgoScript stays deterministic: contracts validate against the transaction and blockchain context, not arbitrary external calls.
    (Core ErgoScript concepts are covered under ErgoScript docs)
    Docs: https://docs.ergoplatform.com/dev/scs/ergoscript/ergoscript-key-concepts/

9) Fees, minimum box value, and “UTXO hygiene” (practical constraints)
Minimum transaction fee

    What it is: Ergo has a protocol minimum fee (commonly 0.001 ERG, though wallets can choose higher).
    Why it matters: Fees are predictable compared to gas-style systems; dApps often design flows around fixed fee assumptions.
    Docs: https://docs.ergoplatform.com/dev/protocol/tx/min-fee/

Minimum box value

    What it is: A box must contain at least a minimum amount of ERG to exist (to pay for its storage footprint).
    Why it matters: This is a major design constraint for token-heavy apps: every token-holding box must also carry enough ERG.
    Docs: https://docs.ergoplatform.com/dev/protocol/tx/min-box-value/

Box selection

    What it is: Wallet logic for choosing which boxes to spend to fund a transaction.
    Why it matters: Impacts privacy, fees, and whether you accidentally create lots of “dust” boxes that are annoying to manage.
    Docs: https://docs.ergoplatform.com/dev/wallet/box-selection/

10) Token design patterns (how people actually build “stateful” apps on eUTXO)
Singleton / “state NFT”

    What it is: A common pattern where a unique token (often supply=1) marks the canonical state box for a protocol (pool state, DAO state, config state).
    Why it matters: It gives you a stable identity for “the one true box” representing a contract’s current state, even though boxes are immutable and replaced each update.
    (This pattern is widely used across Ergo dApps; it relies on native token rules and box replacement.)

Box lifecycle / state transition

    What it is: A contract enforces that when a state box is spent, a new output box is created with:
        the same state NFT,
        updated registers,
        and a script that preserves invariants.
    Why it matters: This is the core “state machine” approach on Ergo.

Token emission / minting transaction

    What it is: Minting happens in a transaction; the token id is tied to the first input box id.
    Why it matters: Prevents ambiguity about token identity and supports deterministic token creation.

11) Oracles and shared data (how contracts learn about the world)
Oracle pools

    What it is: A mechanism to publish external data (like prices) on-chain in a way contracts can reference.
    Why it matters: Many DeFi designs (stablecoins, synthetic assets, lending) need price feeds; on Ergo this is typically done via oracle boxes + data inputs.
    Docs: https://docs.ergoplatform.com/uses/oracles/

Data input referencing

    What it is: Contracts can require that a transaction includes a specific oracle box as a data input and then read its registers.
    Why it matters: This is the standard “no global state, but shared truth” pattern in eUTXO.

12) Privacy-related building blocks (common terms even if you don’t use them)
Sigma protocols (AND/OR composition)

    What it is: Spending conditions can be composed logically (e.g., “Alice AND Bob” or “Alice OR timelock”).
    Why it matters: Enables expressive authorization and is a base for more advanced privacy constructions.
    Docs: https://docs.ergoplatform.com/dev/protocol/zkp/

Ring signatures / threshold signatures (as contract patterns)

    What it is: Ways to prove “one of these keys signed” (ring) or “m-of-n signed” (threshold).
    Why it matters: These show up in multisig custody, DAOs, mixers, and advanced access control.

13) Interoperability & off-chain execution model (how Ergo dApps are actually run)
Off-chain transaction building

    What it is: In Ergo, most “computation” is done off-chain by constructing a transaction that will satisfy on-chain validation.
    Why it matters: This is a huge conceptual shift from account-based chains: the chain validates, it doesn’t “run your program” in the same way.
    Docs (ErgoScript paradigm/scalability discussion): https://docs.ergoplatform.com/dev/scs/ergoscript/

Atomic swaps

    What it is: Trustless exchange patterns enabled by UTXO-style scripting.
    Why it matters: A classic UTXO advantage; also a building block for cross-chain and DEX-like designs.
    Docs: https://docs.ergoplatform.com/dev/protocol/eutxo/atomic/

14) Storage rent in practice (how it affects users and dApps)
“Unmoved boxes” and long-term state

    What it is: Storage rent targets boxes that sit untouched for long periods.
    Why it matters: Protocols that create long-lived boxes (vaults, time locks, cold storage) need to understand how to manage/refresh boxes over time.
    Docs: https://docs.ergoplatform.com/mining/rent/

15) Common ErgoScript idioms (terms you’ll see in real contracts)
SELF

    What it is: The box currently being spent (the script is attached to it).
    Why it matters: Used to read its registers/tokens/value and enforce invariants.

INPUTS / OUTPUTS

    What it is: Arrays of boxes consumed/created by the transaction.
    Why it matters: Most state-machine contracts check that a specific output exists with required properties.

proveDlog / public key checks

    What it is: Standard “signature-like” authorization checks.
    Why it matters: The base case for ownership and spending rights.

(These are covered in ErgoScript key concepts and language resources.)

    Docs: https://docs.ergoplatform.com/dev/scs/ergoscript/ergoscript-key-concepts/

16) Ecosystem “must-know” references and where to learn
Official documentation hub

    What it is: The canonical docs site for protocol, dev, mining, node, and wallet concepts.
    Why it matters: Ergo evolves via EIPs and documented protocol rules; this is where you verify details.
    https://docs.ergoplatform.com/

PDFs / formal documents

    If you need any official PDFs (language specs, papers, etc.), use the documentation base page:
    https://docs.ergoplatform.com/documents/


# Sheet 1 — Ergo Developer Vocabulary (one‑pager)
Core ledger model

    eUTXO (Extended UTXO) : Ergo’s state model—transactions consume boxes and create new boxes; boxes can carry data + scripts.
    Why: everything in Ergo dApps is modeled as box state transitions.
    https://docs.ergoplatform.com/dev/protocol/eutxo/
    Box : An unspent output (UTXO) containing ERG, tokens, registers, and a guarding script.
    Why: the “unit of state” for users and contracts.
    https://docs.ergoplatform.com/dev/data-model/box/
    Transaction (Tx) : Atomic update that spends input boxes and produces output boxes.
    Why: the only way state changes on-chain.
    https://docs.ergoplatform.com/dev/protocol/transactions/
    Data Inputs (read-only inputs) : Boxes referenced for reading but not spent.
    Why: enables oracle reads and shared config/state without contention.
    https://docs.ergoplatform.com/dev/protocol/tx/read-only-inputs/

Box internals (what contracts read/write)

    Registers (R0–R9) : Box fields. Commonly:
        R0 value (nanoERG), R1 script, R2 tokens, R3 creation info, R4–R9 custom data
        Why: registers are how you store contract parameters and evolving state.
        https://docs.ergoplatform.com/dev/data-model/box/registers/
    Tokens in R2 : Native assets stored as (tokenId → amount) pairs.
    Why: tokens are first-class; many protocols are “script + token + registers.”
    https://docs.ergoplatform.com/dev/data-model/box/tokens/

Smart contracts & validation

    ErgoScript : High-level language for spending conditions.
    Why: defines the rules for spending boxes and enforcing invariants.
    https://docs.ergoplatform.com/dev/scs/ergoscript/
    ErgoTree : Serialized low-level form of a contract (what nodes evaluate).
    Why: addresses/scripts compile to ErgoTree; important for tooling and debugging.
    https://docs.ergoplatform.com/dev/scs/ergotree/
    Guarding script / spending predicate : The logic in a box that must evaluate to true to spend it.
    Why: the enforcement point for all protocol rules.
    Context variables (typical): SELF , INPUTS , OUTPUTS , HEIGHT
    Why: contracts validate against the transaction + blockchain context deterministically.
    (See ErgoScript docs above.)
    Sigma protocols / SigmaProp : Cryptographic statements used in authorization (proofs of knowledge, composable logic).
    Why: enables multisig/threshold logic and advanced authorization patterns.
    https://docs.ergoplatform.com/dev/scs/sigma/

Common contract architecture patterns

    State machine via box replacement : Spend a “state box,” create the next “state box” with updated registers.
    Why: primary way to build stateful apps on eUTXO.
    Singleton / State NFT : A unique token (supply 1) that marks the canonical state box.
    Why: gives a stable identity for “the current state” across updates.
    Multi-stage contracts (transaction chaining) : Complex flows implemented as a sequence of spends/creates.
    Why: supports sophisticated logic without global mutable storage.
    (Covered in ErgoScript / eUTXO concepts.)

Fees & UTXO hygiene (practical constraints)

    Minimum transaction fee : Protocol minimum fee rules.
    Why: affects UX and transaction construction.
    https://docs.ergoplatform.com/dev/protocol/tx/min-fee/
    Minimum box value : A box must carry enough ERG to exist.
    Why: every token box needs ERG “dust” to be valid; impacts DeFi design.
    https://docs.ergoplatform.com/dev/protocol/tx/min-box-value/
    Box selection : Wallet/SDK algorithm to choose which boxes to spend.
    Why: impacts privacy, change outputs, and fragmentation.
    https://docs.ergoplatform.com/dev/wallet/box-selection/

Dev tooling & integration terms

    dApp Connector : Wallet ↔ dApp connection for signing and interaction.
    Why: standard browser dApp integration path.
    https://docs.ergoplatform.com/dev/wallet/payments/dApp/
    ErgoPay : QR/link based request flow for wallets.
    Why: common for mobile-friendly payments and dApp flows.
    https://docs.ergoplatform.com/dev/wallet/payments/ergopay/ergo-pay/
    ErgoAuth : Authentication flows using Ergo keys.
    Why: sign-in / authorization patterns for apps.
    https://docs.ergoplatform.com/dev/wallet/payments/ergoauth/
    AppKit / Fleet SDK / ergo-lib : Common libraries for building and signing transactions.
    Why: most off-chain logic is “build a Tx that satisfies scripts.”
    (Entry points) https://docs.ergoplatform.com/dev/stack/frameworks/

Wallet note (for dev testing)

    Yoroi for Ergo is no longer supported—use Nautilus or a mobile wallet from:
    https://ergoplatform.org/en/get-erg/#Wallets

# Sheet 2 — Ergo DeFi Vocabulary (one‑pager)
DeFi on eUTXO (the big idea)

    DeFi protocols are box state machines : liquidity pools, stablecoins, lending positions, etc. are represented by one or more boxes whose scripts enforce valid transitions.
    Why: explains why “updating a pool” means spending and recreating a pool box.

DEX & liquidity primitives

    AMM (Automated Market Maker) : On-chain swap mechanism using a pool’s reserves and pricing function.
    Why: core DEX model; implemented as pool boxes + swap transactions.
    Pool box / pool state : The box holding reserves + parameters (often with a state NFT).
    Why: canonical on-chain state for an AMM pool.
    LP tokens : Tokens representing a share of pool liquidity.
    Why: used to redeem underlying reserves and track provider ownership.
    Swap transaction : A transaction that spends the pool box and outputs the updated pool box + user outputs.
    Why: the “execution” of a trade is a validated state transition.
    Slippage : Difference between expected and executed price due to pool curve and trade size.
    Why: users set limits; contracts enforce min-out constraints.

(DEX overview) https://docs.ergoplatform.com/uses/dex/
Price feeds & oracle terms

    Oracle : On-chain published external data (e.g., ERG/USD).
    Why: stablecoins, lending, and derivatives need reliable prices.
    Oracle pool : A structured mechanism for maintaining and updating oracle values.
    Why: standard way to provide price data to contracts.
    https://docs.ergoplatform.com/uses/oracles/
    Data input oracle read : Using oracle boxes as read-only inputs.
    Why: lets many transactions reference the same price without spending the oracle box.

Stablecoins & collateral concepts

    Collateral : Assets locked to back a stable asset or position.
    Why: defines solvency and liquidation thresholds.
    Overcollateralization : Collateral value exceeds issued stable value.
    Why: common risk control in crypto-backed stable designs.
    Peg : Target price (e.g., 1 USD).
    Why: stablecoin goal; maintained via incentives/mechanisms.
    SigmaUSD (Djed-style) : Ergo’s well-known stablecoin design category in the ecosystem.
    Why: a flagship DeFi primitive on Ergo.
    https://docs.ergoplatform.com/uses/sigmausd/
    Reserve / bank box (pattern) : A box (or set of boxes) holding collateral and enforcing mint/redeem rules.
    Why: typical eUTXO stablecoin architecture.

(Stablecoins overview) https://docs.ergoplatform.com/uses/stablecoins/
Lending / borrowing vocabulary (common across protocols)

    Borrow position / vault : A box representing a user’s collateral + debt state.
    Why: positions are stateful and updated by spending/recreating the position box.
    Interest / rate model : Rules that update debt over time (often height-based).
    Why: must be enforceable via deterministic on-chain checks.
    Liquidation : Forced closing of undercollateralized positions.
    Why: protects solvency; implemented as a valid spend path in the position script.

(Use-cases overview) https://docs.ergoplatform.com/uses/use-cases-overview/
Derivatives vocabulary (Ergo-specific ecosystem terms)

    Options / calls : Right (not obligation) to buy at a strike price.
    Why: implemented via contracts and tokenized positions.
    OptionCoin / OptionPools / Hodlcoin : Examples of derivative primitives discussed in Ergo docs.
    Why: show how far eUTXO + ErgoScript can go for financial contracts.
    https://docs.ergoplatform.com/uses/deriv/

Fees & execution realities in DeFi

    Babel fees : Paying transaction fees in tokens (via a mechanism that still satisfies miner fee requirements).
    Why: improves UX for token-heavy DeFi users.
    https://docs.ergoplatform.com/dev/protocol/tx/babel-fees/
    Chained transactions : DeFi actions may require sequences (e.g., prepare box → execute swap).
    Why: arises from eUTXO constraints and state machine design.

Security & risk terms (what DeFi users/devs watch)

    Invariant : A rule that must always hold (e.g., pool accounting, conservation constraints).
    Why: DeFi safety is “invariants enforced by scripts.”
    MEV (conceptual) : Value extractable by transaction ordering.
    Why: affects DEX execution and user protection patterns (limits, batching).
    Smart contract risk : Bugs in scripts or off-chain builders.
    Why: most failures are incorrect state transition validation or incorrect transaction construction.

# Top 10 invariants Ergo DeFi devs commonly enforce (on-chain)

    State NFT continuity (canonical state box)

    The “pool/state” box must carry the same singleton token (state NFT) before and after the transition.
    Typical check: output state box contains the same tokenId with amount 1 .

    Script continuity (same contract / expected next-stage contract)

    The successor state box must keep the same guarding script (or switch only to an explicitly allowed next script in a staged protocol).
    Typical check: OUTPUTS(i).propositionBytes == SELF.propositionBytes (or equals a known nextScriptHash/bytes ).

    Token conservation (no unintended mint/burn inside the protocol)

    For protocol-controlled tokens (LP token, pool share token, receipt token), enforce that totals match the intended rule:
        strict conservation for “non-burnable” tokens, or
        controlled mint/burn only under specific branches.
    Typical check: sum token amounts across selected outputs equals expected.

    Reserve accounting / balance transition correctness

    Pool reserves must update according to the swap/deposit/withdraw formula (AMM curve, fees, etc.).
    Typical check: new reserves in successor box registers/tokens match computed values from inputs.

    Fee correctness (protocol fee / operator fee / miner fee constraints)

    Enforce that a fee output exists, goes to the right script/address, and is at least the computed amount.
    Typical check: OUTPUTS.exists(o => o.propositionBytes == feeScript && o.value >= fee)

    No value leakage (ERG and/or token leakage constraints)

    Ensure the transaction doesn’t siphon extra ERG/tokens from the state box beyond what the action allows.
    Typical check: successor box keeps minimum ERG, preserves required tokens, and only permitted deltas occur.

    Minimum box value preserved (anti-dust / survivability)

    Successor boxes (state box, fee box, user boxes) must meet minimum box value constraints.
    Typical check: successor.value >= minBoxValue

    Oracle correctness (freshness + identity + bounds)

    If using an oracle data input, enforce:
        the oracle box is the correct one (often via oracle NFT),
        the value is within sane bounds,
        and the reading is “fresh enough” (height window).
    Typical check: data input contains oracle NFT; HEIGHT - oracle.creationHeight <= maxAge .

    Authorization / governance constraints

    Admin actions (parameter changes, emergency modes, upgrades) require a signature (proveDlog) or a threshold condition.
    Typical check: proveDlog(adminPk) or atLeast(k, Coll(pk1, pk2, ...))

    Output structure constraints (shape of the transaction)

    Enforce the transaction has the expected number/type/order of outputs (or at least that required outputs exist).
    Typical check: OUTPUTS.size == N or “must contain” checks via exists / forall .

# Most-used ErgoScript checks & idioms (short list)

A) “There exists an output that matches X”

Use this instead of map+fold counting patterns.

val ok = OUTPUTS.exists({ (o: Box) =>
  o.propositionBytes == expectedScript &&
  o.value >= minValue
})

B) “Find the successor state box by state NFT”

Common pattern: locate the output that carries the state NFT.

val stateId = SELF.tokens(0)._1  // if SELF.tokens(0) is the state NFT
val successorExists = OUTPUTS.exists({ (o: Box) =>
  o.tokens.size > 0 && o.tokens(0)._1 == stateId && o.tokens(0)._2 == 1
})

Notes:

    Many contracts also enforce position (e.g., successor is OUTPUTS(0) ) to avoid ambiguity and reduce complexity.

C) Token/NFT continuity (exact token list vs specific token)

    Exact list equality (order-sensitive):

val sameTokens = OUTPUTS(0).tokens == SELF.tokens

    Specific token continuity (preferred when order may vary):

val id = SELF.tokens(0)._1
val ok = OUTPUTS(0).tokens.exists({ (t: (Coll[Byte], Long)) =>
  t._1 == id && t._2 == 1
})

D) Height windows (timelocks, oracle freshness, epoch rules)

val inWindow = HEIGHT >= startHeight && HEIGHT < endHeight

Oracle freshness often looks like:

val fresh = HEIGHT - oracleBox.creationHeight <= maxAge

E) Script continuity / upgrade gating

val sameScript = OUTPUTS(0).propositionBytes == SELF.propositionBytes

Or allow a controlled upgrade:

val okScript = sameScript || OUTPUTS(0).propositionBytes == nextScriptBytes

F) Register presence checks (avoid .get crashes)

Use isDefined before .get, often guarded by if.

val hasR4 = SELF.R4[Long].isDefined
val ok = hasR4 && (SELF.R4[Long].get > 0L)

(ErgoScript boolean && short-circuits, so the .get is only evaluated if hasR4 is true.)
G) Output “shape” constraints

val correctOutputs = OUTPUTS.size == 3

Or “at least”:

val enough = OUTPUTS.size >= 2

H) “All outputs satisfy a predicate” (less common than exists, but used)

val allOk = OUTPUTS.forall({ (o: Box) => o.value >= minBoxValue })

I) Sum / fold patterns (used for conservation checks)

Example: sum ERG in outputs (or token amounts) with fold.

val totalOut = OUTPUTS.map({ (o: Box) => o.value })
  .fold(0L, { (a: Long, b: Long) => a + b })

J) Authorization checks (single key, multisig-like)

val adminOk = proveDlog(adminPk)

For k-of-n, ErgoScript commonly uses atLeast with a collection of SigmaProps (depending on how you structure keys).