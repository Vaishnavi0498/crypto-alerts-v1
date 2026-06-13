import time
import requests

BINANCE_URL = (
    "https://fapi.binance.com/fapi/v1/exchangeInfo"
)

COINDCX_URL = (
    "https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments"
)

CACHE_SECONDS = 60 * 60 * 24

_cached_symbols = []
_last_refresh = 0


def _load_symbols():

    binance_response = requests.get(
        BINANCE_URL,
        timeout=30
    )

    binance_data = (
        binance_response.json()
    )

    binance_symbols = set()

    for item in binance_data["symbols"]:

        if (
            item["status"] == "TRADING"
            and item["contractType"] == "PERPETUAL"
        ):

            binance_symbols.add(
                item["symbol"]
            )

    coindcx_response = requests.get(
        COINDCX_URL,
        timeout=30
    )

    coindcx_data = (
        coindcx_response.json()
    )

    coindcx_symbols = set()

    for item in coindcx_data:

        if not item.startswith("B-"):
            continue

        symbol = item[2:]          # Remove "B-"
        symbol = symbol.replace("_", "")

        coindcx_symbols.add(symbol)

    return sorted(
        list(
            binance_symbols.intersection(
                coindcx_symbols
            )
        )
    )


def get_symbols():

    global _cached_symbols
    global _last_refresh

    now = time.time()

    if (
        not _cached_symbols
        or
        now - _last_refresh > CACHE_SECONDS
    ):

        try:

            _cached_symbols = (
                _load_symbols()
            )

            _last_refresh = now

        except Exception as e:

            print(
                f"Failed to refresh symbols: {e}"
            )

            if not _cached_symbols:
                raise

    return _cached_symbols

if __name__ == "__main__":

    symbols = get_symbols()

    print(f"Total common symbols: {len(symbols)}")
    print(symbols[:20])
    print(symbols[-20:])
    print("List of coins")
    print(sorted(list(symbols))[:20])