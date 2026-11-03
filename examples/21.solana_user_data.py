import asyncio
import os
from pprint import pprint

from config import TEST_NETWORK
from dipcoin_client import DipcoinClient, MARKET_SYMBOLS, Networks


SOLANA_PARENT_ADDRESS_ENV = "DIPCOIN_SOLANA_PARENT_ADDRESS"
SOLANA_API_ADDRESS_ENV = "DIPCOIN_SOLANA_API_ADDRESS"
SOLANA_PRIVATE_KEY_ENV = "DIPCOIN_SOLANA_API_PRIVATE_KEY"


async def main():
    parent_address = os.getenv(SOLANA_PARENT_ADDRESS_ENV)
    api_address = os.getenv(SOLANA_API_ADDRESS_ENV)
    private_key = os.getenv(SOLANA_PRIVATE_KEY_ENV)
    for variable_name, value in (
        (SOLANA_PARENT_ADDRESS_ENV, parent_address),
        (SOLANA_API_ADDRESS_ENV, api_address),
        (SOLANA_PRIVATE_KEY_ENV, private_key),
    ):
        if not value:
            raise RuntimeError(f"Set {variable_name} before running this example")

    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        private_key,
        parentAddress=parent_address,
        wallet_type="solana",
    )
    await client.init(True)

    assert client.get_public_address() == api_address
    print("sub_account:", client.get_public_address())
    print("parentAddress:", parent_address)

    orders = await client.get_orders({})
    print("Solana sub-account orders:")
    pprint(orders)

    position = await client.get_user_position({"symbol": MARKET_SYMBOLS.BTC})
    print("Solana parent position:")
    pprint(position)

    trades = await client.get_user_trades({"symbol": MARKET_SYMBOLS.BTC})
    print("Solana parent trades:")
    pprint(trades)

    account_data = await client.get_user_account_data()
    print("Solana parent account data:")
    pprint(account_data)

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
