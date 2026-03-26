import base64
import binascii
from datetime import datetime
from random import randint
import time
import random

from eth_utils import from_wei, to_wei

# from web3 import Web3
import time
from typing import Union
import bip_utils
import hashlib
import json

BASE_1E18 = 1000000000000000000
BASE_1E6 = 1000000  # 1e6 for USDC token
BASE_1E9 = 1000000000
SUI_STRING_OBJECT_TYPE = "0x1::string::String"
SUI_CUSTOM_OBJECT_TYPE = "0x1::type_name::TypeName"
SUI_NATIVE_PACKAGE_ID = "0x2"


def getsha256Hash(callArgs: list) -> str:
    callArgsJson = json.dumps(callArgs).encode("utf-8")
    return hashlib.sha256(callArgsJson).digest().hex()


def to_base18(number: Union[int, float]) -> int:
    """Takes in a number and multiples it by 1e18"""
    return to_wei(number, "ether")


def from1e18(number: Union[str, int]) -> float:
    """Takes in a number and divides it by 1e18"""
    return float(from_wei(int(number), "ether"))


def fromSuiBase(number: Union[str, int]) -> float:
    """Takes in a number and divides it by 1e9"""
    ## gwei is base9 and sui is also base9
    return float(from_wei(int(number), "gwei"))


def toSuiBase(number: Union[str, int]) -> int:
    """Takes in a number and multiplies it by 1e9"""
    return to_wei(number, "gwei")


def toUsdcBase(number: Union[int, float]) -> int:
    """Converts a number to usdc contract onchain representation i.e. multiply it by 1e6"""
    return to_wei(number, "mwei")


def fromUsdcBase(number: Union[str, int]) -> float:
    """Converts a usdc quantity to number i.e. divide it by 1e6"""
    return float(from_wei(int(number), "mwei"))


def numberToHex(num, pad=32):
    hexNum = hex(num)
    # padding it with zero to make the size 32 bytes
    padHex = hexNum[2:].zfill(pad)
    return padHex


def getSalt() -> int:
    return (
        int(time.time())
        + random.randint(0, 1000000)
        + random.randint(0, 1000000)
        + random.randint(0, 1000000)
    )


def hexToByteArray(hexStr):
    return bytearray.fromhex(hexStr)


def mnemonicToPrivateKey(seedPhrase: str) -> bytes:
    """BIP39 seed → SLIP-0010 Ed25519 at m/44'/784'/0'/0'/0'; returns 32-byte secret (matches Sui wallets)."""
    bip39_seed = bip_utils.Bip39SeedGenerator(seedPhrase).Generate()
    bip32_ctx = bip_utils.Bip32Slip10Ed25519.FromSeed(bip39_seed)
    derivation_path = "m/44'/784'/0'/0'/0'"
    bip32_der_ctx = bip32_ctx.DerivePath(derivation_path)
    raw = bip32_der_ctx.PrivateKey().Raw()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if isinstance(raw, str) and len(raw) == 64:
        return binascii.unhexlify(raw)
    return bytes(raw)


def privateKeyToPublicKey(privateKey: str) -> str:
    if type(privateKey) is str:
        privateKeyBytes = binascii.unhexlify(privateKey)
    else:
        privateKeyBytes = bytes(privateKey)

    bip32_ctx = bip_utils.Bip32Slip10Ed25519.FromPrivateKey(privateKeyBytes)
    public_key: str = bip32_ctx.PublicKey().RawCompressed()
    return public_key


# Flags match ``sui_types::crypto::SignatureScheme`` for address derivation.
SUI_SIGNATURE_SCHEME_ED25519 = 0x00
SUI_SIGNATURE_SCHEME_SECP256K1 = 0x01


def getAddressFromPublicKey(publicKey, scheme_flag: int = SUI_SIGNATURE_SCHEME_ED25519) -> str:
    """
    Sui address = BLAKE2b-256(scheme_flag || raw_public_key); see
    ``impl From<&PublicKey> for SuiAddress`` (``pk.flag()`` then ``pk``).
    """
    if type(publicKey) is str:
        publicKeyBytes = binascii.unhexlify(publicKey)
    else:
        publicKeyBytes = bytes(publicKey)
    preimage = bytes([scheme_flag & 0xFF]) + publicKeyBytes
    address: str = (
        "0x" + hashlib.blake2b(preimage, digest_size=32).digest().hex()[:]
    )
    return address


# --- suiprivkey (SIP-15, BIP-173 Bech32) and hex/base64 private key imports ---

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_verify_checksum(hrp: str, data: list) -> bool:
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == 1


def _bech32_decode(bech: str):
    """Return (hrp, data_5bit_without_checksum) or (None, None). BIP-0173."""
    if any(ord(x) < 33 or ord(x) > 126 for x in bech):
        return None, None
    if bech.lower() != bech and bech.upper() != bech:
        return None, None
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 120:
        return None, None
    if not all(x in _BECH32_CHARSET for x in bech[pos + 1 :]):
        return None, None
    hrp = bech[:pos]
    data = [_BECH32_CHARSET.find(x) for x in bech[pos + 1 :]]
    if not _bech32_verify_checksum(hrp, data):
        return None, None
    return hrp, data[:-6]


def _convertbits(data: list, frombits: int, tobits: int, pad: bool = True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _decode_suiprivkey_bech32(s: str) -> bytes:
    hrp, data_5 = _bech32_decode(s.strip())
    if hrp is None or hrp != "suiprivkey":
        raise ValueError("Invalid suiprivkey bech32 string")
    payload = _convertbits(data_5, 5, 8, False)
    if payload is None or len(payload) != 33:
        raise ValueError("Invalid suiprivkey payload length")
    if payload[0] != 0:
        raise ValueError(
            "Only ED25519 private keys (scheme 0) are supported; got scheme %s"
            % payload[0]
        )
    return bytes(payload[1:])


def parse_sui_private_key_export(secret: str) -> bytes:
    """
    Parse a Sui-exported key into a 32-byte Ed25519 secret:
      - 64 hex digits (optional 0x prefix)
      - base64 / URL-safe base64: 32 bytes, or 33 bytes with leading 0x00
      - ``suiprivkey1...`` (SIP-15 Bech32)
    """
    s = secret.strip()
    if not s:
        raise ValueError("Empty private key")

    if s.lower().startswith("suiprivkey"):
        return _decode_suiprivkey_bech32(s)

    hexpart = s[2:] if s.startswith(("0x", "0X")) else s
    if len(hexpart) == 64 and all(
        c in "0123456789abcdefABCDEF" for c in hexpart
    ):
        return binascii.unhexlify(hexpart)

    for dec in (base64.b64decode, base64.urlsafe_b64decode):
        for candidate in (s, s + "=" * ((4 - len(s) % 4) % 4)):
            try:
                raw = dec(candidate)
            except Exception:
                continue
            if len(raw) == 32:
                return raw
            if len(raw) == 33 and raw[0] == 0:
                return raw[1:]

    raise ValueError(
        "Unrecognized private key format; use hex, base64, or suiprivkey bech32"
    )


def ed25519_public_key_bytes_from_bip_utils(secret_key_bytes: bytes) -> bytes:
    """Same public key derivation as ``privateKeyToPublicKey`` via bip_utils; do not mix with NaCl signing."""
    pk = privateKeyToPublicKey(secret_key_bytes)
    return binascii.unhexlify(pk) if isinstance(pk, str) else bytes(pk)


def strip_hex_prefix(input):
    if input[0:2] == "0x":
        return input[2:]
    else:
        return input


def address_to_bytes32(addr):
    return "0x000000000000000000000000" + strip_hex_prefix(addr)


def bn_to_bytes8(value: int):
    return str("0x" + "0" * 16 + hex(value)[2:]).encode("utf-8")


def default_value(dict, key, default_value):
    if key in dict:
        return dict[key]
    else:
        return default_value


def default_enum_value(dict, key, default_value):
    if key in dict:
        return dict[key].value
    else:
        return default_value.value


def current_unix_timestamp():
    return int(datetime.now().timestamp())


def random_number(max_range):
    return current_unix_timestamp() + randint(0, max_range) + randint(0, max_range)


def extract_query(value: dict):
    query = ""
    for i, j in value.items():
        query += "&{}={}".format(i, j)
    return query[1:]


def extract_enums(params: dict, enums: list):
    for i in enums:
        if i in params.keys():
            if type(params[i]) == list:
                params[i] = [x.value for x in params[i]]
            else:
                params[i] = params[i].value
    return params


def config_logging(logging, logging_level, log_file: str = None):
    """Configures logging to provide a more detailed log format, which includes date time in UTC
    Example: 2021-11-02 19:42:04.849 UTC <logging_level> <log_name>: <log_message>
    Args:
        logging: python logging
        logging_level (int/str): For logging to include all messages with log levels >= logging_level. Ex: 10 or "DEBUG"
                                 logging level should be based on https://docs.python.org/3/library/logging.html#logging-levels
    Keyword Args:
        log_file (str, optional): The filename to pass the logging to a file, instead of using console. Default filemode: "a"
    """

    logging.Formatter.converter = time.gmtime  # date time in GMT/UTC
    logging.basicConfig(
        level=logging_level,
        filename=log_file,
        format="%(asctime)s.%(msecs)03d UTC %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def decimal_to_bcs(num):
        # Initialize an empty list to store the BCS bytes
        bcs_bytes = []
        while num > 0:
            # Take the last 7 bits of the number
            bcs_byte = num & 0x7F

            # Set the most significant bit (MSB) to 1 if there are more bytes to follow
            if num > 0x7F:
                bcs_byte |= 0x80

            # Append the BCS byte to the list
            bcs_bytes.append(bcs_byte)

            # Right-shift the number by 7 bits to process the next portion
            num >>= 7

        return bcs_bytes

def read_json(file_path: str | None = None) -> dict:
    """
    Reads a JSON file and returns the data as a dictionary.
    Input:
        file_path: optional path to the JSON file, defaults to './rfq-contracts.json'
    Output:
        Returns the data as a dictionary.
    """
    try:
        if file_path is None:
            file_path = './rfq-contracts.json'
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"could not read JSON: {e}")