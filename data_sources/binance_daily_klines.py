from http_client import SESSION


BASE_URL = (
    "https://fapi.binance.com/fapi/v1/klines"
)


def get_daily_candles(
    symbol,
    limit=31
):

    response = SESSION.get(
        BASE_URL,
        params={
            "symbol": symbol,
            "interval": "1d",
            "limit": limit
        },
        timeout=10
    )

    response.raise_for_status()

    candles = response.json()

    formatted = []

    for candle in candles:

        formatted.append(
            {
                "open_time": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "close_time": candle[6],
            }
        )

    return formatted