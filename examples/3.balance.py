import asyncio
import os
from pprint import pprint

from config import TEST_ACCT_KEY, TEST_NETWORK
from dipcoin_client import DipcoinClient, Networks, SuiGraphQLClient


async def main():
    # create client instance
    client = DipcoinClient(
        True,  # agree to terms and conditions
        Networks[TEST_NETWORK],  # network to connect with
        TEST_ACCT_KEY,  # seed phrase of the wallet
    )

    # initialize the client
    # on boards user on . Must be set to true for first time use
    try:
        await client.init(True)
        sui_chain = SuiGraphQLClient(client)
        target_address = os.getenv("SUI_QUERY_ADDRESS") or client.get_public_address()

        print("Testing lightweight Sui GraphQL client")
        print("Target address:", target_address)

        # checks SUI token balance
        print("Chain token balance:", await sui_chain.get_native_chain_token_balance(target_address))

        # check usdc balance deposited to USDC contract
        print("USDC balance:", await sui_chain.get_usdc_balance(target_address))

        usdc_coins = await sui_chain.get_usdc_coins(target_address)
        print("USDC coins:")
        pprint(usdc_coins)

        print("Margin bank balance:", await sui_chain.get_margin_bank_balance(target_address))
    finally:
        await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
