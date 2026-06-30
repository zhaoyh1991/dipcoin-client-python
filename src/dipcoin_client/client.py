import json
from copy import deepcopy
from typing import Any, Mapping, Optional, Union

from .api_service import APIService
from .contracts import Contracts
from .order_signer import OrderSigner
from .onboarding_signer import OnboardingSigner
from .constants import TIME, SERVICE_URLS
from .wallets import SOLANA_CHAIN_ID, SUI_CHAIN_ID, create_wallet_account, display_address
from .websocket_client import WebsocketClient
from sui_utils import *
from .interfaces import *
from .enumerations import *
from .util import humanize_base18_response, humanize_candlestick_response, humanize_orderbook_response, symbol_value
import time

DEAULT_EXCHANGE_LEVERAGE = 3


class DipcoinClient:
    """
    A class to represent a client for interacting with  offchain and onchain APIs.
    """

    def __init__(self, are_terms_accepted, network, private_key="", parentAddress="", wallet_type="sui"):
        self.are_terms_accepted = are_terms_accepted
        self.network = network
        if private_key:
            self.account = create_wallet_account(private_key, wallet_type)
        else:
            self.account = None
        self.wallet_chain_id = self.account.chain_id if self.account else SUI_CHAIN_ID
        self.apis = APIService(
            self.network["apiGateway"]
        )

        self.ws_client = WebsocketClient(self.network["webSocketURL"])
        self.contracts = Contracts(self.network)
        self.order_signer = OrderSigner()
        self.onboarding_signer = OnboardingSigner()
        self.parentAddress = self._normalize_address(self.account.address) if self.account else ""
        if parentAddress != "":
            self.parentAddress = self._normalize_address(parentAddress)

    def _wallet_address(self) -> str:
        return self.account.address if self.account is not None else ""

    def _wallet_chain_id(self) -> int:
        return self.account.chain_id if self.account is not None else SUI_CHAIN_ID

    def _normalize_address(self, address: str) -> str:
        if self._wallet_chain_id() == SOLANA_CHAIN_ID:
            return address
        return address.lower()

    def _is_sui_wallet(self) -> bool:
        return self._wallet_chain_id() == SUI_CHAIN_ID

    def _display_creator_for_request(self, creator: str) -> str:
        if self._is_sui_wallet() or ":" in creator:
            return creator
        return display_address(self._wallet_chain_id(), creator)

    def _auth_get(self, service_url, query=None):
        return self.apis.get(
            service_url,
            query or {},
            auth_required=True,
            wallet=self._wallet_address(),
        )

    def _auth_post(self, service_url, data):
        return self.apis.post(
            service_url,
            data,
            auth_required=True,
            wallet=self._wallet_address(),
        )

    def _ensure_parent_address_in_params(self, params: dict) -> None:
        """TypedDict request objects are plain dicts; optional parentAddress may be omitted."""
        if params.get("parentAddress", "") == "":
            params["parentAddress"] = self.parentAddress
        else:
            params["parentAddress"] = self._normalize_address(params["parentAddress"])

    async def init(self, user_onboarding=True, api_token="", auth_token=""):
        """
        Initialize the client.
        Inputs:
            user_onboarding (bool, optional): If set to true onboards the user address to exchange and gets authToken. Defaults to True.
            api_token(string, optional): API token to initialize client in read-only mode
        """
        contract_info = await self.get_contract_addresses()
        # print("contract_info",contract_info)

        self.contracts.set_contract_addresses(contract_info)

        # 1. priority to read only mode
        if api_token:
            self.apis.api_token = api_token
            # for socket
            self.ws_client.set_api_token(api_token)
        # 2. priority to perform onboarding if `true` over auth_token
        elif user_onboarding:
            self.apis.auth_token = await self.onboard_user()
            # self.ws_client.set_token(self.apis.auth_token)
        # 3. if user has provided auth token avoid onboarding again and use provided token
        elif auth_token:
            self.webSocketClient.set_token(auth_token)

    async def onboard_user(self, token: str = None):
        """
        On boards the user address and returns user authentication token.
        Inputs:
            token: user access token, if you possess one.
        Returns:
            str: user authorization token
        """
        user_auth_token = token

        # if no auth token provided create on
        if not user_auth_token:
            if self._is_sui_wallet():
                onboarding_signature = self.onboarding_signer.create_signature(
                    self.network["onboardingUrl"], self.account.privateKeyBytes
                )
                onboarding_signature = (
                        onboarding_signature + self.account.publicKeyBase64.decode()
                )
            else:
                onboarding_signature = self.onboarding_signer.create_wallet_signature(
                    self.network["onboardingUrl"], self.account
                )
            response = await self.authorize_signed_hash(onboarding_signature)

            if "error" in response:
                raise SystemError(
                    f"Authorization error: {response['error']['message']}"
                )

            # print("response", response)

            user_auth_token = response["data"]["token"]

        return user_auth_token

    async def authorize_signed_hash(self, signed_hash: str):
        """
        Registers user as an authorized user on server and returns authorization token.
        Inputs:
            signed_hash: signed onboarding hash
        Returns:
            dict: response from user authorization API
        """
        return await self.apis.post(
            SERVICE_URLS["USER"]["AUTHORIZE"],
            {
                "signature": signed_hash,
                "userAddress": self.account.address,
                "isTermAccepted": self.are_terms_accepted,
            }
        )

    async def get_contract_addresses(self):
        """
        Returns:
            dict: all contract addresses for the all markets.
        """
        return await self.apis.get(SERVICE_URLS["MARKET"]["EXCHANGE_INFO"])

    def create_order_to_sign(self, params: OrderSignatureRequest) -> Order:
        """
        Creates order signature request for an order.
        Inputs:
            params (OrderSignatureRequest): parameters to create order with, refer OrderSignatureRequest

        Returns:
            Order: order raw info
        """
        expiration = None
        if "expiration" not in params:
            expiration = 0
        else:
            expiration = params["expiration"]

        return Order(
            market=default_value(
                params, "market", self.contracts.get_perpetual_id(
                    symbol_value(params["symbol"]))
            ),
            creator=self._normalize_address(params["maker"])
            if "maker" in params
            else self.parentAddress,
            isLong=params["side"] == ORDER_SIDE.BUY,
            reduceOnly=default_value(params, "reduceOnly", False),
            postOnly=default_value(params, "postOnly", False),
            orderbookOnly=default_value(params, "orderbookOnly", True),
            ioc=default_value(params, "ioc", False),
            quantity=params["quantity"],
            price=params["price"],
            leverage=default_value(params, "leverage", 1),
            expiration=default_value(params, "expiration", expiration),
            salt=default_value(params, "salt", int(time.time() * 1000)
                               ),
            domain="dipcoin.io"

        )

    def create_signed_order(self, req: OrderSignatureRequest) -> OrderSignatureResponse:
        """
        Create an order from provided params and signs it using the private key of the account
        Inputs:
            params (OrderSignatureRequest): parameters to create order with
        Returns:
            OrderSignatureResponse: order raw info and generated signature
        """

        sui_params = deepcopy(req)
        sui_params["price"] = to_base18(req["price"])
        sui_params["quantity"] = to_base18(req["quantity"])
        sui_params["leverage"] = to_base18(req["leverage"])

        order = self.create_order_to_sign(sui_params)
        # print("create_order_to_sign", order)

        symbol = symbol_value(sui_params["symbol"])
        payload_version = 1 if self._is_sui_wallet() else 2
        order_signature = self.order_signer.sign_order_with_wallet(
            order, self.account, payload_version
        )
        return OrderSignatureResponse(
            symbol=symbol,
            price=sui_params["price"],
            quantity=sui_params["quantity"],
            side=sui_params["side"],
            leverage=sui_params["leverage"],
            reduceOnly=default_value(sui_params, "reduceOnly", False),
            salt=order["salt"],
            expiration=order["expiration"],
            orderSignature=order_signature,
            orderType=sui_params["orderType"],
            creator=self._display_creator_for_request(order["creator"]),

        )

    @staticmethod
    def _mapping_get(m: Any, key: str) -> Any:
        if isinstance(m, Mapping):
            return m[key]
        return getattr(m, key)

    def create_signed_reduce_only_plan_order(
        self,
        symbol: MARKET_SYMBOLS,
        side: ORDER_SIDE,
        order_type: ORDER_TYPE,
        order_price: Union[int, float],
        quantity: Union[int, float],
        leverage: Union[int, float],
        maker: str = "",
    ) -> OrderSignatureResponse:
        """
        Reduce-only order signature for TP/SL plan close. Matches server
        OrderData (expiration=0, ioc/postOnly false, orderbookOnly true).
        Sign payload uses order_price/quantity/leverage only — not trigger_price.
        """
        req: OrderSignatureRequest = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "price": order_price,
            "quantity": quantity,
            "leverage": leverage,
            "reduceOnly": True,
            "salt": int(time.time() * 1000),
            "expiration": 0,
            "ioc": False,
            "postOnly": False,
            "orderbookOnly": True,
        }
        if maker:
            req["maker"] = maker
        return self.create_signed_order(req)

    async def set_take_profit_plan(
        self,
        symbol: MARKET_SYMBOLS,
        close_side: ORDER_SIDE,
        trigger_price: Union[int, float],
        order_price: Union[int, float],
        quantity: Union[int, float],
        leverage: Union[int, float],
        order_type: ORDER_TYPE = ORDER_TYPE.LIMIT,
        tpsl_type: str = "normal",
        trigger_way: str = "oracle",
        creator: str = "",
    ):
        """
        仅新增单笔止盈计划（不在同一请求中设置止损或修改已有计划）。
        trigger_price：条件触发价；order_price：签名与执行的委托价（市价计划须为 0）。
        close_side：平多 SELL、平空 BUY。creator：主账户地址，默认 self.parentAddress。
    
        """
        if tpsl_type not in ("normal", "position"):
            raise ValueError("tpsl_type must be 'normal' or 'position'")
        if order_type == ORDER_TYPE.MARKET and order_price != 0:
            raise ValueError("order_price must be 0 for MARKET plan")
        cr = self._normalize_address(creator) if creator else self.parentAddress
        signed = self.create_signed_reduce_only_plan_order(
            symbol,
            close_side,
            order_type,
            order_price,
            quantity,
            leverage,
            maker=cr,
        )
        return await self.apis.post(
            SERVICE_URLS["PLAN"]["BATCH_PLAN_CLOSE"],
            {
                "symbol": symbol_value(symbol),
                "side": symbol_value(close_side),
                "leverage": self._mapping_get(signed, "leverage"),
                "creator": cr,
                "tpOrderType": symbol_value(order_type),
                "tpTpslType": tpsl_type,
                "tpTriggerPrice": to_base18(trigger_price),
                "tpOrderPrice": self._mapping_get(signed, "price"),
                "tpQuantity": self._mapping_get(signed, "quantity"),
                "tpTriggerWay": trigger_way,
                "tpSalt": str(self._mapping_get(signed, "salt")),
                "tpOrderSignature": self._mapping_get(signed, "orderSignature"),
            },
            auth_required=True,
            wallet=self._wallet_address(),
        )

    async def set_stop_loss_plan(
        self,
        symbol: MARKET_SYMBOLS,
        close_side: ORDER_SIDE,
        trigger_price: Union[int, float],
        order_price: Union[int, float],
        quantity: Union[int, float],
        leverage: Union[int, float],
        order_type: ORDER_TYPE = ORDER_TYPE.LIMIT,
        tpsl_type: str = "normal",
        trigger_way: str = "oracle",
        creator: str = "",
    ):
        """
        仅新增单笔止损计划（不在同一请求中设置止盈或修改已有计划）。
        参数含义同 set_take_profit_plan。
        """
        if tpsl_type not in ("normal", "position"):
            raise ValueError("tpsl_type must be 'normal' or 'position'")
        if order_type == ORDER_TYPE.MARKET and order_price != 0:
            raise ValueError("order_price must be 0 for MARKET plan")
        cr = self._normalize_address(creator) if creator else self.parentAddress
        signed = self.create_signed_reduce_only_plan_order(
            symbol,
            close_side,
            order_type,
            order_price,
            quantity,
            leverage,
            maker=cr,
        )
        return await self.apis.post(
            SERVICE_URLS["PLAN"]["BATCH_PLAN_CLOSE"],
            {
                "symbol": symbol_value(symbol),
                "side": symbol_value(close_side),
                "leverage": self._mapping_get(signed, "leverage"),
                "creator": cr,
                "slOrderType": symbol_value(order_type),
                "slTpslType": tpsl_type,
                "slTriggerPrice": to_base18(trigger_price),
                "slOrderPrice": self._mapping_get(signed, "price"),
                "slQuantity": self._mapping_get(signed, "quantity"),
                "slTriggerWay": trigger_way,
                "slSalt": str(self._mapping_get(signed, "salt")),
                "slOrderSignature": self._mapping_get(signed, "orderSignature"),
            },
            auth_required=True,
            wallet=self._wallet_address(),
        )

    async def get_position_tpsl_plans(
        self,
        position_id: int,
        tpsl_type: str="normal",
        parent_address: str = "",
    ):
        """
        查询仓位关联的止盈止损计划。 tpsl_type: 'normal' 或 'position'。
        子账户查询母账户维度时可传 parent_address。
        """
        if tpsl_type not in ("normal", "position"):
            raise ValueError("tpsl_type must be 'normal' or 'position'")
        q: dict = {"positionId": position_id, "tpslType": tpsl_type}
        if parent_address:
            q["parentAddress"] = self._normalize_address(parent_address)
        return humanize_base18_response(await self.apis.get(
            SERVICE_URLS["PLAN"]["POSITION_TPSL"],
            query=q,
            auth_required=True,
            wallet=self._wallet_address(),
        ))

    def create_signed_cancel_order(
            self, params: OrderSignatureRequest, parentAddress: str = ""
    ):
        """
            Creates a cancel order request from provided params and signs it using the private
            key of the account

        Inputs:
            params (OrderSignatureRequest): parameters to create cancel order with
            parentAddress (str): Only provided by a sub account

        Returns:
            OrderSignatureResponse: generated cancel signature
        """
        if "ioc" in params and params["ioc"]:
            params["timeInForce"] = TIME_IN_FORCE.IMMEDIATE_OR_CANCEL
        if (
                "timeInForce" in params
                and params["timeInForce"] == TIME_IN_FORCE.IMMEDIATE_OR_CANCEL
        ):
            params["ioc"] = True
        sui_params = deepcopy(params)
        sui_params["price"] = to_base18(params["price"])
        sui_params["quantity"] = to_base18(params["quantity"])
        sui_params["leverage"] = to_base18(params["leverage"])

        if "triggerPrice" in sui_params:
            sui_params["triggerPrice"] = to_base18(sui_params["triggerPrice"])

        order_to_sign = self.create_order_to_sign(sui_params)
        payload_version = 1 if self._is_sui_wallet() else 2
        hash_val = self.order_signer.get_order_hash(order_to_sign, payload_version, self._wallet_chain_id())
        return self.create_signed_cancel_orders(
            params["symbol"], hash_val.hex(), parentAddress
        )

    def create_signed_cancel_orders(
            self, symbol: MARKET_SYMBOLS, order_hash: list, parentAddress: str = ""
    ):
        """
            Creates a cancel order from provided params and sign it using the private
            key of the account

        Inputs:
            params (list): a list of order hashes
            parentAddress (str): only provided by a sub account
        Returns:
            OrderCancellationRequest: containing symbol, hashes and signature
        """
        if isinstance(order_hash, list) is False:
            order_hash = [order_hash]
        msg = json.dumps({"orderHashes": order_hash}, separators=(",", ":")).encode("utf-8")
        if self._is_sui_wallet():
            cancel_hash = self.order_signer.encode_message({"orderHashes": order_hash})
            hash_sig = (
                    self.order_signer.sign_hash(
                        cancel_hash, self.account.privateKeyBytes, "")
                    + self.account.publicKeyBase64.decode()
            )
        else:
            hash_sig = self.account.sign_message(msg)
        if parentAddress == "":
            parentAddress = self.parentAddress
        else:
            parentAddress = self._normalize_address(parentAddress)
        return OrderCancellationRequest(
            symbol=symbol_value(symbol),
            hashes=order_hash,
            signature=hash_sig,
            parentAddress=parentAddress,
        )

    async def post_cancel_order(self, params: OrderCancellationRequest):
        """
        POST cancel order request
        Inputs:
            params(dict): a dictionary with OrderCancellationRequest required params
        Returns:
            dict: response from orders delete API
        """
        return await self.apis.post(
            SERVICE_URLS["ORDERS"]["ORDERS_CANCEL"],
            {
                "symbol": params["symbol"],
                "orderHashes": params["hashes"],
                "signature": params["signature"],
                "parentAddress": params["parentAddress"],
            },
            auth_required=True, wallet=self._wallet_address(),
        )

    async def cancel_all_orders(
            self,
            symbol: MARKET_SYMBOLS,
            parentAddress: str = "",
    ):
        """
        GETs all orders of specified status for the specified symbol,
        and creates a cancellation request for all orders and
        POSTs the cancel order request to
        Inputs:
            symbol (MARKET_SYMBOLS): Market for which orders are to be cancelled
            status (List[ORDER_STATUS]): status of orders that need to be cancelled
            parentAddress (str): address of parent account, only provided by sub account
        Returns:
            dict: response from orders delete API
        """
        orders = await self.get_orders(
            {"symbol": symbol}
        )
        if parentAddress == "":
            parentAddress = self.parentAddress
        else:
            parentAddress = self._normalize_address(parentAddress)

        hashes = []
        for i in orders["data"]["data"]:
            hashes.append(i["hash"])

        if len(hashes) > 0:
            req = self.create_signed_cancel_orders(
                symbol, hashes, parentAddress)
            return await self.post_cancel_order(req)

        return False

    async def post_signed_order(self, params: PlaceOrderRequest):
        """
        Creates an order from provided params and signs it using the private
        key of the account

        Inputs:
            params (OrderSignatureRequest): parameters to create order with

        Returns:
            OrderSignatureResponse: order raw info and generated signature
        """

        if params["reduceOnly"]:
            print(
                "Warning: Reduce Only feature is deprecated until further notice. Reduce Only orders will be rejected from the API.")

        data = {
            "symbol": symbol_value(params["symbol"]),
            "price": params["price"],
            "quantity": params["quantity"],
            "leverage": params["leverage"],
            "creator": self._display_creator_for_request(params["creator"]),
            "orderType": symbol_value(params["orderType"]),
            "side": symbol_value(params["side"]),
            "reduceOnly": params["reduceOnly"],
            "salt": params["salt"],
            "orderSignature": params["orderSignature"],
            "clientId": "dipcoin-v2-client-python:{}".format(
                default_value(params, "clientId", "")
            ),
        }
        if not self._is_sui_wallet():
            data = {"action": "PlaceOrder", **data}

        return await self.apis.post(
            SERVICE_URLS["ORDERS"]["ORDERS"],
            data,
            auth_required=True, wallet=self._wallet_address(),
        )

    # Relayer payload helpers
    def create_margin_relay_signature(
            self,
            symbol: MARKET_SYMBOLS,
            operation: ADJUST_MARGIN,
            amount: Union[str, int, float],
            salt: int = None,
            expiration: int = 0,
            userAddress: str = "",
    ):
        action = "AddMargin" if operation == ADJUST_MARGIN.ADD else "RemoveMargin"
        market = self.contracts.get_perpetual_id(symbol)
        user = self._normalize_address(userAddress) if userAddress else self.parentAddress
        salt = salt if salt is not None else int(time.time() * 1000)
        amount_base18 = to_base18(amount)
        payload = "".join([
            "{\n",
            f"\"action\":\"{action}\",\n",
            f"\"market\":\"{market}\",\n",
            f"\"user\":\"{self._margin_display_address(user)}\",\n",
            f"\"amount\":\"{amount_base18}\",\n",
            f"\"salt\":\"{salt}\",\n",
            f"\"expiration\":\"{expiration}\",\n",
            "\"domain\":\"dipcoin.io\"\n",
            "}",
        ])
        return {
            "symbol": symbol_value(symbol),
            "market": market,
            "action": action,
            "user": user,
            "amount": str(amount_base18),
            "salt": str(salt),
            "expiration": str(expiration),
            "payload": payload,
            "signature": self.account.sign_message(payload.encode("utf-8")),
        }

    def _margin_display_address(self, address: str) -> str:
        return display_address(self._wallet_chain_id(), address)

    # Market endpoints
    async def get_orderbook(self, params: GetOrderbookRequest):
        """
        Returns a dictionary containing the orderbook snapshot.
        Inputs:
            params(GetOrderbookRequest): the order symbol and limit(orderbook depth)
        Returns:
            dict: Orderbook snapshot
        """
        params = extract_enums(params, ["symbol"])
        return humanize_orderbook_response(await self.apis.get(SERVICE_URLS["MARKET"]["ORDER_BOOK"], params))

    async def get_market_symbols(self):
        """
        Returns a list of active market symbols.
        Returns:
            list: active market symbols
        """

        response = await self.apis.get(SERVICE_URLS["MARKET"]["EXCHANGE_INFO"], {})
        return humanize_base18_response(response)

    async def get_funding_history(self, params: GetFundingHistoryRequest):
        """
        Returns a list of the user's funding payments, a boolean indicating if there is/are more page(s),
            and the next page number
        Inputs:
            params(GetFundingHistoryRequest): params required to fetch funding history

        """
        self._ensure_parent_address_in_params(params)
        params = extract_enums(params, ["symbol"])

        return humanize_base18_response(await self.apis.get(
            SERVICE_URLS["USER"]["FUNDING_HISTORY"],
            params,
            auth_required=True,
            wallet=self._wallet_address(),
        ))

    async def get_exchange_info(self, symbol: MARKET_SYMBOLS = None):
        """
        Returns a dictionary containing exchange info for market(s). The min/max trade size, max allowed oi open
        min/max trade price, step size, tick size etc...
        Inputs:
            symbol(MARKET_SYMBOLS): the market symbol
        Returns:
            dict: exchange info
        """
        query = {"symbol": symbol_value(symbol)} if symbol else {}
        response = await self.apis.get(SERVICE_URLS["MARKET"]["EXCHANGE_INFO"], query)
        return humanize_base18_response(response)

    async def get_ticker_data(self, symbol: MARKET_SYMBOLS = None):
        """
        Returns a dictionary containing ticker data for market(s).
        Inputs:
            symbol(MARKET_SYMBOLS): the market symbol
        Returns:
            dict: ticker info
        """
        query = {"symbol": symbol_value(symbol)} if symbol else {}
        return humanize_base18_response(await self.apis.get(SERVICE_URLS["MARKET"]["TICKER"], query))

    async def get_market_candle_stick_data(self, params: GetCandleStickRequest):
        """
        Returns a list containing the candle stick data.
        Inputs:
            params(GetCandleStickRequest): params required to fetch candle stick data
        Returns:
            list: the candle stick data
        """
        params = extract_enums(params, ["symbol", "interval"])

        return humanize_candlestick_response(await self.apis.get(SERVICE_URLS["MARKET"]["CANDLE_STICK_DATA"], params))

    def get_account(self):
        """
        Returns the user account object
        """
        return self.account

    def get_public_address(self):
        """
        Returns the user account public address
        """
        return self._wallet_address()

    async def get_orders(self, params: GetOrderRequest):
        """
        Returns a list of orders.
        Inputs:
            params(GetOrderRequest): params required to query orders (e.g. symbol,statuses)
        Returns:
            list: a list of orders
        """
        self._ensure_parent_address_in_params(params)
        params = extract_enums(params, ["symbol"])
        return humanize_base18_response(await self.apis.get(
            SERVICE_URLS["USER"]["ORDERS"],
            params,
            True,
            wallet=self._wallet_address(),
        ))

    async def get_user_position(self, params: GetPositionRequest):
        """
        Returns a list of positions.

        Returns:
            list: a list of positions
        """
        self._ensure_parent_address_in_params(params)
        if params is not None:
            params = extract_enums(params, ["symbol"])

        return humanize_base18_response(await self.apis.get(
            SERVICE_URLS["USER"]["USER_POSITIONS"],
            params,
            True,
            wallet=self._wallet_address(),
        ))

    async def get_user_trades(self, params: GetUserTradesRequest):
        """
        Returns a list of user trades.
        Inputs:
            params(GetUserTradesRequest): params to query trades (e.g. symbol)
        Returns:
            list: a list of trade
        """
        self._ensure_parent_address_in_params(params)
        params = extract_enums(params, ["symbol", "type"])
        return humanize_base18_response(await self.apis.get(
            SERVICE_URLS["USER"]["USER_TRADES"],
            params,
            True,
            wallet=self._wallet_address(),
        ))

    async def get_user_account_data(self, parentAddress: str = ""):
        """
        Returns user account data.
        Inputs:
            parentAddress: an optional field, used by sub accounts to fetch parent account state
        """
        if parentAddress == "":
            parentAddress = self.parentAddress
        else:
            parentAddress = self._normalize_address(parentAddress)

        return humanize_base18_response(await self.apis.get(
            service_url=SERVICE_URLS["USER"]["ACCOUNT"],
            query={"parentAddress": parentAddress},
            auth_required=True,
            wallet=self._wallet_address(),
        ))

    async def close_connections(self):
        # close aio http connection
        await self.apis.close_session()
