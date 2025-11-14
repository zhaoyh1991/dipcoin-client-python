from config import TEST_NETWORK
from pprint import pprint
import asyncio
from dipcoin_client import DipcoinClient, Networks


async def main():
    seed_phrase = "autumn erode toilet hello produce energy black reject honey ball lawsuit copy"

    client = DipcoinClient(
        True,  # agree to terms and conditions
        Networks[TEST_NETWORK],  # network to connect i.e. SUI_STAGING or SUI_PROD
        seed_phrase,  # seed phrase of the wallet
    )

    await client.init(True)
    signature = await client.onboard_user()
    pprint("User onboarding Signature:")
    pprint(signature)

    await client.close_connections()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
