Networks = {
    "SUI_STAGING": {
        "url": "https://fullnode.testnet.sui.io:443",
        "apiGateway": "https://demoapi.dipcoin.io/exchange/",
        "webSocketURL": "wss://demows.dipcoin.io/stream/ws",
        "onboardingUrl": "dipcoin.io"
    },
    "SUI_PROD": {
        "url": "https://fullnode.mainnet.sui.io:443",
        "apiGateway": "https://gray-api.dipcoin.io",
        "webSocketURL": "wss://gray-ws.dipcoin.io/stream/ws",
        "onboardingUrl": "dipcoin.io"
    },

}

ORDER_FLAGS = {"IS_BUY": 1, "IS_DECREASE_ONLY": 2}

SUI_CLOCK_OBJECT_ID = "0x0000000000000000000000000000000000000000000000000000000000000006"

TIME = {
    "SECONDS_IN_A_MINUTE": 60,
    "SECONDS_IN_A_DAY": 86400,
    "SECONDS_IN_A_MONTH": 2592000,
}

ADDRESSES = {
    "ZERO": "0x0000000000000000000000000000000000000000",
}

SERVICE_URLS = {
    "MARKET": {
        "ORDER_BOOK": "/api/perp-market-api/orderBook",
        "CANDLE_STICK_DATA": "/api/perp-market-api/kline/history",
        "EXCHANGE_INFO": "/api/perp-market-api/list",
        "TICKER": "/api/perp-market-api/ticker",
    },
    "USER": {
        "USER_POSITIONS": "/api/perp-trade-api/curr-info/positions",
        "USER_TRADES": "/api/perp-trade-api/history/orders",
        "ORDERS": "/api/perp-trade-api/curr-info/orders",
        "ACCOUNT": "/api/perp-trade-api/curr-info/account",
        "AUTHORIZE": "/api/authorize",
        "FUNDING_HISTORY": "/api/perp-trade-api/history/funding-settlements",
    },
    "ORDERS": {
        "ORDERS": "/api/perp-trade-api/trade/placeorder",
        "ORDERS_CANCEL": "/api/perp-trade-api/trade/cancelorder",

    },
}
