import json
from copy import deepcopy

from .api_service import APIService
from .contracts import Contracts
from .order_signer import OrderSigner
from .onboarding_signer import OnboardingSigner
from .constants import SUI_CLOCK_OBJECT_ID, TIME, SERVICE_URLS
from .websocket_client import WebsocketClient
from sui_utils import *
from .interfaces import *
from .enumerations import *
import time

DEAULT_EXCHANGE_LEVERAGE = 3


class DipcoinClient:
    """
    A class to represent a client for interacting with  offchain and onchain APIs.
    """

    def __init__(self, are_terms_accepted, network, private_key=""):
        self.are_terms_accepted = are_terms_accepted
        self.network = network
        if private_key != "":
            if private_key.startswith("0x"):
                private_key = private_key[2:]
                self.account = SuiWallet(privateKey=private_key)
            else:
                self.account = SuiWallet(seed=private_key)
        self.apis = APIService(
            self.network["apiGateway"]
        )

        self.ws_client = WebsocketClient(self.network["webSocketURL"])
        self.contracts = Contracts(self.network)
        self.order_signer = OrderSigner()
        self.onboarding_signer = OnboardingSigner()
        self.contract_signer = Signer()
        self.url = self.network["url"]

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
            onboarding_signature = self.onboarding_signer.create_signature(
                self.network["onboardingUrl"], self.account.privateKeyBytes
            )
            onboarding_signature = (
                    onboarding_signature + self.account.publicKeyBase64.decode()
            )
            print("self.account.address", self.account.address)
            response = await self.authorize_signed_hash(onboarding_signature)

            if "error" in response:
                raise SystemError(
                    f"Authorization error: {response['error']['message']}"
                )

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
                    params["symbol"])
            ),
            creator=params["maker"].lower()
            if "maker" in params
            else self.account.address.lower(),
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
        print("create_order_to_sign", order)

        symbol = sui_params["symbol"].value
        order_signature = self.order_signer.sign_order(
            order, self.account.privateKeyBytes
        )
        order_signature = order_signature + self.account.publicKeyBase64.decode()
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
            creator=order["creator"],

        )

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
        hash_val = self.order_signer.get_order_hash(order_to_sign)
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
        cancel_hash = self.order_signer.encode_message(
            {"orderHashes": order_hash})
        hash_sig = (
                self.order_signer.sign_hash(
                    cancel_hash, self.account.privateKeyBytes, "")
                + self.account.publicKeyBase64.decode()
        )
        print("hash_sig", hash_sig)
        print("address", self.account.address)

        return OrderCancellationRequest(
            symbol=symbol.value,
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
        print("post_cancel_order", SERVICE_URLS["ORDERS"]["ORDERS_CANCEL"])

        return await self.apis.post(
            SERVICE_URLS["ORDERS"]["ORDERS_CANCEL"],
            {
                "symbol": params["symbol"],
                "orderHashes": params["hashes"],
                "signature": params["signature"],
                "parentAddress": params["parentAddress"],
            },
            auth_required=True, wallet=self.account.address,
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
        print("cancel_all_orders", orders)

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

        return await self.apis.post(
            SERVICE_URLS["ORDERS"]["ORDERS"],
            {
                "symbol": params["symbol"],
                "price": params["price"],
                "quantity": params["quantity"],
                "leverage": params["leverage"],
                "creator": params["creator"],
                "orderType": params["orderType"].value,
                "side": params["side"].value,
                "reduceOnly": params["reduceOnly"],
                "salt": params["salt"],
                "orderSignature": params["orderSignature"],
                "clientId": "dipcoin-v2-client-python:{}".format(
                    default_value(params, "clientId", "")
                ),
            },
            auth_required=True, wallet=self.account.address,
        )

    # Contract calls
    async def deposit_margin_to_bank(self, amount: int, coin_id: str = "") -> bool:
        """
        Deposits given amount of USDC from user's account to margin bank

        Inputs:
            amount (number): quantity of usdc to be deposited to bank in base decimals (1,2 etc)
            coin_id (string) (optional): the id of the coin you want the amount to be deposited from

        Returns:
            Boolean: true if amount is successfully deposited, false otherwise
        """
        usdc_coins = self.get_usdc_coins()
        if coin_id == "":
            coin_id = self._get_coin_having_balance(usdc_coins["data"], amount)

        package_id = self.contracts.get_package_id()
        user_address = self.account.getUserAddress()
        callArgs = []
        callArgs.append(self.contracts.get_bank_id())

        callArgs.append(self.contracts.get_sequencer_id())
        callArgs.append(getSalt())

        callArgs.append(self.account.getUserAddress())
        callArgs.append(str(toUsdcBase(amount)))
        callArgs.append(coin_id)

        callArgs[2] = getsha256Hash(callArgs)

        txBytes = rpc_unsafe_moveCall(
            self.url,
            callArgs,
            "deposit_to_bank",
            "margin_bank",
            user_address,
            package_id,
            typeArguments=[self.contracts.get_currency_type()],
        )
        signature = self.contract_signer.sign_tx(txBytes, self.account)
        res = rpc_sui_executeTransactionBlock(self.url, txBytes, signature)
        try:
            if res["result"]["effects"]["status"]["status"] == "success":
                return True
            else:
                return False
        except Exception as e:
            return res

    async def withdraw_margin_from_bank(self, amount: Union[float, int]) -> bool:
        """
        Withdraws given amount of usdc from margin bank if possible

        Inputs:
            amount (number): quantity of usdc to be withdrawn from bank in base decimals (1,2 etc)

        Returns:
            Boolean: true if amount is successfully withdrawn, false otherwise
        """

        bank_id = self.contracts.get_bank_id()
        account_address = self.account.getUserAddress()

        callArgs = [
            bank_id,
            self.contracts.get_sequencer_id(),
            getSalt(),
            account_address,
            str(toUsdcBase(amount)),
        ]

        callArgs[2] = getsha256Hash(callArgs)
        txBytes = rpc_unsafe_moveCall(
            self.url,
            callArgs,
            "withdraw_from_bank",
            "margin_bank",
            self.account.getUserAddress(),
            self.contracts.get_package_id(),
            typeArguments=[self.contracts.get_currency_type()],
        )
        signature = self.contract_signer.sign_tx(txBytes, self.account)
        res = rpc_sui_executeTransactionBlock(self.url, txBytes, signature)
        try:
            if res["result"]["effects"]["status"]["status"] == "success":
                return True
            else:
                return False
        except Exception as e:
            return res

    async def withdraw_all_margin_from_bank(self):
        """
        Withdraws everything of usdc from margin bank

        Inputs:
            No input Required
        Returns:
            Boolean: true if amount is successfully withdrawn, false otherwise
        """
        bank_id = self.contracts.get_bank_id()
        account_address = self.account.getUserAddress()

        callArgs = [
            bank_id,
            self.contracts.get_sequencer_id(),
            getSalt(),
            account_address,
        ]

        callArgs[2] = getsha256Hash(callArgs)
        txBytes = rpc_unsafe_moveCall(
            self.url,
            callArgs,
            "withdraw_all_margin_from_bank",
            "margin_bank",
            self.account.getUserAddress(),
            self.contracts.get_package_id(),
            typeArguments=[self.contracts.get_currency_type()],
        )
        signature = self.contract_signer.sign_tx(txBytes, self.account)
        res = rpc_sui_executeTransactionBlock(self.url, txBytes, signature)

        if res["result"]["effects"]["status"]["status"] == "success":
            return True
        else:
            return False

    async def adjust_margin(
            self,
            symbol: MARKET_SYMBOLS,
            operation: ADJUST_MARGIN,
            amount: str,
            parentAddress: str = "",
    ):
        """
        Adjusts user's on-chain position by adding or removing the specified amount of margin.
        Performs on-chain contract call, the user must have gas tokens
        Inputs:
            symbol (MARKET_SYMBOLS): market for which to adjust user leverage
            operation (ADJUST_MARGIN): ADD/REMOVE adding or removing margin to position
            amount (number): amount of margin to be adjusted
            parentAddress (str): optional, if provided, the margin of parent is
                                being adjusted (for sub accounts only)
        Returns:
            Boolean: true if the margin is adjusted
        """

        user_position = await self.get_user_position(
            {"symbol": symbol}
        )
        print(user_position)

        if user_position == {}:
            raise (Exception(f"User has no open position on market: {symbol}"))

        callArgs = []
        callArgs.append(self.contracts.get_config_id())
        callArgs.append(SUI_CLOCK_OBJECT_ID)
        callArgs.append(self.contracts.get_perpetual_id(symbol))
        callArgs.append(self.contracts.get_bank_id())

        callArgs.append(self.contracts.get_sub_account_id())
        callArgs.append(self.contracts.get_sequencer_id())

        callArgs.append(self.contracts.get_price_oracle_object_id(symbol))

        callArgs.append(self.account.getUserAddress())

        callArgs.append(str(to_base18(amount)))

        callArgs.append(getsha256Hash(callArgs + [getSalt()]))
        print("callArgs", callArgs)

        if operation == ADJUST_MARGIN.ADD:
            txBytes = rpc_unsafe_moveCall(
                self.url,
                callArgs,
                "add_margin",
                "exchange",
                self.account.getUserAddress(),
                self.contracts.get_package_id(),
                typeArguments=[self.contracts.get_currency_type()],
            )

        else:
            txBytes = rpc_unsafe_moveCall(
                self.url,
                callArgs,
                "remove_margin",
                "exchange",
                self.account.getUserAddress(),
                self.contracts.get_package_id(),
                typeArguments=[self.contracts.get_currency_type()],
            )

        signature = self.contract_signer.sign_tx(txBytes, self.account)
        result = rpc_sui_executeTransactionBlock(self.url, txBytes, signature)
        if result["result"]["effects"]["status"]["status"] == "success":
            return True
        else:
            return False

    async def update_sub_account(self, sub_account_address: str, status: bool) -> bool:
        """
        Used to whitelist and account as a sub account or revoke sub account status from an account.
        Inputs:
            sub_account_address (str): address of the sub account
            status (bool): new status of the sub account

        Returns:
            Boolean: true if the sub account status is update
        """
        callArgs = []
        callArgs.append(self.contracts.get_config_id())
        callArgs.append(self.contracts.get_sub_account_id())
        callArgs.append(sub_account_address)
        callArgs.append(status)
        txBytes = rpc_unsafe_moveCall(
            self.url,
            callArgs,
            "set_sub_account",
            "sub_accounts",
            self.account.getUserAddress(),
            self.contracts.get_package_id(),
        )

        signature = self.contract_signer.sign_tx(txBytes, self.account)
        result = rpc_sui_executeTransactionBlock(self.url, txBytes, signature)
        if result["result"]["effects"]["status"]["status"] == "success":
            return True
        else:
            return False

    async def get_native_chain_token_balance(self, userAddress: str = None) -> float:
        """
        Returns user's native chain token (SUI) balance
        """
        try:
            callArgs = []
            callArgs.append(userAddress or self.account.getUserAddress())
            callArgs.append("0x2::sui::SUI")

            result = rpc_call_sui_function(
                self.url, callArgs, method="suix_getBalance"
            )
            return fromSuiBase(result.raw_response["totalBalance"])
        except Exception as e:
            raise (Exception(f"Failed to get balance, error: {e}"))

    async def get_usdc_coins(self, userAddress: str = None):
        """
        Returns the list of the usdc coins owned by user
        """
        try:
            callArgs = []
            callArgs.append(userAddress or self.account.getUserAddress())
            callArgs.append(self.contracts.get_currency_type())
            result = rpc_call_sui_function(
                self.url, callArgs, method="suix_getCoins")
            return result.raw_response
        except Exception as e:
            raise (Exception("Failed to get USDC coins, Exception: {}".format(e)))

    async def get_usdc_balance(self, userAddress: str = None) -> float:
        """
        Returns user's USDC token balance .
        """
        try:
            callArgs = []
            callArgs.append(userAddress or self.account.getUserAddress())
            callArgs.append(self.contracts.get_currency_type())
            result = rpc_call_sui_function(
                self.url, callArgs, method="suix_getBalance"
            )
            return fromUsdcBase(result.raw_response["totalBalance"])

        except Exception as e:
            raise (Exception("Failed to get balance, Exception: {}".format(e)))

    async def get_user_position_from_chain(self, market: MARKET_SYMBOLS, userAddress: str = None):
        """
        Returns the user positions from chain
        """
        try:
            call_args = []
            call_args.append(self.contracts.get_position_table_id(market))
            call_args.append(
                {"type": "address", "value": userAddress or self.account.getUserAddress()}
            )
            result = rpc_call_sui_function(
                self.url, call_args, method="suix_getDynamicFieldObject"
            )
            if "error" in result.raw_response:
                if result.raw_response["error"]["code"] == "dynamicFieldNotFound":
                    return "Given user have no position open"
            return result.raw_response["data"]["content"]["fields"]["value"]["fields"]

        except Exception as e:
            raise (Exception("Failed to get positions, Exception: {}".format(e)))

    async def get_margin_bank_balance(self, userAddress: str = None) -> float:
        """
        Returns user's Margin Bank balance.
        """
        try:
            call_args = []
            call_args.append(self.contracts.get_bank_table_id())
            call_args.append(
                {"type": "address", "value": userAddress or self.account.getUserAddress()}
            )
            result = rpc_call_sui_function(
                self.url, call_args, method="suix_getDynamicFieldObject"
            ).raw_response
            print("get_margin_bank_balance", result)

            balance = fromSuiBase(
                result["data"]["content"]["fields"]["value"]["fields"]["balance"]
            )
            return balance
        except Exception as e:
            raise (Exception("Failed to get balance, Exception: {}".format(e)))

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
        return await self.apis.get(SERVICE_URLS["MARKET"]["ORDER_BOOK"], params)

    async def get_market_symbols(self):
        """
        Returns a list of active market symbols.
        Returns:
            list: active market symbols
        """

        return await self.apis.get(SERVICE_URLS["MARKET"]["EXCHANGE_INFO"], {})



    async def get_funding_history(self, params: GetFundingHistoryRequest):
        """
        Returns a list of the user's funding payments, a boolean indicating if there is/are more page(s),
            and the next page number
        Inputs:
            params(GetFundingHistoryRequest): params required to fetch funding history

        """

        params = extract_enums(params, ["symbol"])

        return await self.apis.get(
            SERVICE_URLS["USER"]["FUNDING_HISTORY"], params, auth_required=True, wallet=self.account.address,
        )

    async def get_exchange_info(self, symbol: MARKET_SYMBOLS = None):
        """
        Returns a dictionary containing exchange info for market(s). The min/max trade size, max allowed oi open
        min/max trade price, step size, tick size etc...
        Inputs:
            symbol(MARKET_SYMBOLS): the market symbol
        Returns:
            dict: exchange info
        """
        query = {"symbol": symbol.value} if symbol else {}
        return await self.apis.get(SERVICE_URLS["MARKET"]["EXCHANGE_INFO"], query)

    async def get_ticker_data(self, symbol: MARKET_SYMBOLS = None):
        """
        Returns a dictionary containing ticker data for market(s).
        Inputs:
            symbol(MARKET_SYMBOLS): the market symbol
        Returns:
            dict: ticker info
        """
        query = {"symbol": symbol.value} if symbol else {}
        return await self.apis.get(SERVICE_URLS["MARKET"]["TICKER"], query)

    async def get_market_candle_stick_data(self, params: GetCandleStickRequest):
        """
        Returns a list containing the candle stick data.
        Inputs:
            params(GetCandleStickRequest): params required to fetch candle stick data
        Returns:
            list: the candle stick data
        """
        params = extract_enums(params, ["symbol", "interval"])

        return await self.apis.get(SERVICE_URLS["MARKET"]["CANDLE_STICK_DATA"], params)


    def get_account(self):
        """
        Returns the user account object
        """
        return self.account

    def get_public_address(self):
        """
        Returns the user account public address
        """
        return self.account.address

    async def get_orders(self, params: GetOrderRequest):
        """
        Returns a list of orders.
        Inputs:
            params(GetOrderRequest): params required to query orders (e.g. symbol,statuses)
        Returns:
            list: a list of orders
        """
        params = extract_enums(params, ["symbol"])
        print("get_orders", params)
        return await self.apis.get(SERVICE_URLS["USER"]["ORDERS"], params, True, wallet=self.account.address, )

    async def get_user_position(self, params: GetPositionRequest):
        """
        Returns a list of positions.

        Returns:
            list: a list of positions
        """
        if params is not None:
            params = extract_enums(params, ["symbol"])

        return await self.apis.get(SERVICE_URLS["USER"]["USER_POSITIONS"], params, True, wallet=self.account.address, )

    async def get_user_trades(self, params: GetUserTradesRequest):
        """
        Returns a list of user trades.
        Inputs:
            params(GetUserTradesRequest): params to query trades (e.g. symbol)
        Returns:
            list: a list of trade
        """
        params = extract_enums(params, ["symbol", "type"])
        return await self.apis.get(SERVICE_URLS["USER"]["USER_TRADES"], params, True, wallet=self.account.address,)



    async def get_user_account_data(self, parentAddress: str = ""):
        """
        Returns user account data.
        Inputs:
            parentAddress: an optional field, used by sub accounts to fetch parent account state
        """
        return await self.apis.get(
            service_url=SERVICE_URLS["USER"]["ACCOUNT"],
            query={"parentAddress": parentAddress},
            auth_required=True,
            wallet=self.account.getUserAddress()
        )

    async def close_connections(self):
        # close aio http connection
        await self.apis.close_session()

    def _get_coin_having_balance(self, usdc_coin_list: list, balance: int) -> str:
        balance = toUsdcBase(balance)
        for coin in usdc_coin_list:
            if int(coin["balance"]) >= balance:
                return coin["coinObjectId"]
        raise Exception(
            "Not enough balance available, please merge your coins for get usdc"
        )
