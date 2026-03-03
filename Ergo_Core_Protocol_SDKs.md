#### Core Protocol & SDKs

| Repository | Language | What to Extract | Priority |
|-----------|----------|----------------|----------|
| `ergoplatform/ergo` | Scala | Node API endpoints (Swagger), config options, mining | High |
| `ergoplatform/sigmastate-interpreter` | Scala | ErgoScript compiler internals, ErgoTree spec, test cases as examples | High |
| `ergoplatform/sigma-rust` | Rust | WASM bindings, wallet features, ErgoTree interpreter | High |
| `ergoplatform/eips` | Markdown | All EIPs as structured reference docs | High |
| `ergoplatform/oracle-core` | Rust | Oracle pool v2 architecture, connector patterns | High |
| `ergoplatform/ergo-appkit` | Java/Scala | SDK patterns, transaction building, contract compilation | High |
| `fleet-sdk/fleet` | TypeScript | Core library, transaction builder, wallet integration, serialization | High |
| `fleet-sdk/fleet-by-example` | TypeScript | Worked examples — direct cookbook material | High |
| `fleet-sdk/docs` | Markdown | VitePress docs — migrate/cross-reference | High |
| `ergo-pad/ergo-python-appkit` | Python | Python SDK patterns, JPype bridge | Medium |
| `ergoplatform/ergo-wallet-app` | Kotlin | Mobile wallet patterns, key management | Medium |
| `ergoplatform/ledger-app-ergo` | C | Hardware wallet integration | Low |

#### DeFi Protocols — Smart Contracts + Off-chain Code

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Spectrum/ErgoDEX** | | | |
| `spectrum-finance/ergo-dex` | DEX contracts | ErgoScript | AMM pools, order-book, atomic swaps, partial fills, LP mechanics |
| `spectrum-finance/ergo-dex-backend` | Off-chain bots | Scala | Order matching, execution bots, state tracking |
| **Dexy Stablecoin** | | | |
| `kushti/dexy-stable` | Stablecoin | ErgoScript/Scala | Oracle-pegged minting, LP with oracle rate modification, cross-tracker, top-up swaps, anti-drain mechanisms |
| `ergoplatform/ergo-jde` (Dexy specs) | Spec | Markdown/Scala | Dexy design docs and test specifications |
| **SigmaUSD / AgeUSD** | | | |
| `DjedAlliance/Djed-Ergo` | Stablecoin | ErgoScript/Scala | AgeUSD protocol, headless dApp pattern, reserve management, CLI implementation |
| **Duckpools** | | | |
| `duckpools` org — contracts repo | Lending | ErgoScript | Lending pools, collateralized borrowing, interest rate algorithms, liquidation |
| `duckpools` — option pools | Options | ErgoScript | Option contract patterns |
| **SigmaFi** | | | |
| SigmaFi contracts | Bonds/Yield | ErgoScript | P2P bond contracts, yield strategies |
| SigmaFi UI | Frontend | JS/TS | dApp connector integration with DeFi |
| **Phoenix / HodlCoin** | | | |
| HodlCoin contracts | Proof-of-hodl | ErgoScript | Time-locked value accrual, proof-of-hodl mechanics |
| **SigmaO** | | | |
| SigmaO contracts | Options trading | ErgoScript | Decentralized options on Ergo tokens |

#### Infrastructure & Bridges

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Rosen Bridge** (34 repos) | | | |
| `rosen-bridge/contract` | Bridge contracts | ErgoScript | Guard/watcher architecture, multi-sig consensus on-chain, RWT staking, fraud detection, event lifecycle |
| `rosen-bridge/watcher` | Watcher node | TypeScript | Chain scanning, commitment creation, event trigger assembly |
| `rosen-bridge/scanner` | Block scanner | TypeScript | Abstract scanner pattern, address/token extractors, observation extraction |
| `rosen-bridge/guard` (if public) | Guard node | TypeScript | Event verification, cross-chain tx signing, payment distribution |
| `rosen-bridge/ui` | Frontend | TypeScript | Bridge UI patterns, cross-chain status tracking |
| **Wallets** | | | |
| `nautls/nautilus-wallet` | Browser wallet | TypeScript/Vue | EIP-12 dApp connector implementation (reference), wallet architecture, Ledger integration |
| `ThierryM1212/SAFEW` | Browser wallet | JavaScript | Alternative EIP-12 implementation, ErgoMixer integration |
| `ErgoWallet/ergowallet-desktop` | Desktop wallet | TypeScript | Desktop wallet patterns, multi-wallet management |

#### DAOs & Governance

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Paideia** (11 repos) | | | |
| `paideiadao/paideia-contracts` | DAO contracts | ErgoScript/Python | Staking, voting, proposal lifecycle, treasury management, config boxes as on-chain oracles, EIP-6 protocol specs |
| `paideiadao/paideia-app` | Frontend | TypeScript/Next.js | Full dApp frontend with wallet connection, proposal UI, staking interface |
| `paideiadao/paideia-state` | State management | Scala | On-chain state tracking, box scanning |
| `paideiadao/paideia-offchain` | Off-chain logic | Python | Transaction assembly, bot operations |
| `paideiadao/paideia-sdk` | SDK | Scala | Optimized Scala function calls for contract interaction |
| `paideiadao/paideia-data` | Backend | Python/SQL/Redis | Database patterns for dApp state, caching |

#### Analytics & Portfolio

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **CruxFinance** | Portfolio/Analytics | Scala/Rust/JS/TS | Cross-chain liquidity, portfolio tracking, charting, EXLE lending integration |
| **ErgoPad / Danaides** | Indexing | Python | High-performance blockchain indexing, dApp backend patterns |
| `ergo-pad/nft-market` | NFT Marketplace | TypeScript/Next.js | NFT marketplace frontend patterns, MUI + Next.js template |
