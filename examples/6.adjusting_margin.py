import asyncio
import os
from pprint import pprint

from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    MARKET_SYMBOLS,
    Networks,
    calculate_max_removable_margin,
)


PRIVATE_KEY = os.getenv("DIPCOIN_PRIVATE_KEY", TEST_ACCT_KEY)
PARENT_ADDRESS = os.getenv("DIPCOIN_PARENT_ADDRESS", "")
WALLET_TYPE = os.getenv("DIPCOIN_WALLET_TYPE", "sui")
PROTOCOL_CHAIN_ID = os.getenv("DIPCOIN_PROTOCOL_CHAIN_ID")
SYMBOL = MARKET_SYMBOLS(os.getenv("DIPCOIN_MARGIN_SYMBOL", "ETH-PERP"))
AMOUNT = os.getenv("DIPCOIN_MARGIN_AMOUNT", "0.01")
REMOVE_AMOUNT = os.getenv("DIPCOIN_REMOVE_MARGIN_AMOUNT", AMOUNT)
ACTION = os.getenv("DIPCOIN_MARGIN_ACTION", "cycle").lower()
CONFIRMATION_SECONDS = float(os.getenv("DIPCOIN_CONFIRMATION_SECONDS", "10"))


def transaction_digest(response, action):
    data = response.get("data") if isinstance(response, dict) else None
    digest = data.get("digest") if isinstance(data, dict) else None
    if not digest:
        raise RuntimeError(f"{action} failed: {response}")
    return digest


def print_removable_margin(position_response):
    positions = position_response.get("data", [])
    if not positions:
        return
    current_position = positions[0]
    print(
        "max_removable_margin:",
        calculate_max_removable_margin(current_position),
    )
    print(
        "suggested_removable_margin_98pct:",
        calculate_max_removable_margin(
            current_position,
            safety_factor="0.98",
        ),
    )


async def main():
    if ACTION not in {"add", "remove", "cycle"}:
        raise ValueError("DIPCOIN_MARGIN_ACTION must be add, remove, or cycle")

    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        PRIVATE_KEY,
        parentAddress=PARENT_ADDRESS,
        wallet_type=WALLET_TYPE,
        protocol_chain_id=(
            int(PROTOCOL_CHAIN_ID) if PROTOCOL_CHAIN_ID is not None else None
        ),
    )
    try:
        await client.init(True)

        position_before = await client.get_user_position({"symbol": SYMBOL})
        print("position_before:")
        pprint(position_before)
        if not position_before.get("data"):
            print(f"No open position for {SYMBOL.value}")
            return
        latest_position = position_before

        if ACTION in {"add", "cycle"}:
            add_response = await client.add_margin(SYMBOL, AMOUNT)
            print(
                "add_margin_digest:",
                transaction_digest(add_response, "AddMargin"),
            )

            await asyncio.sleep(CONFIRMATION_SECONDS)
            latest_position = await client.get_user_position({"symbol": SYMBOL})
            print("position_after_add:")
            pprint(latest_position)

        if ACTION in {"remove", "cycle"}:
            print("position_before_remove:")
            pprint(latest_position)
            print_removable_margin(latest_position)

            remove_response = await client.remove_margin(SYMBOL, REMOVE_AMOUNT)
            print(
                "remove_margin_digest:",
                transaction_digest(remove_response, "RemoveMargin"),
            )

            await asyncio.sleep(CONFIRMATION_SECONDS)
            print("position_after_remove:")
            pprint(await client.get_user_position({"symbol": SYMBOL}))
    finally:
        await client.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
