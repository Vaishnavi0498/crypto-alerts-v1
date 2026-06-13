import json
import os
import time
import requests

CACHE_FILE = "data/coindcx_symbols.json"
CACHE_TTL_SECONDS = 24 * 60 * 60

URL = "https://api.coindcx.com/exchange/v1/markets"


def load_coindcx_symbols():

    if os.path.exists(CACHE_FILE):

        age = (
            time.time()
            - os.path.getmtime(CACHE_FILE)
        )

        if age < CACHE_TTL_SECONDS:

            with open(
                CACHE_FILE,
                "r"
            ) as f:

                return set(
                    json.load(f)
                )

    response = requests.get(
        URL,
        timeout=20
    )

    response.raise_for_status()

    markets = response.json()

    symbols = set()

    for market in markets:

        pair = market.get(
            "coindcx_name",
            ""
        )

        if pair.endswith("USDT"):

            symbols.add(
                pair.upper()
            )

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        CACHE_FILE,
        "w"
    ) as f:

        json.dump(
            sorted(symbols),
            f
        )

    return symbols