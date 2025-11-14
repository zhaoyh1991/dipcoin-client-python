# Dipcoin Python Client

A simple Python client library for interacting with the Dipcoin perp protocol, including its off-chain API gateway and on-chain contracts.

## Requirements

- Python 3.8 - 3.12 (recommended: Python 3.11)
- Note: Python 3.13 is not supported due to gevent compatibility issues

## Installation

### 1. Create Virtual Environment (Recommended)

```bash
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install dependencies
pip install -r requirements.in
```

### 3. Install Project in Development Mode

```bash
pip install -e .
```

This installs the project in editable mode, so code changes take effect immediately without reinstalling.

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
TEST_ACCT_KEY = "your_mnemonic_phrase"  # Keep this secure!
TEST_NETWORK = "SUI_STAGING"  # or "SUI_MAINNET"
```

**⚠️ Security Warning**: The `TEST_ACCT_KEY` in `examples/config.py` contains your seed phrase . Keep it secure and never commit it to version control.

### Run Examples

```bash
cd examples
python 1.initialization.py
```

### Basic Usage

```python
from dipcoin_client import BluefinClient, Networks
import asyncio

async def main():
    client = BluefinClient(
        True,  # Agree to terms and conditions
        Networks["SUI_STAGING"],
        "your_mnemonic_phrase"
    )
    await client.init(True)
    print("Account Address:", client.get_public_address())

if __name__ == "__main__":
    asyncio.run(main())
```

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

### Issue: gevent Compilation Error (Python 3.13)

**Error**: `undeclared name not builtin: long`

**Solution**: Use Python 3.8-3.12 instead of Python 3.13.

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