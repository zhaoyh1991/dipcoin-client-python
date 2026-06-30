from typing import TypedDict, Union
from .enumerations import *


MarketSymbol = Union[MARKET_SYMBOLS, str]


class Order(TypedDict):
    market: str
    creator: str
    isLong: bool
    reduceOnly: bool
    postOnly: bool
    orderbookOnly: bool
    ioc: bool
    quantity: int
    price: int
    leverage: int
    expiration: int
    salt: int
    orderFlag: int
    domain: str


class RequiredOrderFields(TypedDict):
    symbol: MarketSymbol  # market for which to create order
    price: int  # price at which to place order. Will be zero for a market order
    quantity: int  # quantity/size of order
    side: ORDER_SIDE  # BUY/SELL
    orderType: ORDER_TYPE  # MARKET/LIMIT


class OrderSignatureRequest(RequiredOrderFields):
    leverage: int  # (optional) leverage to take, default is 1
    reduceOnly: bool  # (optional) Reduce Only feature is deprecated until further notice. Default is set to false.
    salt: int  # (optional) random number for uniqueness of order. Generated randomly if not provided
    expiration: int  # (optional) time at which order will expire. Will be set to 1 month if not provided
    maker: str  # (optional) maker of the order, defaults to the initialized account
    ioc: bool


class OrderSignatureResponse(RequiredOrderFields):
    maker: str
    orderSignature: str


class PlaceOrderRequest(OrderSignatureResponse):
    timeInForce: TIME_IN_FORCE  # IOC/GTT by default all orders are GTT
    postOnly: bool  # true/false, default is true
    cancelOnRevert: bool  # if true, order will be cancelled in case of on-chain settlement error
    clientId: str  # id of the client


class GetOrderbookRequest(TypedDict):
    symbol: MarketSymbol
    limit: int  # number of bids/asks to retrieve, should be <= 50


class GetCandleStickRequest(TypedDict):
    symbol: MarketSymbol
    interval: Interval
    startTime: float
    endTime: float
    limit: int


class OrderCancelSignatureRequest(TypedDict):
    symbol: MarketSymbol
    hashes: list
    parentAddress: str  # (optional) should only be provided by a sub account


class OrderCancellationRequest(OrderCancelSignatureRequest):
    signature: str


class GetTransactionHistoryRequest(TypedDict):
    symbol: MarketSymbol  # will fetch orders of provided market
    pageSize: int  # will get only provided number of orders, must be <= 50
    pageNum: int  # will fetch particular page records


class GetPositionRequest(GetTransactionHistoryRequest):
    parentAddress: str  # (optional) should be provided by sub accounts


class GetUserTradesRequest(TypedDict):
    symbol: MarketSymbol
    beginTime: int
    endTime: int
    pageSize: int
    pageNum: int
    parentAddress: str  # (optional) should be provided by sub account


class GetOrderRequest(GetTransactionHistoryRequest):
    parentAddress: str  # (optional) should be provided by sub accounts


class GetFundingHistoryRequest(TypedDict):
    symbol: MarketSymbol  # will fetch funding history of provided market
    parentAddress: str
    pageSize: int  # will get only provided number of records, must be <= 50
    pageNum: int  # will fetch particular page records
