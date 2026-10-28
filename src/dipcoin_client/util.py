"""通用小工具（定价精度、数量精度、响应格式化等）。"""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
from enum import Enum


BASE_18 = Decimal("1000000000000000000")
BASE_18_INT = 10 ** 18
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


def _position_decimal(position: Mapping, key: str, default=None) -> Decimal:
    if key not in position:
        if default is not None:
            return Decimal(default)
        raise ValueError(f"position is missing required field: {key}")

    value = position[key]
    try:
        decimal = Decimal(str(value).strip())
    except (AttributeError, InvalidOperation, ValueError) as exc:
        raise ValueError(f"position field {key} must be a finite number") from exc
    if not decimal.is_finite():
        raise ValueError(f"position field {key} must be a finite number")
    return decimal


def _to_base18_decimal(value: Decimal) -> int:
    return int((value * BASE_18).to_integral_value(rounding=ROUND_DOWN))


def calculate_max_removable_margin(position: Mapping, safety_factor="1") -> str:
    """Estimate the removable margin for a humanized position snapshot.

    ``position`` should be one item from ``get_user_position()["data"]``.
    BUY/LONG are treated as long positions and SELL/SHORT as short positions.
    Only a negative ``fundingDue`` (or the ``fundingFee`` alias) reduces the
    result. Calculations mirror the protocol's 1e18 fixed-point truncation.

    The default ``safety_factor`` returns the formula's theoretical maximum.
    Pass ``"0.98"`` to apply the same price-movement buffer currently used by
    the backend. The result is an estimate because oracle price and funding can
    change between reading the position and executing the removal.
    """
    if not isinstance(position, Mapping):
        raise TypeError("position must be a mapping")

    margin = _position_decimal(position, "margin")
    oracle_price = _position_decimal(position, "oraclePrice")
    quantity = _position_decimal(position, "quantity")
    avg_entry_price = _position_decimal(position, "avgEntryPrice")
    leverage = _position_decimal(position, "leverage")
    funding_key = "fundingDue" if "fundingDue" in position else "fundingFee"
    funding_fee = _position_decimal(position, funding_key, "0")

    try:
        factor = Decimal(str(safety_factor).strip())
    except (AttributeError, InvalidOperation, ValueError) as exc:
        raise ValueError("safety_factor must be a finite number") from exc
    if not factor.is_finite() or factor <= 0 or factor > 1:
        raise ValueError("safety_factor must be greater than 0 and at most 1")

    if margin < 0:
        raise ValueError("position field margin must not be negative")
    if quantity < 0:
        raise ValueError("position field quantity must not be negative")
    if oracle_price < 0:
        raise ValueError("position field oraclePrice must not be negative")
    if avg_entry_price < 0:
        raise ValueError("position field avgEntryPrice must not be negative")
    if leverage <= 0:
        raise ValueError("position field leverage must be greater than 0")

    side = str(position.get("side", "")).strip().upper()
    if side not in {"BUY", "LONG", "SELL", "SHORT"}:
        raise ValueError("position field side must be BUY/LONG or SELL/SHORT")

    decimals = (
        margin,
        oracle_price,
        quantity,
        avg_entry_price,
        leverage,
        funding_fee,
        factor,
    )
    precision = max(60, sum(len(value.as_tuple().digits) for value in decimals) + 20)
    with localcontext() as context:
        context.prec = precision
        margin_base = _to_base18_decimal(margin)
        oracle_price_base = _to_base18_decimal(oracle_price)
        quantity_base = _to_base18_decimal(quantity)
        avg_entry_price_base = _to_base18_decimal(avg_entry_price)
        leverage_base = _to_base18_decimal(leverage)
        funding_fee_base = _to_base18_decimal(funding_fee)
        factor_base = _to_base18_decimal(factor)

        if leverage_base <= 0:
            raise ValueError("position field leverage is below 1e-18 precision")

        mro_base = BASE_18_INT * BASE_18_INT // leverage_base
        notional_value_base = oracle_price_base * quantity_base // BASE_18_INT
        oi_open_base = avg_entry_price_base * quantity_base // BASE_18_INT
        min_funding_fee_base = min(funding_fee_base, 0)

        if side in {"BUY", "LONG"}:
            adjusted_notional_base = (
                notional_value_base * (BASE_18_INT - mro_base) // BASE_18_INT
            )
            calculated_base = (
                margin_base
                + adjusted_notional_base
                - oi_open_base
                + min_funding_fee_base
            )
        else:
            adjusted_notional_base = (
                notional_value_base * (BASE_18_INT + mro_base) // BASE_18_INT
            )
            calculated_base = (
                margin_base
                + oi_open_base
                - adjusted_notional_base
                + min_funding_fee_base
            )

        removable_base = min(margin_base, max(calculated_base, 0))
        removable_base = removable_base * factor_base // BASE_18_INT
        return from_base18_string(removable_base)


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
