from dipcoin_client.wallets import create_wallet_account


SOLANA_PRIVATE_KEY = "2DD7ksoBz87XBVin7SCBKf4bodwvkWB22UujRA83T25hX2eS38N7v7fdidb5hKHdg2B2wWi3xArJq2ZMSv2pQc4M"
SOLANA_ADDRESS = "411Avm3xwNPZhXc8Qk4yRmubirmkMCQzAjkU1ATKod49"


def main():
    solana_account = create_wallet_account(SOLANA_PRIVATE_KEY, "solana")
    assert solana_account.address == SOLANA_ADDRESS

    signature = solana_account.sign_message(b'{"onboardingUrl":"dipcoin.io"}')
    signature_payload, scheme, public_key = signature.split("-")

    assert len(signature_payload) == 128
    assert scheme == "5"
    assert public_key

    print("Solana address:", solana_account.address)
    print("Solana signature:", signature)


if __name__ == "__main__":
    main()
