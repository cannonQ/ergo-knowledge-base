---
title: duckpools/lend-protocol-contracts — repaymentContract.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/repaymentContract.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/repaymentContract.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Repayment Contract

## Purpose

This contract validates loan repayment transactions within the DuckPools lending protocol. It ensures that when a borrower repays a loan, the pool state is correctly updated with the repaid amount, the pool's borrow token balance increases accordingly, and the repaid value is transferred to the pool.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: Initial pool box—contains the Pool State NFT and borrow token balance before repayment
- `INPUTS(1)`: The repayment box itself (`SELF`)—carries the loan amount in its tokens and the repayment value in ERG
- Additional inputs may exist (change, fees, etc.)

**Outputs:**
- `OUTPUTS(0)`: Final pool box—updated pool state with refreshed borrow token balance and increased ERG value
- Additional outputs may exist (borrower change, etc.)

## Key Logic

The contract enforces five invariants:

1. **Pool NFT Identity (Initial)**: Verifies `INPUTS(0)` holds the correct Pool State NFT (`PoolNft`), confirming it is the authentic pool box.

2. **Pool NFT Identity (Final)**: Verifies `OUTPUTS(0)` carries the same Pool State NFT, ensuring the pool state is preserved and transitioned correctly.

3. **Borrow Token Reconciliation**: Calculates the change in borrowed tokens:
   - `borrow0` = `MaxBorrowTokens − initial_borrow_balance`
   - `borrow1` = `MaxBorrowTokens − final_borrow_balance`
   - `deltaBorrowed` = `borrow0 − borrow1` must equal the loan amount
   - This ensures the borrow token supply decreased by exactly the repayment amount (higher available balance = lower debt).

4. **Value Transfer Validation**: Ensures `finalPool.value − initialPool.value ≥ SELF.value − transactionFee`, confirming sufficient ERG was transferred to the pool to cover the repayment minus protocol fees.

5. **Multi-Box Spend Safety**: Enforces `INPUTS(1) == SELF` to prevent a single box from being spent multiple times in the same transaction (protects against double-repayment).

## Registers Used

**No R4–R9 registers are explicitly read or written in this contract.**

The contract relies entirely on:
- **Box value** (`box.value`): Tracks ERG amounts
- **Native tokens** (`box.tokens`): Tracks pool state NFT and borrow token balances
- **Token indices**: Assumes fixed positions in the tokens array (e.g., token(0) = Pool NFT, token(2) = borrow tokens)

*Note: Register usage may be managed by companion contracts or off-chain logic.*

## Tokens

1. **Pool State NFT** (`PoolNft = Ahk13GiqmS1txRpk9TdJmbs1Qr6wGya8MstvhMVfNDbq`):
   - Singleton token identifying the authoritative pool box
   - Must appear in both input and output at `tokens(0)`
   - Enforces single pool state across transactions

2. **Borrow Token** (position `tokens(2)`):
   - Represents available lending capacity or outstanding debt
   - Balance tracked via `MaxBorrowTokens` reserve accounting:
     - `available = MaxBorrowTokens − balance`
     - `borrowed = available`
   - Repayment increases the balance (decreases borrowed amount)

3. **Loan Amount** (`SELF.tokens(0)._2`):
   - The quantity of borrow tokens being repaid in this transaction
   - Must match the calculated `deltaBorrowed`

## Integration Pattern

**Off-chain bot / transaction builder responsibilities:**

1. **Construct inputs:**
   - Fetch the current pool box (identified by Pool State NFT)
   - Fetch the borrower's repayment box with loan amount encoded in tokens(0)

2. **Calculate state transition:**
   - Determine the new pool borrow token balance: `newBalance = oldBalance + loanAmount`
   - Determine required ERG for pool: `poolERG = oldPoolERG + repaidValue − txFee`

3. **Construct outputs:**
   - Create new pool box carrying the Pool State NFT, updated borrow token balance, and increased ERG
   - Create borrower change output if needed

4. **Verify invariants before submission:**
   - Confirm borrow token delta matches loan amount
   - Confirm ERG transfer covers repayment
   - Confirm NFT presence and identity in both input and output

5. **Sign and submit:** Broadcast transaction; Ergo validates via this script.

## Related Contracts

**Likely integration points** (not directly referenced but architecturally coupled):

- **Pool Initialization Contract**: Mints the Pool State NFT and borrow token; sets `MaxBorrowTokens` constant
- **Borrowing Contract**: Decreases borrow token balance and sends ERG to borrower (inverse operation)
- **Interest Accrual Contract**: May update pool state to reflect interest fees before or after repayment
- **Liquidation Contract**: Seizes collateral and repays on behalf of defaulted borrowers

---

## Security Observations

- **Constant Segregation**: `MaxBorrowTokens` and `PoolNft` are hardcoded; no dynamic configuration risk
- **Invariant Enforcement**: All five conditions must pass (AND logic via `sigmaProp`); any failure aborts the transaction
- **Multi-box Attack Prevention**: `INPUTS(1) == SELF` guards against index manipulation in multi-input scenarios
- **State Machine Pattern**: Pool State NFT enforces a singleton pattern, ensuring only one valid pool box per transaction