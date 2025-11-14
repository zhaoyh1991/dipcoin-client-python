from .enumerations import MARKET_SYMBOLS


_DEFAULT_MARKET = "BTC-PERP"

# Contract addresses for SUI_STAGING
STAGING_CONTRACTS = {
    "sub_account_id": "0x62a28e07b1e3ddb2cb1108349761ec1cf096b0c3523863af3bfd4e36e14beb5b",
    "bank_table_id": "0x236762ea78c43dabff54175fee324c8919fd06cca5bbc8e7fc3fb9a9f0f10c1c",
    "package_id": "0x0114b1d4656ac42a9523da1c7241f0291918f9517fd30f3e6e84b9fd5b3e3730",
    "bank_id": "0x16be93006a3ced6fa2dde428c9b8418b4986efd4abc6980d7f4367bbfd638353",
    "config_id": "0x05a630c36e8a6cb9ff99e2d2595e55ec70d002a8069a90c2d1bac0bfa12271fa",
    "currency_type": "0x1f2788918b609959c9052a1f00c49765752acb24d99997a102903be7da18dd0d::coin::COIN",
    "sequencer_id": "0xaed1352c3f6f2a44fd521350f53a98f675d4b07cc36916607eae24c2650a9cb9",
    "price_oracle_object_id": "0x362f009be96a1d74ff76156cec96876b89aa09529c1261d491751903ee798e4d",
    "position_table_ids":{
        "BTC-PERP":"0xfb67a57e1ff22ebdbd6f8b0833dd4cda0d34bb2bd3b9cd254fcb68a17428e541",
        "ETH-PERP":"0xe6764eff20b9d36c11669a59bc669e1c13d380c7bf12ee1fe75c2241ec9e8719",
        "SUI-PERP":"0xdbf4902bb3e9a476f437c70c6637a5e3155bd94963a79513fd5f31e9a2d67d8a",
    },
    "price_oracle_object_id":{
        "BTC-PERP":"0x8c65003d5d1a529adc4be78cfceb3855ef529d9807fcd58b06caab0a96caa806",
        "ETH-PERP":"0x362f009be96a1d74ff76156cec96876b89aa09529c1261d491751903ee798e4d",
        "SUI-PERP":"0x1e9be81a16c22896f2b4852e8b5c5e59d247c5566dee7b390477f4b7f70914df",
    }
}

# Contract addresses for SUI_PROD
PROD_CONTRACTS = {
    "sub_account_id": "0x3ad8c911dff3ee0aeeaf86f0c7e7a540a23743477e831d14f62b63e58fb8eb0d",  
    "bank_table_id": "0x9c78b1bb63de6ceece5be85a7dd6af77bf57a7a989bb51f27e4a2fbabf0ca2db",
    "package_id": "0x978fed071cca22dd26bec3cf4a5d5a00ab10f39cb8c659bbfdfbec4397241001",
    "bank_id": "0x3cc2bfbe6b9dc346f3f27a47b4b0c9eaaf0143c0c704726a1513a1e8c5d9a4c1",
    "config_id": "0xdeff2ed27dfe5402e38d60b090a7dcf9b4842c16ec63e472119272173603dfd8",
    "currency_type": "0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC",
    "sequencer_id": "0x5dd7fa4c14b88167458df2ea281f4253213137ef4cd91d9b83fb56d0494f6741",
    "position_table_ids":{
        "BTC-PERP":"0xa155915bf30421843902ce952b2567d774b1454035003aa426b9bdb60132dc95",
        "ETH-PERP":"0xe99695623b81fce940322e02ed987b36574269e92156a01996ee134af2707d57",
        "SUI-PERP":"0xae6251d9f16b8a77109d1472d0946459ceab64b8d6bb1717067dee1e22fb06c0",
        "BNB-PERP":"0x49a00a7bb7776cc4b7cbdc43be6ab6ce3b763157bafc8259959730ecb48efee7",
        "XRP-PERP":"0x61dfd7df986027f1e08277e015e8110930369987bf16054475ec415dc7105234",
        "SOL-PERP":"0xca2b0b7cc8009b8fc3feaa4f4a0b07c7eb650ad8928b70a9d2bbf81a45dc05d8",
    },
    "price_oracle_object_id":{
        "BTC-PERP":"0x9a62b4863bdeaabdc9500fce769cf7e72d5585eeb28a6d26e4cafadc13f76ab2",
        "ETH-PERP":"0x9193fd47f9a0ab99b6e365a464c8a9ae30e6150fc37ed2a89c1586631f6fc4ab",
        "SUI-PERP":"0x801dbc2f0053d34734814b2d6df491ce7807a725fe9a01ad74a07e9c51396c37",
        "BNB-PERP":"0x9c6e77f0ecfc46aac395e21c52ccb96518f85acacae743c5b47f4ca5e29826c3",
        "XRP-PERP":"0x93bfda25cb6b1653a9c769e8216014bd2c06997f3edb479566761fbf2abf6ac2",
        "SOL-PERP":"0x9d0d275efbd37d8a8855f6f2c761fa5983293dd8ce202ee5196626de8fcd4469",
    }
}


class Contracts:
    def __init__(self, network=None):
        self.contract_info = {}
        # Determine network type from network dict
        self.network_type = self._get_network_type(network)
        # Store contract addresses in contracts_global_info based on network type
        self.contracts_global_info = (
            STAGING_CONTRACTS.copy() if self.network_type == "SUI_STAGING" else PROD_CONTRACTS.copy()
        )

    def _get_network_type(self, network):
        """Determine network type from network dictionary"""
        if network is None:
            return "SUI_STAGING"  # Default to staging
        
        # Check apiGateway to determine network type
        api_gateway = network.get("apiGateway", "")
        if "demoapi.dipcoin.io" in api_gateway:
            return "SUI_STAGING"
        elif "gray-api.dipcoin.io" in api_gateway:
            return "SUI_PROD"
        else:
            # Default to staging if cannot determine
            return "SUI_STAGING"

    def set_contract_addresses(self, contracts_info):
        c_dict = {}
        for c in contracts_info["data"]:
            c_dict[c["symbol"]] = c

        # print("c dict",c_dict)

        self.contract_info = c_dict
        # Keep contracts_global_info, don't clear it

    def get_sub_account_id(self):
        return self.contracts_global_info["sub_account_id"]

    def get_bank_table_id(self):
        return self.contracts_global_info["bank_table_id"]

    def get_package_id(self):
        return self.contracts_global_info["package_id"]

    def get_bank_id(self):
        return self.contracts_global_info["bank_id"]

    def get_config_id(self):
        return self.contracts_global_info["config_id"]

    def get_currency_type(self):
        return self.contracts_global_info["currency_type"]

    
    def get_sequencer_id(self) -> str:
        return self.contracts_global_info["sequencer_id"]

    def get_position_table_id(self, market: MARKET_SYMBOLS) -> str:
        return self.contracts_global_info["position_table_id"][market.value]

    def get_price_oracle_object_id(self, market: MARKET_SYMBOLS):
        return self.contracts_global_info["price_oracle_object_id"][market.value]

  

    def get_perpetual_id(self, market: MARKET_SYMBOLS):
        return self.contract_info[market.value]["perpId"]
