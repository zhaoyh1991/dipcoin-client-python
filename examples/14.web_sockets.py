import sys, os

# sys.path.append(os.getcwd() + "/src/")
import time
from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    SOCKET_EVENTS,
    config_logging,
)
import asyncio
import logging

config_logging(logging, logging.DEBUG)

event_received = False


def callback(event):
    global event_received
    print("Event data:", event)
    event_received = True


async def main():
    client = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
    await client.init(True)

    def on_error(ws, error):
        print(error)

    def on_close(ws):
        # unsubscribe from global events
        status = client.ws_client.unsubscribe_global_updates_by_symbol(
            MARKET_SYMBOLS.ETH
        )
        print("Unsubscribed from global ETH events: {}".format(status))
        # close socket connection
        print("### closed ###")

    def on_open(ws):
        # subscribe to global event updates for ETH market
        # status = client.ws_client.subscribe_global_updates_by_symbol(MARKET_SYMBOLS.ETH)


        status = client.ws_client.subscribe_orderbook_depth_streams_by_symbol(MARKET_SYMBOLS.ETH)
        print("Subscribed to  ETH events: {}".format(status))

        # logs event name and data for all markets and users that are subscribed.
        # helpful for debugging
        # client.socket.listen("default",callback)

    print("Making socket connection to  exchange")
    client.ws_client.initialize_socket(
        on_open=on_open, on_error=on_error, on_close=on_close
    )

    timeout = 60
    end_time = time.time() + timeout
    while not event_received and time.time() < end_time:
        time.sleep(1)

    client.ws_client.stop()
    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
