"""通用小工具（定价精度、数量精度、响应格式化等）。"""

from decimal import Decimal
from enum import Enum


BASE_18 = Decimal("1000000000000000000")
BASE18_MIN_ABS = Decimal("1000000000")
BASE18_RESPONSE_KEYS = {
    "amount",
    "amount24h",
    "accountValue",
    "availableBalance",
    "avgEntryPrice",
    "avgFillPrice",
    "avgPrice",
    "balance",
    "bankBalance",
    "bestAskPrice",
    "bestAskAmount",
    "bestBidPrice",
    "bestBidAmount",
    "change24h",
    "closeQuantity",
    "commission",
    "costPrice",
    "eightHFundingRate",
    "entryPrice",
    "fee",
    "filledFee",
    "filledQty",
    "filledQuantity",
    "freeCollateral",
    "funding",
    "fundingFee",
    "fundingRate",
    "fundingDue",
    "fundingFeeNext",
    "high24h",
    "indexPrice",
    "initialMargin",
    "lastPrice",
    "leverage",
    "liquidationPrice",
    "low24h",
    "maintenanceMargin",
    "margin",
    "makerFee",
    "markPrice",
    "maxFunding",
    "maxQtyLimit",
    "maxQtyMarket",
    "maxTradePrice",
    "maxTradeSize",
    "maxValue",
    "midMarketPrice",
    "minTradePrice",
    "minTradeSize",
    "mtbLong",
    "mtbShort",
    "netMargin",
    "openQty",
    "open24h",
    "openInterest",
    "openPrice",
    "orderValue",
    "oraclePrice",
    "pnl",
    "positionQtyReduced",
    "positionQtyReducible",
    "positionSelectedLeverage",
    "positionValue",
    "price",
    "quantity",
    "quoteQty",
    "rate24h",
    "realizedPnl",
    "roe",
    "settlementFundingFee",
    "settlementAmount",
    "size",
    "selectedLeverage",
    "stepSize",
    "takerFee",
    "tickSize",
    "totalPositionMargin",
    "totalUnrealizedProfit",
    "triggerPrice",
    "unrealizedPnl",
    "unrealizedProfit",
    "volume24h",
    "walletBalance",
}


def normalize_price(price: float, precision: int) -> float:
    return round(price, precision)


def normalize_qty(qty: float, precision: int) -> float:
    return round(max(0.0, qty), precision)


def enum_value(value):
    return value.value if isinstance(value, Enum) else value


def symbol_value(value):
    return enum_value(value)


def _format_decimal(value: Decimal) -> str:
    formatted = format(value.normalize(), "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


def from_base18_string(value) -> str:
    return _format_decimal(Decimal(str(value)) / BASE_18)


def humanize_orderbook_response(obj):
    def convert_level(level):
        if not isinstance(level, list):
            return humanize_base18_response(level)
        converted = list(level)
        for index in (0, 1):
            if index < len(converted) and _looks_base18_value(converted[index]):
                converted[index] = from_base18_string(converted[index])
        return converted
    
    if isinstance(obj, list):
        return [humanize_orderbook_response(item) for item in obj]

    if not isinstance(obj, dict):
        return humanize_base18_response(obj)
    result = {}
    for key, value in obj.items():
        if key in {"bids", "asks"} and isinstance(value, list):
            result[key] = [convert_level(level) for level in value]
        else:
            result[key] = humanize_orderbook_response(value)
    return result


def humanize_candlestick_response(obj):
    def convert_candle(candle):
        if not isinstance(candle, list):
            return humanize_base18_response(candle)
        converted = list(candle)
        for index in (1, 2, 3, 4, 5, 7, 9, 10):
            if index < len(converted) and _looks_base18_value(converted[index]):
                converted[index] = from_base18_string(converted[index])
        return converted

    if isinstance(obj, dict):
        return {
            key: [convert_candle(candle) for candle in value]
            if key == "data" and isinstance(value, list)
            else humanize_candlestick_response(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [convert_candle(item) for item in obj]
    return obj


def humanize_websocket_payload(topic, payload):
    if not topic:
        return payload

    if topic.startswith("perp/orderBook."):
        return humanize_orderbook_response(payload)

    if topic.startswith("perp/ticker."):
        return humanize_base18_response(payload)

    if topic.startswith("perp/tradeList."):
        return humanize_base18_response(payload)

    if topic in {"userUpdates", "MarketDataUpdate"}:
        return humanize_base18_response(payload)

    return payload


def humanize_base18_response(obj, parent_key=None):
    if isinstance(obj, list):
        return [humanize_base18_response(item, parent_key) for item in obj]
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key in BASE18_RESPONSE_KEYS and _looks_base18_value(value):
                result[key] = from_base18_string(value)
            else:
                result[key] = humanize_base18_response(value, key)
        return result
    return obj


def _looks_integral(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and (text.isdigit() or (text[0] == "-" and text[1:].isdigit()))
    return False


def _looks_base18_value(value) -> bool:
    if isinstance(value, bool):
        return False
    try:
        decimal = Decimal(str(value).strip())
    except Exception:
        return False
    if decimal != decimal.to_integral_value():
        return False
    return decimal == 0 or abs(decimal) >= BASE18_MIN_ABS
