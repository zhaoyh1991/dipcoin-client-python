import base64
import binascii

from nacl.signing import SigningKey

from .enumerations import WALLET_SCHEME
from .utilities import (
    SUI_SIGNATURE_SCHEME_ED25519,
    SUI_SIGNATURE_SCHEME_SECP256K1,
    ed25519_public_key_bytes_from_bip_utils,
    getAddressFromPublicKey,
    mnemonicToPrivateKey,
    parse_sui_private_key_export,
)


class SuiWallet:
    def __init__(
        self,
        seed: str = "",
        privateKey: str = "",
        scheme: WALLET_SCHEME = WALLET_SCHEME.ED25519,
    ):
        if seed and privateKey:
            raise ValueError("Provide either seed (mnemonic) or privateKey, not both")
        if not seed and not privateKey:
            raise ValueError("Either seed or privateKey is required")

        if seed:
            sk_bytes = mnemonicToPrivateKey(seed)
        else:
            sk_bytes = parse_sui_private_key_export(privateKey)

        if len(sk_bytes) != 32:
            raise ValueError(
                "Ed25519 secret key must be 32 bytes, got %s" % len(sk_bytes)
            )

        self.scheme = scheme
        self.privateKeyBytes = sk_bytes
        self.privateKey = binascii.hexlify(sk_bytes).decode()
        self.key = self.privateKey

        if scheme == WALLET_SCHEME.ED25519:
            pk_bytes = SigningKey(sk_bytes).verify_key.encode()
            addr_scheme = SUI_SIGNATURE_SCHEME_ED25519
        else:
            pk_bytes = ed25519_public_key_bytes_from_bip_utils(sk_bytes)
            addr_scheme = SUI_SIGNATURE_SCHEME_SECP256K1

        self.publicKeyBytes = pk_bytes
        self.publicKey = binascii.hexlify(pk_bytes).decode()
        self.publicKeyBase64 = base64.b64encode(pk_bytes)
        self.privateKeyBase64 = base64.b64encode(sk_bytes)
        self.address = getAddressFromPublicKey(pk_bytes, scheme_flag=addr_scheme)

    def getPublicKey(self) -> str:
        return self.publicKey

    def getPrivateKey(self) -> str:
        return self.privateKey

    def getUserAddress(self):
        return self.address

    def getKeyScheme(self):
        return self.scheme
