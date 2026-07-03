from typing import Any, Dict, List, Optional, Union

import aiohttp

from .enumerations import ADJUST_MARGIN, MARKET_SYMBOLS
from sui_utils import Signer, fromSuiBase, fromUsdcBase, getSalt, getsha256Hash, toUsdcBase


class SuiGraphQLClient:
    """
    Sui GraphQL helper for direct chain reads and transaction submission.

    PTB construction for Dipcoin Move calls is intentionally not implemented
    here yet. Use Dipcoin relayer payload helpers for add/remove margin flows.
    """

    def __init__(self, dipcoin_client):
        self.client = dipcoin_client
        self.account = dipcoin_client.account
        self.contracts = dipcoin_client.contracts
        self.url = self._resolve_graphql_url(dipcoin_client.network)
        self.contract_signer = Signer()

    @staticmethod
    def _resolve_graphql_url(network: Dict[str, Any]) -> str:
        if network.get("graphqlUrl"):
            return network["graphqlUrl"]
        url = network.get("url", "")
        if "mainnet" in url:
            return "https://graphql.mainnet.sui.io/graphql"
        return "https://graphql.testnet.sui.io/graphql"

    def _require_sui_wallet(self) -> None:
        if not self.client._is_sui_wallet():
            raise NotImplementedError(
                "Direct Sui GraphQL chain calls require wallet_type='sui'. "
                "Use relayer/API flows for ETH and Solana wallets."
            )

    async def query(
            self,
            query: str,
            variables: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                    self.url,
                    json={"query": query, "variables": variables or {}},
                    headers=request_headers,
                    ssl=False,
            ) as response:
                payload = await response.json(content_type=None)

        if payload.get("errors"):
            raise Exception(f"Sui GraphQL query failed: {payload['errors']}")
        return payload.get("data", {})

    async def get_balance(self, userAddress: str = None, coin_type: str = None) -> Dict[str, Any]:
        self._require_sui_wallet()
        address = userAddress or self.account.getUserAddress()
        coin_type = coin_type or "0x2::sui::SUI"
        query = """
        query Balance($address: SuiAddress!, $coinType: String!) {
          address(address: $address) {
            balance(coinType: $coinType) {
              coinType { repr }
              totalBalance
              coinBalance
              addressBalance
            }
          }
        }
        """
        data = await self.query(query, {"address": address, "coinType": coin_type})
        return data["address"]["balance"]

    async def get_native_chain_token_balance(self, userAddress: str = None) -> float:
        try:
            balance = await self.get_balance(userAddress, "0x2::sui::SUI")
            return fromSuiBase(balance["totalBalance"])
        except Exception as exc:
            raise Exception(f"Failed to get balance, error: {exc}")

    async def get_usdc_balance(self, userAddress: str = None) -> float:
        try:
            balance = await self.get_balance(userAddress, self.contracts.get_currency_type())
            return fromUsdcBase(balance["totalBalance"])
        except Exception as exc:
            raise Exception(f"Failed to get balance, Exception: {exc}")

    async def get_usdc_coins(self, userAddress: str = None, limit: int = 50):
        self._require_sui_wallet()
        try:
            return await self.get_coin_objects(
                userAddress or self.account.getUserAddress(),
                self.contracts.get_currency_type(),
                limit,
            )
        except Exception as exc:
            raise Exception(f"Failed to get USDC coins, Exception: {exc}")

    async def get_coin_objects(
            self,
            userAddress: str,
            coin_type: str,
            limit: int = 50,
    ) -> Dict[str, Any]:
        self._require_sui_wallet()
        query = """
        query Coins($address: SuiAddress!, $type: String!, $first: Int!, $after: String) {
          address(address: $address) {
            objects(first: $first, after: $after, filter: { type: $type }) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                address
                version
                digest
                contents {
                  json
                }
              }
            }
          }
        }
        """
        coin_object_type = f"0x2::coin::Coin<{coin_type}>"
        coins: List[Dict[str, Any]] = []
        after = None
        while True:
            data = await self.query(
                query,
                {
                    "address": userAddress,
                    "type": coin_object_type,
                    "first": min(limit, 50),
                    "after": after,
                },
            )
            objects = data["address"]["objects"]
            for node in objects["nodes"]:
                fields = self._coin_fields(node)
                coins.append({
                    "coinObjectId": node["address"],
                    "version": node.get("version"),
                    "digest": node.get("digest"),
                    "balance": fields.get("balance"),
                })
            if len(coins) >= limit or not objects["pageInfo"]["hasNextPage"]:
                return {
                    "data": coins[:limit],
                    "nextCursor": objects["pageInfo"].get("endCursor"),
                    "hasNextPage": objects["pageInfo"]["hasNextPage"],
                }
            after = objects["pageInfo"]["endCursor"]

    async def get_object(self, object_id: str) -> Dict[str, Any]:
        self._require_sui_wallet()
        query = """
        query Object($id: SuiAddress!) {
          object(address: $id) {
            address
            version
            digest
            owner { __typename }
            asMoveObject {
              hasPublicTransfer
              contents {
                type { repr }
                json
              }
            }
          }
        }
        """
        data = await self.query(query, {"id": object_id})
        return data["object"]

    async def get_dynamic_field(
            self,
            parent_object_id: str,
            name_literal: str,
    ) -> Optional[Dict[str, Any]]:
        self._require_sui_wallet()
        query = """
        query DynamicField($parent: SuiAddress!, $name: String!) {
          object(address: $parent) {
            dynamicField(name: { literal: $name }) {
              name { json }
              value {
                __typename
                ... on MoveValue { json }
                ... on MoveObject {
                  address
                  version
                  digest
                  contents { json }
                }
              }
            }
          }
        }
        """
        data = await self.query(query, {"parent": parent_object_id, "name": name_literal})
        obj = data.get("object")
        return None if obj is None else obj.get("dynamicField")

    async def get_user_position_from_chain(self, market: MARKET_SYMBOLS, userAddress: str = None):
        try:
            field = await self.get_dynamic_field(
                self.contracts.get_position_table_id(market),
                userAddress or self.account.getUserAddress(),
            )
            if not field:
                return "Given user have no position open"
            return self._dynamic_value_json(field)
        except Exception as exc:
            raise Exception(f"Failed to get positions, Exception: {exc}")

    async def get_margin_bank_balance(self, userAddress: str = None) -> float:
        try:
            field = await self.get_dynamic_field(
                self.contracts.get_bank_table_id(),
                userAddress or self.account.getUserAddress(),
            )
            if not field:
                return 0
            value = self._dynamic_value_json(field)
            balance = value.get("balance", value)
            return fromSuiBase(balance)
        except Exception as exc:
            raise Exception(f"Failed to get balance, Exception: {exc}")

    async def execute_transaction(
            self,
            transaction_data_bcs: str,
            signatures: List[str],
    ) -> Dict[str, Any]:
        self._require_sui_wallet()
        mutation = """
        mutation ExecuteTransaction($tx: Base64!, $sigs: [Base64!]!) {
          executeTransaction(transactionDataBcs: $tx, signatures: $sigs) {
            effects {
              digest
              status
              epoch { epochId startTimestamp }
              gasEffects {
                gasSummary {
                  computationCost
                  storageCost
                  storageRebate
                }
              }
            }
          }
        }
        """
        data = await self.query(mutation, {"tx": transaction_data_bcs, "sigs": signatures})
        result = data["executeTransaction"]
        return result

    async def sign_and_execute_transaction(
            self,
            transaction_data_bcs: str,
            signatures: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        self._require_sui_wallet()
        signatures = signatures or [
            self.contract_signer.sign_tx(transaction_data_bcs, self.account)
        ]
        return await self.execute_transaction(transaction_data_bcs, signatures)

    async def deposit_margin_to_bank(
            self,
            amount: int,
            coin_id: str = "",
            gas_budget: int = 100000000,
    ) -> Dict[str, Any]:
        self._raise_ptb_not_implemented("deposit_margin_to_bank")

    async def withdraw_margin_from_bank(self, amount: Union[float, int]) -> bool:
        self._raise_ptb_not_implemented("withdraw_margin_from_bank")

    async def withdraw_all_margin_from_bank(self):
        self._raise_ptb_not_implemented("withdraw_all_margin_from_bank")

    async def adjust_margin(
            self,
            symbol: MARKET_SYMBOLS,
            operation: ADJUST_MARGIN,
            amount: str,
            parentAddress: str = "",
    ):
        self._raise_ptb_not_implemented("adjust_margin")

    async def update_sub_account(self, sub_account_address: str, status: bool) -> bool:
        self._raise_ptb_not_implemented("update_sub_account")

    @staticmethod
    def _raise_ptb_not_implemented(method_name: str):
        raise NotImplementedError(
            f"{method_name} requires Sui PTB construction, which is not implemented in this version. "
            "Use Dipcoin relayer/API flows, or call execute_transaction() with pre-built transactionDataBcs."
        )

    @staticmethod
    def _coin_fields(node: Dict[str, Any]) -> Dict[str, Any]:
        contents = (node.get("contents") or {}).get("json") or {}
        return contents.get("fields", contents)

    @staticmethod
    def _dynamic_value_json(field: Dict[str, Any]) -> Any:
        value = field.get("value") or {}
        if "json" in value:
            return value["json"]
        contents = value.get("contents") or {}
        json_value = contents.get("json")
        return json_value.get("fields", json_value) if isinstance(json_value, dict) else json_value

    @staticmethod
    def _get_coin_having_balance(usdc_coin_list: list, balance: int) -> str:
        for coin in usdc_coin_list:
            if int(coin["balance"]) > toUsdcBase(balance):
                return coin["coinObjectId"]
        raise Exception(f"No coin having balance greater than {balance}")
