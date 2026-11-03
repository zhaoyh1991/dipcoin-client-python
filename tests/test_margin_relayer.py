import unittest
from unittest.mock import AsyncMock, Mock, patch

from dipcoin_client import ADJUST_MARGIN, DipcoinClient, Networks
from dipcoin_client.wallets import display_address


NOW_MS = 1_700_000_000_000
EXPIRATION = NOW_MS + 300_000
MARKET = "0x" + "ab" * 32
SYMBOL = "ETH-PERP"
SUI_KEY = "0x" + "03" * 32
SOLANA_KEY = "0x" + "02" * 32
EVM_KEY = "0x" + "01" * 32

CHAIN_CASES = (
    ("sui", SUI_KEY, 0, "Sui", 65, 32, "01"),
    ("eth", EVM_KEY, 1, "Ethereum", 66, 33, "04"),
    ("solana", SOLANA_KEY, 2, "Solana", 65, 32, "05"),
    ("arbitrum", EVM_KEY, 3, "Arbitrum", 66, 33, "04"),
    ("optimism", EVM_KEY, 4, "Optimism", 66, 33, "04"),
    ("base", EVM_KEY, 5, "Base", 66, 33, "04"),
    ("polygon", EVM_KEY, 6, "Polygon", 66, 33, "04"),
)


def create_client(wallet_type, private_key, parent_address=""):
    client = DipcoinClient(
        True,
        Networks["SUI_STAGING"],
        private_key,
        parentAddress=parent_address,
        wallet_type=wallet_type,
    )
    client.contracts.contract_info = {SYMBOL: {"perpId": MARKET}}
    return client


class MarginRelayRequestTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_protocol_chains_build_standard_relayer_request(self):
        for (
            wallet_type,
            private_key,
            chain_id,
            prefix,
            signature_length,
            public_key_length,
            scheme_hex,
        ) in CHAIN_CASES:
            with self.subTest(wallet_type=wallet_type):
                client = create_client(wallet_type, private_key)
                signer = Mock(wraps=client.account.sign_relay_message)
                client.account.sign_relay_message = signer
                try:
                    with patch(
                        "dipcoin_client.client.time.time",
                        return_value=NOW_MS / 1000,
                    ):
                        request = client.create_margin_relay_request(
                            SYMBOL,
                            ADJUST_MARGIN.ADD,
                            "1.25",
                            salt=12345,
                            expiration=EXPIRATION,
                        )

                    self.assertEqual(
                        {"action", "user", "params", "signature", "publicKey"},
                        set(request),
                    )
                    self.assertEqual("AddMargin", request["action"])
                    self.assertEqual(chain_id, request["user"]["chainId"])
                    self.assertTrue(request["user"]["rawAddress"].startswith("0x"))
                    self.assertEqual(MARKET, request["params"]["market"])
                    self.assertEqual(SYMBOL, request["params"]["symbol"])
                    self.assertEqual(
                        "1250000000000000000", request["params"]["amount"]
                    )
                    self.assertEqual("12345", request["params"]["salt"])
                    self.assertEqual(EXPIRATION, request["params"]["expiration"])

                    signature = bytes.fromhex(request["signature"][2:])
                    public_key = bytes.fromhex(request["publicKey"][2:])
                    self.assertEqual(signature_length, len(signature))
                    self.assertEqual(scheme_hex, request["signature"][-2:])
                    self.assertEqual(public_key_length, len(public_key))

                    payload = signer.call_args.args[0].decode("utf-8")
                    expected_display = display_address(
                        chain_id, client.parentAddress
                    )
                    self.assertEqual(
                        "{\n"
                        '"action":"AddMargin",\n'
                        f'"market":"{MARKET}",\n'
                        f'"user":"{expected_display}",\n'
                        '"amount":"1250000000000000000",\n'
                        '"salt":"12345",\n'
                        f'"expiration":"{EXPIRATION}",\n'
                        '"domain":"dipcoin.io"\n'
                        "}",
                        payload,
                    )
                    self.assertTrue(
                        expected_display.startswith(f"{prefix}:")
                    )
                finally:
                    await client.close_connections()

    async def test_parent_address_is_separate_from_api_signer(self):
        parent = "0x72cfe0e5e4de41b23dc998de9e5160f65e18eda0"
        client = create_client("eth", EVM_KEY, parent)
        try:
            with patch(
                "dipcoin_client.client.time.time",
                return_value=NOW_MS / 1000,
            ):
                request = client.create_margin_relay_request(
                    SYMBOL,
                    ADJUST_MARGIN.REMOVE,
                    "0.5",
                    salt=54321,
                    expiration=EXPIRATION,
                )

            self.assertNotEqual(parent, client.account.address)
            self.assertEqual(parent, request["user"]["rawAddress"])
            self.assertEqual("RemoveMargin", request["action"])
            self.assertEqual("500000000000000000", request["params"]["amount"])
        finally:
            await client.close_connections()

    async def test_add_and_remove_margin_submit_to_relayer(self):
        client = create_client("eth", EVM_KEY)
        client._auth_post = AsyncMock(
            return_value={"code": 200, "data": {"digest": "digest"}}
        )
        try:
            with patch(
                "dipcoin_client.client.time.time",
                return_value=NOW_MS / 1000,
            ):
                add_response = await client.add_margin(
                    SYMBOL, "1", salt=1, expiration=EXPIRATION
                )
                remove_response = await client.remove_margin(
                    SYMBOL, "0.25", salt=2, expiration=EXPIRATION
                )

            self.assertEqual("digest", add_response["data"]["digest"])
            self.assertEqual("digest", remove_response["data"]["digest"])
            self.assertEqual(2, client._auth_post.await_count)
            add_call, remove_call = client._auth_post.await_args_list
            self.assertEqual("/api/perp-relayer/v1/relay", add_call.args[0])
            self.assertEqual("AddMargin", add_call.args[1]["action"])
            self.assertEqual("RemoveMargin", remove_call.args[1]["action"])
        finally:
            await client.close_connections()

    async def test_rejects_invalid_margin_requests_before_signing(self):
        client = create_client("eth", EVM_KEY)
        try:
            with patch(
                "dipcoin_client.client.time.time",
                return_value=NOW_MS / 1000,
            ):
                with self.assertRaisesRegex(ValueError, "operation must be"):
                    client.create_margin_relay_request(
                        SYMBOL, "ADD", "1", expiration=EXPIRATION
                    )
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    client.create_margin_relay_request(
                        SYMBOL,
                        ADJUST_MARGIN.ADD,
                        "0",
                        expiration=EXPIRATION,
                    )
                with self.assertRaisesRegex(ValueError, "future"):
                    client.create_margin_relay_request(
                        SYMBOL,
                        ADJUST_MARGIN.ADD,
                        "1",
                        expiration=NOW_MS,
                    )
                with self.assertRaisesRegex(ValueError, "within one hour"):
                    client.create_margin_relay_request(
                        SYMBOL,
                        ADJUST_MARGIN.ADD,
                        "1",
                        expiration=NOW_MS + 3_600_001,
                    )
        finally:
            await client.close_connections()


if __name__ == "__main__":
    unittest.main()
