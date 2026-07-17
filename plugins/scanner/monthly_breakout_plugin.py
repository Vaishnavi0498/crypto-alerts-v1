from plugins.scanner.base_plugin import (
    BasePlugin
)

from services.rolling_high_service import (
    rolling_high_service
)


class MonthlyBreakoutPlugin(BasePlugin):

    ALERT_TYPE = "MONTHLY_BREAKOUT"

    def process(
        self,
        symbol,
        candles
    ):

        if len(candles) < 2:

            return []

        current = candles[-2]

        monthly_high = (
            rolling_high_service.get_high(
                symbol
            )
        )

        if monthly_high is None:

            return []

        current_high = current["high"]

        if current_high <= monthly_high:

            return []

        last_alerted = (
            rolling_high_service.get_last_alerted_level(
                symbol
            )
        )

        if last_alerted == monthly_high:

            return []

        rolling_high_service.mark_alerted(
            symbol,
            monthly_high
        )

        return [
            {
                "symbol": symbol,
                "price": current["close"],
                "notes":
f"""
🚀 MONTHLY BREAKOUT

Current High:
{current_high:.8f}

Previous 30-Day High:
{monthly_high:.8f}

The latest completed 1-minute candle
has broken above the previous
30-day highest price.

Potential continuation breakout.
"""
            }
        ]