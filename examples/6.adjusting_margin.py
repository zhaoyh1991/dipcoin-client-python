from pprint import pprint
from config import TEST_ACCT_KEY, TEST_NETWORK
import asyncio
from dipcoin_client import (
    DipcoinClient,
    ADJUST_MARGIN,
    Networks,
    MARKET_SYMBOLS,
)


async def main():
    client = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
    await client.init(True)

    # Already open positions on exchange can be queried using
    position = await client.get_user_position({"symbol": MARKET_SYMBOLS.ETH})

    if not position:
        print("Account has no open position")
        return

    # Direct PTB construction is deferred. Submit this payload to the Dipcoin
    # relayer endpoint once it is available.
    pprint(
        client.create_margin_relay_signature(
            MARKET_SYMBOLS.ETH,
            ADJUST_MARGIN.ADD,
            1,
        )
    )

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
