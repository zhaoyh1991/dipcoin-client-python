from enum import Enum


class ORDER_TYPE(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class ORDER_SIDE(Enum):
    BUY = "BUY"
    SELL = "SELL"


class MARKET_SYMBOLS(Enum):
    BTC = "BTC-PERP"
    ETH = "ETH-PERP"
    SOL = "SOL-PERP"
    SUI = "SUI-PERP"
    XRP = "XRP-PERP"
    BNB = "BNB-PERP"

    
class TIME_IN_FORCE(Enum):
    IMMEDIATE_OR_CANCEL = "IOC"
    GOOD_TILL_TIME = "GTT"





class ORDER_STATUS(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    STAND_BY = "STAND_BY"
    STAND_BY_PENDING = "STAND_BY_PENDING"


class CANCEL_REASON(Enum):
    UNDERCOLLATERALIZED = "UNDERCOLLATERALIZED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    USER_CANCELLED = "USER_CANCELLED"
    EXCEEDS_MARKET_BOUND = "EXCEEDS_MARKET_BOUND"
    COULD_NOT_FILL = "COULD_NOT_FILL"
    EXPIRED = "EXPIRED"
    USER_CANCELLED_ON_CHAIN = "USER_CANCELLED_ON_CHAIN"
    SYSTEM_CANCELLED = "SYSTEM_CANCELLED"
    SELF_TRADE = "SELF_TRADE"
    POST_ONLY_FAIL = "POST_ONLY_FAIL"
    FAILED = "FAILED"
    NETWORK_DOWN = "NETWORK_DOWN"


class Interval(Enum):
    _1m = "1m"
    _3m = "3m"
    _5m = "5m"
    _15m = "15m"
    _30m = "30m"
    _1h = "1h"
    _4h = "4h"
    _1d = "1d"
    _1w = "1w"


class SOCKET_EVENTS(Enum):
    GET_LAST_KLINE_WITH_INTERVAL = "{}@kline@{}"

    ORDERBOOK_DEPTH_STREAM_ROOM = "perp/orderBook.{}.{}"
    USER_UPDATES_ROOM = "userUpdates"
    TICKER = "perp/ticker.{}"

    MARKET_DATA_UPDATE = "MarketDataUpdate"
    RECENT_TRADES = "perp/tradeList.{}"





class MARGIN_TYPE(Enum):
    ISOLATED = "ISOLATED"


class ADJUST_MARGIN(Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"


class TRADE_TYPE(Enum):
    ISOLATED = "IsolatedTrader"
    LIQUIDATION = "IsolatedLiquidation"
