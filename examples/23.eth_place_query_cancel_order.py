import asyncio
from pprint import pprint

from config import TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    ETH_CHAIN_ID,
    MARKET_SYMBOLS,
    Networks,
    ORDER_SIDE,
    ORDER_TYPE,
    OrderSignatureRequest,
)


# Test-wallet credentials only. Do not use a private key that holds real funds.
ETH_PARENT_ADDRESS = "0x72cfe0e5e4de41b23dc998de9e5160f65e18eda0"
ETH_API_ACCOUNT_ADDRESS = "0xf55c9893b3bb7e639c7856ff76c6f2439711caa3"
ETH_API_ACCOUNT_PRIVATE_KEY = (
    "0x704d035af33657d0793d9cf9b8cb412a6b9c887fd18cdf4e8662dde5c44ee280"
)


async def main():
    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        ETH_API_ACCOUNT_PRIVATE_KEY,
        parentAddress=ETH_PARENT_ADDRESS,
        wallet_type="eth",
        protocol_chain_id=ETH_CHAIN_ID,
    )
    try:
        await client.init(True)

        assert client.get_public_address() == ETH_API_ACCOUNT_ADDRESS
        print("api_account:", client.get_public_address())
        print("parentAddress:", ETH_PARENT_ADDRESS)

        order = OrderSignatureRequest(
            symbol=MARKET_SYMBOLS.BTC,
            price=80000,
            quantity=0.01,
            side=ORDER_SIDE.SELL,
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

        open_orders = await client.get_orders({"symbol": MARKET_SYMBOLS.BTC})
        print("open_orders:")
        pprint(open_orders)

        cancel_request = client.create_signed_cancel_orders(
            MARKET_SYMBOLS.BTC,
            order_hash=[order_hash],
        )
        print("cancel_request:")
        pprint(cancel_request)

        cancel_resp = await client.post_cancel_order(cancel_request)
        print("cancel_resp:")
        pprint(cancel_resp)

        await asyncio.sleep(20)

        orders_after_cancel = await client.get_orders(
            {"symbol": MARKET_SYMBOLS.BTC}
        )
        print("orders_after_cancel:")
        pprint(orders_after_cancel)
    finally:
        await client.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
