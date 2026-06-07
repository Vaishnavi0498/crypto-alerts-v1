import requests

BINANCE_FUTURES_INFO_URL = (
    "https://fapi.binance.com/fapi/v1/exchangeInfo"
)


def get_futures_symbols():

    response = requests.get(
        BINANCE_FUTURES_INFO_URL,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    symbols = []

    for item in data["symbols"]:

        if item["status"] != "TRADING":
            continue

        if item["contractType"] != "PERPETUAL":
            continue

        symbols.append(
            item["symbol"]
        )

    symbols.sort()

    return symbols


if __name__ == "__main__":

    symbols = get_futures_symbols()

    print(
        f"Loaded {len(symbols)} futures symbols"
    )

    print(symbols[:20])