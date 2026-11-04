# Dipcoin Python Client

A simple Python client library for interacting with the Dipcoin perp protocol, including its off-chain API gateway and on-chain contracts.

## What's New in 1.3.0

- Added Solana wallet support for onboarding plus v3 order and plan-order signing.
- Added Ethereum, Arbitrum, Optimism, Base, and Polygon wallet support with
  protocol-chain-aware authorization and v3 signing.
- Sui wallets remain supported; order and plan-order signing now defaults to v3.
- Added relayer-based margin adjustment for Sui, Solana, and EVM wallets.
- Added a fixed-point helper for estimating maximum removable margin.
- Humanized known 10^18-scaled numeric fields in both REST responses and websocket market/user payloads.
- Switched direct Sui chain helpers to a lightweight GraphQL client without Rust-native dependencies.

## Requirements

- Python 3.8 - 3.12 (recommended: Python 3.11)
- No Rust toolchain, Sui CLI, or local Sui PTB builder is required for the default client.

## Installation

### 1. Create Virtual Environment (Recommended)

```bash
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### 2. Install Package

```bash
pip install --upgrade pip
pip install dipcoin-client
```

After installation, import the client from your own Python script:

For routine API use, create an API wallet from the API management page in the
official Dipcoin website, then use its private key for signing and pass your
main wallet address as `parentAddress`. Avoid using your main wallet's private
key directly; the SDK supports it, but it gives the client broader authority.

```python
import asyncio
from dipcoin_client import DipcoinClient, Networks


async def main():
    client = DipcoinClient(
        True,
        Networks["SUI_STAGING"],
        "your_api_wallet_private_key",
        parentAddress="0x...your_main_wallet_address...",
    )
    try:
        await client.init(True)
        print("Wallet address:", client.get_public_address())
        print(await client.get_user_account_data())
    finally:
        await client.close_connections()


asyncio.run(main())
```

The PyPI package installs the client library, not the repository's `examples/` directory. To run a ready-made example, get the source repository and install the PyPI package in that environment:

```bash
git clone https://github.com/dipcoinlab/diptrade-perp-client-python.git
cd diptrade-perp-client-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install dipcoin-client
cp examples/.env.example examples/.env
# Edit examples/.env with your own test-wallet values, then:
source examples/.env && python examples/22.solana_place_query_cancel_order.py
```

The Solana order example submits and cancels a real test-environment order. Use test credentials and verify the selected network before running it. Other examples are in `examples/`; some require additional credentials or may submit orders.

For local development from this repository:

```bash
pip install -e .
```

This installs the project and direct dependencies in editable mode, so code changes take effect immediately without reinstalling.

## PyCharm Configuration

To enable proper code navigation and autocomplete in PyCharm:

1. **Mark Directories as Sources Root**:
   - Right-click on `src` directory → `Mark Directory as` → `Sources Root`
   - Right-click on `examples` directory → `Mark Directory as` → `Sources Root`

2. **Configure Python Interpreter**:
   - Go to `File` → `Settings` (Windows/Linux) or `PyCharm` → `Preferences` (macOS)
   - Navigate to `Project` → `Python Interpreter`
   - Ensure Python 3.8-3.12 is selected
   - Add project path: Click gear icon → `Show All` → Select interpreter → Click folder icon
   - Add to `Interpreter Paths`: `<project_root>/src`

3. **Invalidate Caches** (if needed):
   - `File` → `Invalidate Caches and Restart`

## Usage

### Configuration

Edit `examples/config.py` to set your test credentials:

```python
TEST_ACCT_KEY = "your_api_wallet_private_key"
TEST_NETWORK = "SUI_STAGING"  # mainnet: use "SUI_PROD"
```

Generate an API wallet in the official Dipcoin website's API management page.
Use that API wallet's private key as `TEST_ACCT_KEY` and configure the parent
wallet address where the example supports `parentAddress`. Do not use the main
wallet's private key for routine API access. Treat API wallet private keys as
secrets and never commit them to version control.

Examples `21.solana_user_data.py`, `22.solana_place_query_cancel_order.py` and
`23.eth_place_query_cancel_order.py` read the parent/API addresses and API
private key from environment variables. Copy `examples/.env.example` to
`examples/.env`, fill in your own test-wallet values, then load them and run:

```bash
source examples/.env && python examples/22.solana_place_query_cancel_order.py
# or
source examples/.env && python examples/23.eth_place_query_cancel_order.py
```

The local `examples/.env` is ignored by Git. Never put a private key in a
tracked source file.

### Run Examples

```bash
cd examples
python 1.initialization.py
```

### Basic Usage

```python
from dipcoin_client import DipcoinClient, Networks
import asyncio

async def main():
    client = DipcoinClient(
        True,  # Agree to terms and conditions
        Networks["SUI_STAGING"],
        "your_api_wallet_private_key",
        parentAddress="0x...your_main_wallet_address...",
    )
    try:
        await client.init(True)
        print("API wallet address:", client.get_public_address())
        print(await client.get_user_account_data())
    finally:
        await client.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
```

By default, the client decodes the JWT `exp` claim before authenticated REST requests and re-onboards automatically when the token will expire within 10 minutes. It does not retry failed requests after a `401`, so long-running programs should still handle expired-token or authorization errors returned by the API.

```python
client = DipcoinClient(
    True,
    Networks["SUI_STAGING"],
    "your_api_wallet_private_key",
    parentAddress="0x...your_main_wallet_address...",
    auto_reauth=True,  # default
    token_refresh_margin_seconds=600,  # default: 10 minutes
)
```

### EVM and Solana wallets

EVM wallets use the same EIP-191 `personal_sign` implementation and signature
scheme (`4`) on every supported EVM chain. The protocol chain identity is
separate from the signature scheme:

| `wallet_type` | Dipcoin protocol chain ID | Signed creator prefix |
| --- | ---: | --- |
| `eth` / `ethereum` / `evm` | 1 | `Ethereum:` |
| `arbitrum` | 3 | `Arbitrum:` |
| `optimism` | 4 | `Optimism:` |
| `base` | 5 | `Base:` |
| `polygon` | 6 | `Polygon:` |

These are Dipcoin protocol chain IDs, not EIP-155/RPC chain IDs. For example,
use `3` for Arbitrum rather than `42161`, and `5` for Base rather than `8453`.
The client sends the selected protocol chain ID to `/api/authorize`; the gateway
stores it in the JWT and injects `X-Wallet-Chain-Id` into downstream requests.

```python
client = DipcoinClient(
    True,
    Networks["SUI_STAGING"],
    "0x...api_wallet_private_key",
    wallet_type="arbitrum",
    parentAddress="0x...your_main_wallet_address...",
)
await client.init(True)
```

For configuration-driven integrations, keep `wallet_type="eth"` and pass the
protocol chain separately:

```python
from dipcoin_client import ARBITRUM_CHAIN_ID

client = DipcoinClient(
    True,
    Networks["SUI_STAGING"],
    "0x...api_wallet_private_key",
    wallet_type="eth",
    protocol_chain_id=ARBITRUM_CHAIN_ID,
    parentAddress="0x...your_main_wallet_address...",
)
```

Use `wallet_type="solana"` for Solana onboarding and v3 order, cancel, and
plan-order signatures.

Solana accepts a 32-byte seed or 64-byte keypair encoded as hex, base64, base58, or a JSON byte array.

Order and plan-order signatures default to `payloadVersion=3`. The client reads `marketEpoch` from exchange info during `init()` and falls back to `0` only when the market does not expose it yet. In a long-running process, refresh the market cache before signing when its 60-second TTL has elapsed:

```python
await client.refresh_market_info_if_stale()
signed_order = client.create_signed_order(order_request)
```

The refresh interval can be changed with `market_info_cache_ttl_seconds` when creating `DipcoinClient`. `get_exchange_info()` also updates the signing cache with the data it fetches. Pass `payloadVersion` or `marketEpoch` only when you need to override those defaults for a specific request.

### Wallet credentials (mnemonic or private key)

For API usage, prefer an API wallet created from the API management page in the
official Dipcoin website. Pass that wallet's private key to the client and the
main wallet address as `parentAddress`. `DipcoinClient` also accepts these
credential formats when direct wallet signing is intentionally needed:

- **BIP39 mnemonic** — space-separated phrase (typically 12 or 24 words). The client detects a mnemonic heuristically (word count and alphabetic words).
- **Sui private key export** — any of:
  - 64 hex characters (optional `0x` prefix)
  - Standard or URL-safe **base64** (32 bytes, or 33 bytes with a leading `0x00` byte)
  - **`suiprivkey1...`** Bech32 string (SIP-15), as exported by Sui tooling

The derived address and signing path match Sui’s Ed25519 wallet behavior (including correct address derivation from `scheme || public key`).

### Sub-accounts and `parentAddress`

Some setups use a **sub-account** key that only has trading/API permissions, while the **main wallet** remains the parent on-chain identity.

- When you authenticate with the **sub-account** key, pass the **main wallet address** as `parentAddress` in `DipcoinClient(...)`.
- For Solana, both the sub-account and `parentAddress` are Solana addresses. The JWT is issued for the signing sub-account, while query/body `parentAddress` remains the raw parent Solana address.
- When you use the **main wallet** mnemonic or private key directly, you normally **do not** need `parentAddress`; the client defaults it from your own address. This is supported for compatibility, but API-wallet signing is recommended for routine use.

Example (sub-account key + main wallet as parent), see `examples/test_sui_taker_pingpong.py`:

```python
client = DipcoinClient(
    True,
    Networks["SUI_STAGING"],  # use Networks["SUI_PROD"] on mainnet
    TEST_ACCT_KEY,  # sub-account / API trading key
    parentAddress="0x...main_wallet_address...",
)
```

For **mainnet**, pass `Networks["SUI_PROD"]` as the second argument instead of `SUI_STAGING` (see `src/dipcoin_client/constants.py`).

### Direct Sui chain access

Direct Sui chain access is not part of the core client workflow, and the examples focus on Dipcoin API/relayer operations. The optional `SuiGraphQLClient` module remains available for users who specifically need low-level Sui GraphQL reads or transaction submission; it does not provide PTB construction. For routine product operations, use Dipcoin relayer methods instead.

If local Sui PTB construction becomes important, evaluate community tooling such as `pysui` or the Java reference implementation in `sui4j` as a separate package instead of adding native dependencies to this client.

Add/remove margin uses the Dipcoin relayer for Sui, Solana, and all supported EVM chains:

```python
await client.add_margin(MARKET_SYMBOLS.ETH, "1")
await client.remove_margin(MARKET_SYMBOLS.ETH, "0.5")
```

Before removing margin, the SDK can estimate the maximum from a humanized
position snapshot. The helper uses `fundingDue` and mirrors the protocol's
10^18 fixed-point arithmetic:

```python
from dipcoin_client import calculate_max_removable_margin

response = await client.get_user_position({"symbol": MARKET_SYMBOLS.ETH})
position = response["data"][0]
maximum = calculate_max_removable_margin(position)
conservative = calculate_max_removable_margin(position, safety_factor="0.98")
```

The value is only an estimate: oracle price and unsettled funding may change
before the relayer executes the removal. The optional `0.98` factor matches the
current backend safety buffer.

### API numeric scaling (10¹⁸)

Read endpoints such as order book, ticker, exchange info, orders, positions, trades, funding history, and account data now convert known 10¹⁸ fixed-point fields into human-readable strings without losing precision.

Websocket payloads for ticker, order book, recent trades, and known user / market update topics are also normalized before your listener callback receives them, so websocket handling stays consistent with REST reads.

Order placement and signatures still accept human-readable inputs and convert request fields to base-18 integers before submitting.

### Update: take profit & stop loss (plan orders)

The client supports **position-linked TP/SL plan orders** (single side per request: either TP or SL, not both; additive flow rather than editing existing plans in one call):

- `DipcoinClient.set_take_profit_plan(...)` — submit a take-profit plan close order (signed like a normal reduce-only order via `create_signed_order`).
- `DipcoinClient.set_stop_loss_plan(...)` — same for stop-loss.
- `DipcoinClient.get_position_tpsl_plans(position_id, tpsl_type, parent_address=...)` — list TP/SL plans for a position (`tpsl_type`: `"normal"` or `"position"`).

Human-readable prices and quantities should be aligned to the contract tick/step (or decimal precision) **before** calling these methods. You can use `normalize_price` / `normalize_qty` in `dipcoin_client.util` for simple `round(..., precision)` style formatting, or apply tick/step rounding in your strategy.

**`get_orders` and plan order types:** responses can include **ordinary limit/market orders and plan (TP/SL) orders** in the same list. Use the order field **`planOrderType`** to tell them apart:

| `planOrderType` | Meaning |
|-----------------|--------|
| `open` | Regular  order（open/close） |
| `takeProfit` | Take-profit plan order |
| `stopLoss` | Stop-loss plan order |

Filter or branch on this field when you only want classic working orders or only TP/SL plans.

### Getting productive quickly

If you run into integration issues, **LLM / AI coding assistants** work well with this repo: point the tool at **`examples/`** and this README so it can map patterns (initialization, signing, orders, `parentAddress`) to your use case.

## Project Structure

```
diptrade-perp-client-python/
├── src/
│   ├── dipcoin_client/      # Main client package
│   └── sui_utils/            # SUI blockchain utilities
├── examples/                 # Example code
├── tests/                    # Test code
├── pyproject.toml           # Project configuration
└── requirements.in          # Dependencies list
```

## Troubleshooting

### Issue: coincurve Installation Error

**Solution**:
```bash
source venv/bin/activate
pip uninstall coincurve -y
pip install --no-cache-dir --force-reinstall coincurve==17.0.0
```

### Issue: Import Errors in PyCharm

**Error**: `ModuleNotFoundError: No module named 'sui_utils'`

**Solutions**:
1. Ensure `pip install -e .` has been run
2. Mark `src` directory as Sources Root in PyCharm
3. Configure Python interpreter paths correctly
4. Invalidate caches and restart PyCharm

### Issue: Build Errors

**Error**: `error: subprocess-exited-with-error`

**Solutions**:
1. Check Python version (should be 3.8-3.12)
2. Upgrade pip and setuptools:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```
3. Install build tools:
   ```bash
   # macOS
   xcode-select --install
   
   # Ubuntu/Debian
   sudo apt-get install build-essential python3-dev
   ```

## Quick Reference

```bash
# Install project (development mode)
pip install -e .

# Uninstall project
pip uninstall dipcoin-client

# Check installed package
pip show dipcoin-client

# Upgrade pip
pip install --upgrade pip

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
```

## Notes

- **Python Version**: Use Python 3.8-3.12. Python 3.13 is not supported.
- **Virtual Environment**: Always use a virtual environment to isolate dependencies.
- **Security**: Never commit private keys or mnemonic phrases to version control.
- **Dependencies**: If you modify `pyproject.toml`, reinstall with `pip install -e .`

## License

See LICENSE file for details.
