import unittest
from unittest.mock import AsyncMock

from dipcoin_client import DipcoinClient, Networks
from dipcoin_client.order_signer import OrderSigner
from dipcoin_client.wallets import (
    ARBITRUM_CHAIN_ID,
    BASE_CHAIN_ID,
    ETH_CHAIN_ID,
    EVM_PERSONAL_SIGN_SCHEME,
    OPTIMISM_CHAIN_ID,
    POLYGON_CHAIN_ID,
    create_wallet_account,
    display_address,
)


PRIVATE_KEY = "0x" + "01" * 32
EVM_CHAINS = {
    "eth": (ETH_CHAIN_ID, "Ethereum"),
    "arbitrum": (ARBITRUM_CHAIN_ID, "Arbitrum"),
    "optimism": (OPTIMISM_CHAIN_ID, "Optimism"),
    "base": (BASE_CHAIN_ID, "Base"),
    "polygon": (POLYGON_CHAIN_ID, "Polygon"),
}


class EvmWalletChainTest(unittest.TestCase):
    def test_all_evm_chains_keep_scheme_four_and_use_chain_prefix(self):
        addresses = set()

        for wallet_type, (chain_id, prefix) in EVM_CHAINS.items():
            with self.subTest(wallet_type=wallet_type):
                account = create_wallet_account(PRIVATE_KEY, wallet_type)
                addresses.add(account.address)

                self.assertEqual(chain_id, account.chain_id)
                self.assertEqual(EVM_PERSONAL_SIGN_SCHEME, account.scheme)
                self.assertIn("-4-", account.sign_message(b"test"))
                self.assertEqual(
                    f"{prefix}:{account.address}",
                    display_address(account.chain_id, account.address),
                )

        self.assertEqual(1, len(addresses))

    def test_explicit_protocol_chain_id_selects_evm_chain(self):
        account = create_wallet_account(
            PRIVATE_KEY,
            "eth",
            protocol_chain_id=BASE_CHAIN_ID,
        )

        self.assertEqual(BASE_CHAIN_ID, account.chain_id)
        self.assertEqual(EVM_PERSONAL_SIGN_SCHEME, account.scheme)

    def test_rejects_eip_155_chain_id(self):
        with self.assertRaisesRegex(ValueError, "1, 3, 4, 5, 6"):
            create_wallet_account(
                PRIVATE_KEY,
                "eth",
                protocol_chain_id=42161,
            )

    def test_order_payload_uses_selected_evm_prefix(self):
        account = create_wallet_account(PRIVATE_KEY, "arbitrum")
        serialized = OrderSigner().get_serialized_order(
            {
                "market": "0xmarket",
                "marketEpoch": 7,
                "creator": account.address,
                "isLong": True,
                "reduceOnly": False,
                "postOnly": False,
                "orderbookOnly": True,
                "ioc": False,
                "quantity": 1,
                "price": 2,
                "leverage": 3,
                "expiration": 0,
                "salt": 4,
            },
            payload_version=3,
            wallet_chain_id=account.chain_id,
        )

        self.assertIn(
            f'"creator":"Arbitrum:{account.address}"',
            serialized,
        )


class EvmAuthorizationTest(unittest.IsolatedAsyncioTestCase):
    async def test_authorize_sends_protocol_chain_id(self):
        client = DipcoinClient(
            True,
            Networks["SUI_STAGING"],
            PRIVATE_KEY,
            wallet_type="optimism",
        )
        client.apis.post = AsyncMock(return_value={"code": 200})

        try:
            await client.authorize_signed_hash("signature-4-address")
            client.apis.post.assert_awaited_once_with(
                "/api/authorize",
                {
                    "signature": "signature-4-address",
                    "userAddress": client.get_public_address(),
                    "isTermAccepted": True,
                    "chainId": OPTIMISM_CHAIN_ID,
                },
            )
        finally:
            await client.close_connections()


if __name__ == "__main__":
    unittest.main()
