import os
import time
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


NTFY_TOPIC = os.getenv(
    "NTFY_TOPIC",
    "crypto-alerts"
)

NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


def send_ntfy_alert(
    symbol,
    price,
    notes
):

    title = f"{symbol} Alert"

    message = f"""
CRYPTO ALERT

Symbol:
{symbol}

Current Price:
{price}

Analysis:
--------------------------------

{notes}

--------------------------------
"""

    retries = 3

    for attempt in range(retries):

        try:

            response = requests.post(
                NTFY_URL,
                data=message.encode("utf-8"),
                headers={
                    "Title": title
                },
                timeout=10
            )

            if response.status_code == 200:

                print(
                    f"NTFY SENT: {symbol}"
                )

                return True

            print(
                f"NTFY FAILED: "
                f"{response.status_code}"
            )

        except requests.exceptions.Timeout:

            print(
                f"NTFY TIMEOUT: {symbol}"
            )

        except requests.exceptions.RequestException as e:

            print(
                f"NTFY REQUEST ERROR: {e}"
            )

        time.sleep(
            2 ** attempt
        )

    return False


def send_alert(
    symbol,
    price,
    notes
):

    print()
    print("=" * 60)
    print("ALERT")
    print("=" * 60)

    print(
        f"SYMBOL: {symbol}"
    )

    print(
        f"PRICE: {price}"
    )

    print()

    if notes:

        print(notes)

    print()
    print("=" * 60)

    send_ntfy_alert(
        symbol,
        price,
        notes
    )