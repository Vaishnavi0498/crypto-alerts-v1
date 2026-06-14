from http_client import SESSION


BASE_URL = (
    "https://fapi.binance.com/fapi/v1/klines"
)


def get_recent_candles(
    symbol,
    interval="1h",
    limit=20
):

    response = SESSION.get(
        BASE_URL,
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        },
        timeout=10
    )

    response.raise_for_status()

    candles = response.json()

    formatted = []

    for c in candles:

        formatted.append(
            {
                "open_time": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
                "close_time": c[6]
            }
        )

    return formatted