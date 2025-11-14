from pprint import pprint
import asyncio
import time
import random
from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_SIDE,
    ORDER_TYPE,
    ORDER_STATUS,
    OrderSignatureRequest,
)


async def main():
    client = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
    await client.init(True)

    # todo 下面的都是测试
    # cancel placed order
    # cancellation_request = client.create_signed_cancel_orders(
    #     MARKET_SYMBOLS.ETH, order_hash=["95c32aea0bc52c708fb238ab45dd1a21484d0fa598d2ea957d879e3f0e3ed969"]
    # )
    # # print("cancellation_request",cancellation_request)
    # cancel_resp = await client.post_cancel_order(cancellation_request)
    # print("cancel_resp", cancel_resp)
    # time.sleep(200)

    leverage = 10
    order = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=2905,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.BUY,
        orderType=ORDER_TYPE.LIMIT,
        leverage=leverage,
        expiration=0,
    )
    signed_order = client.create_signed_order(order)
    post_resp = await client.post_signed_order(signed_order)
    print(post_resp)
    time.sleep(2)

    # cancel placed order
    cancellation_request = client.create_signed_cancel_orders(
        MARKET_SYMBOLS.ETH, order_hash=[post_resp["data"]]
    )

    cancel_resp = await client.post_cancel_order(cancellation_request)
    print(cancel_resp)

    order = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=2905,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.BUY,
        orderType=ORDER_TYPE.LIMIT,
        leverage=leverage,
        expiration=0,
    )
    signed_order = client.create_signed_order(order)
    post_resp = await client.post_signed_order(signed_order)
    print(post_resp)
    time.sleep(2)

    resp = await client.cancel_all_orders(
        MARKET_SYMBOLS.ETH
    )
    if resp is False:
        print("No open order to cancel")
    else:
        print(resp)

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
