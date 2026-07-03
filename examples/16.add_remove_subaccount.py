from config import TEST_ACCT_KEY, TEST_SUB_ACCT_KEY, TEST_NETWORK
from dipcoin_client import (
    DipcoinClient,
    Networks,
)
import asyncio


async def main():
  # initialize the parent account client
  clientParent = DipcoinClient(True, Networks[TEST_NETWORK], TEST_ACCT_KEY)
  await clientParent.init(True)

  # initialize the child account client
  clientChild = DipcoinClient(True, Networks[TEST_NETWORK], TEST_SUB_ACCT_KEY)
  await clientChild.init(True)

  print("Parent: ", clientParent.get_public_address())
  print("Child: ", clientChild.get_public_address())

  print("Sub-account add/remove PTB construction is deferred.")
  print("Use backend relayer/API flow when the endpoint is available.")


if __name__ == "__main__":
  loop = asyncio.new_event_loop()
  loop.run_until_complete(main())
  loop.close()
