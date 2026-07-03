import base64
import binascii
import json
from dataclasses import dataclass
from typing import Optional

from nacl.signing import SigningKey

from sui_utils import SuiWallet


SUI_CHAIN_ID = 0
ETH_CHAIN_ID = 1
SOLANA_CHAIN_ID = 2

SUI_ED25519_SCHEME = "1"
ETH_PERSONAL_SIGN_SCHEME = "4"
SOLANA_ED25519_SCHEME = "5"

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _strip_0x(value: str) -> str:
    return value[2:] if value.startswith(("0x", "0X")) else value


def _b58encode(raw: bytes) -> str:
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number:
        number, rem = divmod(number, 58)
        encoded = _B58_ALPHABET[rem] + encoded
    leading_zeroes = len(raw) - len(raw.lstrip(b"\0"))
    return "1" * leading_zeroes + (encoded or "1")


def _b58decode(value: str) -> bytes:
    number = 0
    for char in value:
        number *= 58
        number += _B58_ALPHABET.index(char)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\0" * leading_zeroes + raw


def _parse_secret_key(value: str, prefer_base58: bool = False) -> bytes:
    key = value.strip()
    if key.startswith("["):
        return bytes(json.loads(key))
    if key.startswith(("0x", "0X")):
        return bytes.fromhex(key[2:])
    try:
        return bytes.fromhex(key)
    except ValueError:
        if prefer_base58:
            try:
                return _b58decode(key)
            except ValueError:
                pass
        try:
            return base64.b64decode(key, validate=True)
        except binascii.Error:
            return _b58decode(key)


def join_signature(sig_hex: str, scheme: str, pubkey_raw: bytes) -> str:
    return f"{sig_hex}-{scheme}-{base64.b64encode(pubkey_raw).decode()}"


@dataclass
class WalletAccount:
    address: str
    chain_id: int
    scheme: str

    def sign_message(self, message: bytes) -> str:
        raise NotImplementedError

    def getUserAddress(self) -> str:
        return self.address


class SuiWalletAccount(WalletAccount):
    def __init__(self, private_key: str):
        pk = private_key.strip()
        if _looks_like_bip39_mnemonic(pk):
            self.wallet = SuiWallet(seed=pk)
        else:
            self.wallet = SuiWallet(privateKey=pk)
        super().__init__(self.wallet.address.lower(), SUI_CHAIN_ID, SUI_ED25519_SCHEME)

    @property
    def privateKeyBytes(self):
        return self.wallet.privateKeyBytes

    @property
    def publicKeyBase64(self):
        return self.wallet.publicKeyBase64

    def sign_message(self, message: bytes) -> str:
        from sui_utils import Signer, decimal_to_bcs
        import hashlib

        intent = bytearray([3, 0, 0])
        intent.extend(decimal_to_bcs(len(message)))
        intent.extend(message)
        digest = hashlib.blake2b(intent, digest_size=32).digest()
        sig_hex = Signer().sign_hash(digest, self.privateKeyBytes, "")
        return join_signature(sig_hex, self.scheme, base64.b64decode(self.publicKeyBase64))


class EthWalletAccount(WalletAccount):
    def __init__(self, private_key: str):
        from coincurve import PrivateKey
        from eth_utils import keccak

        secret = _parse_secret_key(private_key)
        if len(secret) != 32:
            raise ValueError("ETH private key must be 32 bytes")
        self.private_key = PrivateKey(secret)
        public_key = self.private_key.public_key.format(compressed=False)[1:]
        address_bytes = keccak(public_key)[-20:]
        self.address_bytes = address_bytes
        super().__init__("0x" + address_bytes.hex(), ETH_CHAIN_ID, ETH_PERSONAL_SIGN_SCHEME)

    def sign_message(self, message: bytes) -> str:
        from eth_utils import keccak

        prefix = f"\x19Ethereum Signed Message:\n{len(message)}".encode()
        digest = keccak(prefix + message)
        sig = self.private_key.sign_recoverable(digest, hasher=None)
        return join_signature(sig.hex(), self.scheme, self.address_bytes)


class SolanaWalletAccount(WalletAccount):
    def __init__(self, private_key: str):
        secret = _parse_secret_key(private_key, prefer_base58=True)
        if len(secret) == 64:
            secret = secret[:32]
        if len(secret) != 32:
            raise ValueError("Solana private key must be 32-byte seed or 64-byte keypair")
        self.signing_key = SigningKey(secret)
        pubkey = bytes(self.signing_key.verify_key)
        self.pubkey = pubkey
        super().__init__(_b58encode(pubkey), SOLANA_CHAIN_ID, SOLANA_ED25519_SCHEME)

    def sign_message(self, message: bytes) -> str:
        sig = self.signing_key.sign(message).signature
        return join_signature(sig.hex(), self.scheme, self.pubkey)


def _looks_like_bip39_mnemonic(value: str) -> bool:
    words = value.split()
    return len(words) in (12, 15, 18, 21, 24) and all(word.isalpha() for word in words)


def create_wallet_account(private_key: str, wallet_type: Optional[str] = None) -> WalletAccount:
    normalized = (wallet_type or "sui").lower()
    if normalized in ("sui", "sui_ed25519"):
        return SuiWalletAccount(private_key)
    if normalized in ("eth", "ethereum", "evm"):
        return EthWalletAccount(private_key)
    if normalized in ("sol", "solana"):
        return SolanaWalletAccount(private_key)
    raise ValueError("wallet_type must be one of: sui, eth, solana")


def display_address(chain_id: int, address: str) -> str:
    if chain_id == SUI_CHAIN_ID:
        return "Sui:" + address.lower()
    if chain_id == ETH_CHAIN_ID:
        return "Ethereum:" + address.lower()
    if chain_id == SOLANA_CHAIN_ID:
        return "Solana:" + address
    raise ValueError(f"unsupported chain id: {chain_id}")
