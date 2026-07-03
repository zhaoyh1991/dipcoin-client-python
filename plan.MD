# Sui GraphQL Migration Plan

## Current SDK Sui Chain Surface

- Direct Sui chain methods have been removed from `DipcoinClient`.
- `SuiGraphQLClient` is the default lightweight direct Sui helper because it avoids native dependencies.
- `SuiGraphQLClient.get_native_chain_token_balance`, `get_usdc_coins`, and `get_usdc_balance` read balances through GraphQL.
- `SuiGraphQLClient.get_user_position_from_chain` and `get_margin_bank_balance` use GraphQL dynamic-field queries.
- `SuiGraphQLClient.execute_transaction` submits already-built `transactionDataBcs` and signatures through GraphQL.
- Direct in-SDK Dipcoin Move-call PTB construction is intentionally deferred.
- Legacy helpers under `src/sui_utils/rpc.py`, `src/sui_utils/sui_interfaces.py`, and transaction signing helpers are no longer exposed through `DipcoinClient`.
- `DipcoinClient.create_margin_relay_signature` remains in the main client because add/remove margin should move to backend relayer flows.

## Recommended Direction

- Keep `SuiGraphQLClient` as the default direct Sui transport for simple reads and transaction submission without PTB construction.
- Use relayer APIs for Dipcoin-specific write flows that should work across Sui, ETH, and Solana wallets.
- Remove direct Sui chain writes from the main trading client so ETH and Solana users use the same relayer path as Sui users where possible.
- Keep `create_margin_relay_signature` in `DipcoinClient`; this is the preferred SDK surface for add/remove margin relayer support.
- If local PTB construction becomes important, evaluate it as a separate package using community `pysui` or the `sui4j` reference, instead of adding native dependencies to this client.

## Replacement Options

- **Relayer-first:** add REST endpoints for deposit, withdraw, add margin, remove margin, sub-account updates, and close-position operations; SDK signs payloads and submits them to relayers.
- **GraphQL:** preferred first option for simple chain reads and transaction execution because it is easier to integrate from Python than generated gRPC clients.
- **PTB builder:** do not bundle in this client for now. If needed later, evaluate community `pysui` first, or port low-level BCS/PTB logic from `sui4j` into a separate package.
- **gRPC:** reserve for cases where GraphQL cannot cover transaction/object details or maintained Sui tooling makes gRPC easier.
- **SDK removal:** remove direct Sui chain write support from this client and document official relayer-only flows.

## GraphQL / PTB Evaluation

- **GraphQL reads:** good fit for simple chain reads such as object lookups, coin pages, balances, transaction history, and dynamic-field style queries if the official schema exposes the required object relationships.
- **GraphQL writes:** can be used as the transaction submission/execution transport when the SDK already has transaction bytes and signatures. Treat GraphQL as the read/write API layer replacing JSON-RPC endpoints.
- **PTB:** not a transport. PTB is the transaction-building/composition layer needed to encode one or more Move calls into transaction bytes before GraphQL or gRPC can execute them.
- **PTB support scope:** needed later if the SDK should locally compose deposit, withdraw, sub-account, add-margin, remove-margin, or multi-step Sui transactions without backend relayers.
- **Relayer writes:** preferred for product flows like add/remove margin, deposit/withdraw, and sub-account operations because it also works for ETH/Solana wallets via signed payloads.
- **Python complexity:** GraphQL can be implemented with `aiohttp` and plain query strings. gRPC usually requires generated clients and protobuf version management, so keep it as a second step unless GraphQL cannot cover required PTB/query behavior.

## SDK Shape

- `DipcoinClient`: exchange API client only; wallet onboarding, order signing, cancel signing, relayer payload signing.
- `SuiGraphQLClient`: default lightweight Sui GraphQL transport.
- `SuiPtbBuilder` (optional separate package later): local PTB construction for Dipcoin Move calls if relayer-only write flows are insufficient.
- `SuiGrpcClient` (optional later): only add if GraphQL cannot satisfy required data or execution needs.

## Migration Steps

1. `SuiGraphQLClient` added as a lightweight object/balance/coin/dynamic-field reference implementation.
2. `DipcoinClient` remains free of direct Sui chain methods.
3. Add/remove margin examples now use `create_margin_relay_signature` and wait for relayer submission.
4. If direct Sui writes remain required, implement PTB construction separately and execute with GraphQL.
5. Choose gRPC only if GraphQL cannot cover a required read/write path with acceptable complexity.

## Open Items

- Confirm whether backend relayer endpoints will cover deposit, withdraw, sub-account management, add margin, and remove margin.
- Confirm which direct Sui write methods still need SDK support after relayer endpoints are available.
- Decide whether margin-bank reads should remain chain reads or move to backend read APIs.
- Validate GraphQL dynamic-field literal names against Dipcoin table key encoding in staging.
- If local PTB support becomes necessary, evaluate `pysui` installation tradeoffs and `sui4j` as references in a separate package.
- Use gRPC only if GraphQL cannot cover a required read/write path with acceptable complexity.
