import asyncio
import os
import time
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger

from config import *
from dipcoin_client import (
    DipcoinClient,
    Networks,
    MARKET_SYMBOLS,
    ORDER_SIDE,
    ORDER_TYPE,
    OrderSignatureRequest,
    from1e18,
    normalize_price,
    normalize_qty,
)

os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/sui_taker_pingpong.log",
    rotation="1 day",
    retention="7 days",
    enqueue=True,
    encoding="utf-8",
)


@dataclass
class PingPongConfig:
    symbol: MARKET_SYMBOLS = MARKET_SYMBOLS.SUI
    leverage: float = 3.0
    trade_qty: float = 100.0
    poll_interval_sec: int = 50
    orderbook_limit: int = 5
    # 每次开仓方向交替：False->开多, True->开空
    alternate_side: bool = True


def _parse_price(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return from1e18(v)
    except Exception:
        return None


def _parse_qty(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return from1e18(v)
    except Exception:
        return None


async def get_best_bid_ask(client: DipcoinClient, cfg: PingPongConfig) -> Tuple[Optional[float], Optional[float]]:
    try:
        ob = await client.get_orderbook({"symbol": cfg.symbol, "limit": cfg.orderbook_limit})
    except Exception as e:
        logger.warning("get_orderbook failed: {}", e)
        return None, None

    raw = ob.get("data", ob) if isinstance(ob, dict) else ob
    if not isinstance(raw, dict):
        return None, None

    bids = raw.get("bids") or raw.get("bid") or []
    asks = raw.get("asks") or raw.get("ask") or []

    best_bid = None
    best_ask = None

    if isinstance(bids, list) and bids:
        row = bids[0]
        if isinstance(row, dict):
            best_bid = _parse_price(row.get("price") or row.get("p"))
        elif isinstance(row, (list, tuple)) and row:
            best_bid = _parse_price(row[0])

    if isinstance(asks, list) and asks:
        row = asks[0]
        if isinstance(row, dict):
            best_ask = _parse_price(row.get("price") or row.get("p"))
        elif isinstance(row, (list, tuple)) and row:
            best_ask = _parse_price(row[0])

    return best_bid, best_ask


async def get_position_simple(client: DipcoinClient, cfg: PingPongConfig) -> Tuple[Optional[str], float]:
    """
    返回 (side, qty)
    side: "LONG" / "SHORT" / None
    qty: >=0
    """
    try:
        resp = await client.get_user_position({"symbol": cfg.symbol})
    except Exception as e:
        logger.warning("get_user_position failed: {}", e)
        return None, 0.0

    rows = []
    if isinstance(resp, dict):
        data = resp.get("data")
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and isinstance(data.get("data"), list):
            rows = data.get("data") or []

    symbol_rows = [p for p in rows if str(p.get("symbol")) == cfg.symbol.value]
    if not symbol_rows:
        return None, 0.0

    row = symbol_rows[0]
    side_raw = str(row.get("side") or "").upper()
    qty_raw = row.get("quantity") or "0"
    qty = abs(_parse_qty(qty_raw) or 0.0)

    side = None
    if side_raw in ("BUY", "LONG"):
        side = "LONG"
    elif side_raw in ("SELL", "SHORT"):
        side = "SHORT"
    return side, qty


async def place_market(
        client: DipcoinClient,
        cfg: PingPongConfig,
        side: ORDER_SIDE,
        quantity: float,
        reduce_only: bool,
) -> dict:
    # MARKET=吃单(taker)，price=0
    req = OrderSignatureRequest(
        symbol=cfg.symbol,
        price=0,
        quantity=quantity,
        side=side,
        orderType=ORDER_TYPE.MARKET,
        leverage=cfg.leverage,
        expiration=0,
        reduceOnly=reduce_only,
        ioc=False,
        postOnly=False,
        orderbookOnly=True,
    )
    signed = client.create_signed_order(req)
    return await client.post_signed_order(signed)


async def loop_pingpong(client: DipcoinClient, cfg: PingPongConfig) -> None:
    next_open_short = False
    while True:
        try:
            # query order book
            best_bid, best_ask = await get_best_bid_ask(client, cfg)
            # query position
            pos_side, pos_qty = await get_position_simple(client, cfg)
            # query account
            account_data = await client.get_user_account_data()
            open_orders = await client.get_orders({})
            ### 

            logger.info(
                "OB best_bid={} best_ask={} | position side={} qty={}| account_data={},open_orders={}",
                best_bid,
                best_ask,
                pos_side,
                pos_qty,
                account_data,
                open_orders
            )
            ##add tpsl plan
            #sui price precision is 4
            #sui qty precision is 0
            #resp = await client.set_take_profit_plan(cfg.symbol, ORDER_SIDE.SELL, normalize_price(best_bid*1.1,4), normalize_price(best_bid*1.1,4), normalize_qty(pos_qty,0), cfg.leverage)
            #logger.info("SET TP PLAN resp={}", resp)
            #resp = await client.set_stop_loss_plan(cfg.symbol, ORDER_SIDE.SELL, normalize_price(best_ask*0.9,4), normalize_price(best_ask*0.9,4), normalize_qty(pos_qty,0)    , cfg.leverage)
            #logger.info("SET SL PLAN resp={}", resp)
            #time.sleep(90)
           

            if pos_side is not None and pos_qty > 0:
                # 有仓位：市价平仓（taker）
                close_side = ORDER_SIDE.SELL if pos_side == "LONG" else ORDER_SIDE.BUY
                resp = await place_market(client, cfg, close_side, pos_qty, reduce_only=True)
                logger.info("CLOSE {} qty={} resp={}", pos_side, pos_qty, resp)
                await asyncio.sleep(max(1, cfg.poll_interval_sec))
                continue

            # 无仓位：市价开仓（taker）
            if cfg.alternate_side:
                open_side = ORDER_SIDE.SELL if next_open_short else ORDER_SIDE.BUY
                next_open_short = not next_open_short
            else:
                open_side = ORDER_SIDE.BUY

            resp = await place_market(client, cfg, open_side, cfg.trade_qty, reduce_only=False)
            logger.info("OPEN {} qty={} resp={}", open_side.value, cfg.trade_qty, resp)

        except Exception as e:
            logger.error("Pingpong loop error: {}", e)

        await asyncio.sleep(cfg.poll_interval_sec)


async def main() -> None:
    ### 0xf8e10afae1ece75bc3274135047be555ac119dbb3a1e29312e4504510c055059 is sub account of 0x770e6c2abe4f5334fb3b95ae7f1047f33385fe54033d90550bbd2fe5b422fee2
    ### 0x770e6c2abe4f5334fb3b95ae7f1047f33385fe54033d90550bbd2fe5b422fee2 is main account
    ### suiprivkey1qp0rnv5knxrrutqg3q0u34yrxdae8jx573cmycjua5svr5cdlsfhzsv0dve is private key of 0xf8e10afae1ece75bc3274135047be555ac119dbb3a1e29312e4504510c055059



    client = DipcoinClient(
        True,
        Networks[TEST_NETWORK],
        "suiprivkey1qp0rnv5knxrrutqg3q0u34yrxdae8jx573cmycjua5svr5cdlsfhzsv0dve",
        parentAddress="0x770e6c2abe4f5334fb3b95ae7f1047f33385fe54033d90550bbd2fe5b422fee2"
    )
    await client.init(True)

    cfg = PingPongConfig()
    logger.info("Starting SUI taker pingpong with config: {}", cfg)
    try:
        await loop_pingpong(client, cfg)
    finally:
        await client.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
