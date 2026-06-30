import asyncio
from pprint import pprint

from config import TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    MARKET_SYMBOLS,
    Networks,
    ORDER_SIDE,
    ORDER_TYPE,
    OrderSignatureRequest,
)


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

    try:
        assert client.get_public_address() == SOLANA_SUB_ACCOUNT_ADDRESS
        print("sub_account:", client.get_public_address())
        print("parentAddress:", SOLANA_PARENT_ADDRESS)

        order = OrderSignatureRequest(
            symbol=MARKET_SYMBOLS.SUI,
            price=0.2,
            quantity=1,
            side=ORDER_SIDE.BUY,
            orderType=ORDER_TYPE.LIMIT,
            leverage=10,
            expiration=0,
        )

        signed_order = client.create_signed_order(order)
        print("signed_order:")
        pprint(signed_order)

        place_resp = await client.post_signed_order(signed_order)
        print("place_resp:")
        pprint(place_resp)

        order_hash = place_resp.get("data")
        if not order_hash:
            raise RuntimeError("place order response did not include order hash")

        await asyncio.sleep(10)

        open_orders = await client.get_orders({"symbol": MARKET_SYMBOLS.SUI})
        print("open_orders:")
        pprint(open_orders)

        cancel_request = client.create_signed_cancel_orders(
            MARKET_SYMBOLS.SUI,
            order_hash=[order_hash],
        )
        print("cancel_request:")
        pprint(cancel_request)

        cancel_resp = await client.post_cancel_order(cancel_request)
        print("cancel_resp:")
        pprint(cancel_resp)

        await asyncio.sleep(20)

        orders_after_cancel = await client.get_orders({"symbol": MARKET_SYMBOLS.SUI})
        print("orders_after_cancel:")
        pprint(orders_after_cancel)
    finally:
        await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
