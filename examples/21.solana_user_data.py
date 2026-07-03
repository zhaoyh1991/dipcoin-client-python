import asyncio
from pprint import pprint

from config import TEST_NETWORK
from dipcoin_client import DipcoinClient, MARKET_SYMBOLS, Networks


SOLANA_PARENT_ADDRESS = "2ERFGBW7XG3jTuMYHf7JD4nPSauKV4eV3sk8aCjENeQw"
SOLANA_SUB_ACCOUNT_ADDRESS = "FUrJrAezwXjmwq2DfAAYJ2XKk4V6Z1GfySZdEQFWmAEW"
SOLANA_SUB_ACCOUNT_PRIVATE_KEY = "4f7Gi71DQAZyiBzMES4fBSdBF3xhRtiXDzSNQKwWnELr3191MKoD4yfXKDsSxAHv9uDSNzC5pkNzEEVREGfyKVbG"


async def main():
    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        SOLANA_SUB_ACCOUNT_PRIVATE_KEY,
        parentAddress=SOLANA_PARENT_ADDRESS,
        wallet_type="solana",
    )
    await client.init(True)

    assert client.get_public_address() == SOLANA_SUB_ACCOUNT_ADDRESS
    print("sub_account:", client.get_public_address())
    print("parentAddress:", SOLANA_PARENT_ADDRESS)

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
