"""
    This example shows how users can get their orders information.
    The get_orders route provides a number of optional params that can be 
    mixed together to fetch the exact data that user needs.
"""
import sys, os

# sys.path.append(os.getcwd() + "/src/")
from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_STATUS,
    ORDER_TYPE,
)
import asyncio


async def main():
    client = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
    await client.init(True)

    print("Get all ETH market orders regardless of their type/status")
    orders = await client.get_orders(
        {
            "symbol": MARKET_SYMBOLS.ETH,
        }
    )
    print("Received orders: ", orders)


    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
