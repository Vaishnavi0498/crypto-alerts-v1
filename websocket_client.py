import asyncio
import json
import websockets

from database import get_monitored_symbols
from alert_engine import evaluate_alerts
from notifications import send_alert
from datetime import datetime, UTC
from price_cache import (
    init_price_table,
    update_price,
    get_price
)


class SymbolMonitor:

    def __init__(self):
        self.current_symbols = []

    def get_symbols(self):

        symbols = get_monitored_symbols()

        if not symbols:
            symbols = ["BTCUSDT"]

        return sorted(symbols)

    async def listen(self):

        while True:

            try:

                new_symbols = self.get_symbols()

                if new_symbols != self.current_symbols:

                    self.current_symbols = new_symbols

                    print()
                    print("=" * 60)
                    print("LOADING SYMBOLS")
                    print(self.current_symbols)
                    print("=" * 60)
                    print()

                streams = "/".join(
                    [
                        f"{s.lower()}@trade"
                        for s in self.current_symbols
                    ]
                )

                url = (
                    "wss://fstream.binance.com/stream?streams="
                    + streams
                )

                async with websockets.connect(url) as ws:

                    reconnect_check = 0

                    while True:

                        message = await ws.recv()

                        data = json.loads(message)

                        trade = data["data"]

                        symbol = trade["s"]

                        price = float(trade["p"])

                        if price <= 0:

                            continue

                        if symbol in ["BTCUSDT", "ETHUSDT"]:

                            cached = get_price(symbol)

                            if (
                                cached is not None
                                and cached > 0
                                and abs(price - cached) / cached > 0.50
                            ):
                                print(
                                    "REJECTING SUSPICIOUS PRICE",
                                    symbol,
                                    price,
                                    cached
                                )
                                continue

                        update_price(
                            symbol,
                            price,
                            datetime.now(UTC).isoformat()
                        )

                        events = evaluate_alerts(
                            symbol,
                            price
                        )

                        for event in events:

                            send_alert(
                                symbol=event["symbol"],
                                price=event["price"],
                                notes=event["notes"]
                            )

                        reconnect_check += 1

                        if reconnect_check >= 100:

                            latest_symbols = self.get_symbols()

                            if latest_symbols != self.current_symbols:

                                print()
                                print(
                                    "NEW SYMBOL DETECTED - RECONNECTING"
                                )
                                print()

                                break

                            reconnect_check = 0

            except Exception as e:

                print()
                print(
                    "CONNECTION ERROR:",
                    e
                )
                print()

                await asyncio.sleep(5)


if __name__ == "__main__":

    init_price_table()

    monitor = SymbolMonitor()

    asyncio.run(
        monitor.listen()
    )