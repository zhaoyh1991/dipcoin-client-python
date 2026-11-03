import asyncio
import os
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


ETH_PARENT_ADDRESS_ENV = "DIPCOIN_ETH_PARENT_ADDRESS"
ETH_API_ADDRESS_ENV = "DIPCOIN_ETH_API_ADDRESS"
ETH_PRIVATE_KEY_ENV = "DIPCOIN_ETH_API_PRIVATE_KEY"


async def main():
    parent_address = os.getenv(ETH_PARENT_ADDRESS_ENV)
    api_address = os.getenv(ETH_API_ADDRESS_ENV)
    private_key = os.getenv(ETH_PRIVATE_KEY_ENV)
    for variable_name, value in (
        (ETH_PARENT_ADDRESS_ENV, parent_address),
        (ETH_API_ADDRESS_ENV, api_address),
        (ETH_PRIVATE_KEY_ENV, private_key),
    ):
        if not value:
            raise RuntimeError(f"Set {variable_name} before running this example")

    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        private_key,
        parentAddress=parent_address,
        wallet_type="eth",
        protocol_chain_id=ETH_CHAIN_ID,
    )
    try:
        await client.init(True)

        assert client.get_public_address() == api_address
        print("api_account:", client.get_public_address())
        print("parentAddress:", parent_address)

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
