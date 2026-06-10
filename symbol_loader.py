import requests


def get_all_futures_symbols():

    url = (
        "https://fapi.binance.com/fapi/v1/exchangeInfo"
    )

    response = requests.get(
        url,
        timeout=30
    )

    data = response.json()

    symbols = []

    for item in data["symbols"]:

        if (
            item["status"] == "TRADING"
            and item["contractType"]
            == "PERPETUAL"
        ):

            symbols.append(
                item["symbol"]
            )

    return sorted(symbols)