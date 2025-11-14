from pprint import pprint
import asyncio
import time
from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_SIDE,
    ORDER_TYPE,
    OrderSignatureRequest,
)


async def place_orders(client: DipcoinClient):


    # Sign and place a limit order at 4x leverage. Order is signed using the account seed phrase set on the client
    adjusted_leverage = 10
    signature_request = OrderSignatureRequest(
        symbol=MARKET_SYMBOLS.ETH,  # market symbol
        price=3000,  # price at which you want to place order
        quantity=0.01,  # quantity
        side=ORDER_SIDE.BUY,
        orderType=ORDER_TYPE.LIMIT,
        leverage=adjusted_leverage,
        expiration=0,  # expiry after 10 days, default expiry is a month
    )
    print("signature_request", signature_request)
    signed_order = client.create_signed_order(signature_request)
    print("signed_order", signed_order)

    resp = await client.post_signed_order(signed_order)
    print({"msg": "placing limit order", "resp": resp})




async def main():
    # initialize client
    client = DipcoinClient(
        True,  # agree to terms and conditions
        Networks[TEST_NETWORK],  # network to connect with
        TEST_ACCT_KEY,  # seed phrase of the wallet
    )

    await client.init(True)
    await place_orders(client)

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
