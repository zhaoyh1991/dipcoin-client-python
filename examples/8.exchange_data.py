import sys, os

# sys.path.append(os.getcwd() + "/src/")
import time

from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    TRADE_TYPE,
    Interval,
)

import asyncio


async def main():
    client = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
    await client.init(True)

    # gets state of order book. Gets first 10 asks and bids
    orderbook = await client.get_orderbook({"symbol": MARKET_SYMBOLS.ETH})
    print(orderbook)

    # gets current funding rate on market
    funding_rate = await client.get_ticker_data(MARKET_SYMBOLS.ETH)
    print(funding_rate)

    # gets market data about min/max order size, oracle price, fee etc..
    exchange_info = await client.get_exchange_info(MARKET_SYMBOLS.ETH)
    print(exchange_info)

    # gets market candle info
    candle_data = await client.get_market_candle_stick_data(
        {"symbol": MARKET_SYMBOLS.ETH, "interval": Interval._1m, "startTime": int(time.time()) - 60 * 10,
         "endTime": int(time.time())}
    )
    print(candle_data)

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
