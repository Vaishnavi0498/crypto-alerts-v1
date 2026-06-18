import threading
import time

from notifications import send_alert

MAX_BATCH_SIZE = 5
MAX_WAIT_SECONDS = 300  # 5 minutes

_lock = threading.Lock()
_pending = []
_first_alert_time = None


def queue_alert(symbol, price, notes):
    global _first_alert_time

    with _lock:
        # Replace existing alert for same symbol (optional but recommended)
        for i, alert in enumerate(_pending):
            if alert["symbol"] == symbol:
                _pending[i] = {
                    "symbol": symbol,
                    "price": price,
                    "notes": notes,
                }
                return

        _pending.append(
            {
                "symbol": symbol,
                "price": price,
                "notes": notes,
            }
        )

        if len(_pending) == 1:
            _first_alert_time = time.time()

        if len(_pending) >= MAX_BATCH_SIZE:
            _flush_locked()


def _flush_locked():
    global _pending, _first_alert_time

    if not _pending:
        return

    message = "🚨 RSI Alerts\n\n"

    for idx, alert in enumerate(_pending, start=1):
        message += (
            f"{idx}. {alert['symbol']}\n"
            f"Price: {alert['price']}\n"
            f"{alert['notes']}\n\n"
        )

    # Reuse existing notification function
    send_alert(
        symbol=f"{len(_pending)} Alerts",
        price="",
        notes=message,
    )

    _pending = []
    _first_alert_time = None


def background_flush_loop():
    while True:
        time.sleep(5)

        with _lock:
            if (
                _pending
                and _first_alert_time is not None
                and time.time() - _first_alert_time >= MAX_WAIT_SECONDS
            ):
                _flush_locked()