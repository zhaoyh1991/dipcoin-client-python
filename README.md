# Dipcoin Python Client

A simple Python client library for interacting with the Dipcoin perp protocol, including its off-chain API gateway and on-chain contracts.

## What's New in 1.2.0

- Added Solana wallet support for onboarding plus v2 order/cancel signing.
- Added preparatory ETH wallet signing support in the client for future Dipcoin enablement.
- Kept Sui compatibility on the legacy v1 signing flow.
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
pip install dipcoin_client_sui
```

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
TEST_ACCT_KEY = "your_mnemonic_phrase"  # or hex private key, suiprivkey bech32, etc.
TEST_NETWORK = "SUI_STAGING"  # mainnet: use "SUI_PROD"
```

**⚠️ Security Warning**: The `TEST_ACCT_KEY` in `examples/config.py` is a secret (mnemonic or private key). Keep it secure and never commit it to version control.

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
        "your_mnemonic_phrase"
    )
    await client.init(True)
    print("Account Address:", client.get_public_address())

if __name__ == "__main__":
    asyncio.run(main())
```

### ETH and Solana wallets

Use `wallet_type="solana"` to onboard and sign v2 order/cancel payloads today. `wallet_type="eth"` is implemented in the client as a preparatory integration, but Dipcoin does not currently support ETH wallets in production yet. Sui remains on the legacy v1 signature format for backward compatibility.

```python
client = DipcoinClient(True, Networks["SUI_PROD"], "0x...eth_private_key", wallet_type="eth")
await client.init(True)
```

Solana accepts a 32-byte seed or 64-byte keypair encoded as hex, base64, base58, or a JSON byte array.

### Wallet credentials (mnemonic or private key)

`DipcoinClient` accepts either:

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
- When you use the **main wallet** mnemonic or private key directly, you normally **do not** need `parentAddress`; the client defaults it from your own address.

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

### Sui GraphQL helpers

Direct Sui chain methods are no longer exposed on `DipcoinClient`. Use `SuiGraphQLClient` for lightweight direct Sui reads and GraphQL transaction submission without native dependencies.

```python
from dipcoin_client import DipcoinClient, Networks, SuiGraphQLClient

client = DipcoinClient(True, Networks["SUI_PROD"], PRIVATE_KEY)
await client.init(True)
sui_chain = SuiGraphQLClient(client)
balance = await sui_chain.get_native_chain_token_balance()
```

GraphQL execution is available through `SuiGraphQLClient.execute_transaction(transaction_data_bcs, signatures)`. Local PTB construction is not bundled because direct Sui writes are not a core SDK requirement and most product flows should go through Dipcoin relayers.

If local Sui PTB construction becomes important, evaluate community tooling such as `pysui` or the Java reference implementation in `sui4j` as a separate package instead of adding native dependencies to this client.

For new add/remove margin integrations, prefer `DipcoinClient.create_margin_relay_signature(...)` and submit the signed payload through backend relayer APIs once available.

### API numeric scaling (10¹⁸)

Read endpoints such as order book, ticker, exchange info, orders, positions, trades, funding history, and account data now convert known 10¹⁸ fixed-point fields into human-readable strings without losing precision.

Websocket payloads for ticker, order book, recent trades, and known user / market update topics are also normalized before your listener callback receives them, so websocket handling stays consistent with REST reads.

Order placement and signatures still accept human-readable inputs and convert request fields to base-18 integers before submitting.

### Publishing to PyPI

```bash
python -m pip install --upgrade build twine
rm -rf build dist
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

For TestPyPI, use `python -m twine upload --repository testpypi dist/*`. Ensure `pyproject.toml` has the intended version before building.

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
dipcoin-client-python/
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
pip uninstall dipcoin_client_sui

# Check installed package
pip show dipcoin_client_sui

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
