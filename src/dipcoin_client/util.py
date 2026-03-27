"""通用小工具（定价精度、数量精度等）。"""


def normalize_price(price: float, precision: int) -> float:
    return round(price, precision)


def normalize_qty(qty: float, precision: int) -> float:
    return round(max(0.0, qty), precision)
