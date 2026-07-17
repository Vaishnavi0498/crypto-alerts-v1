from plugins.scanner.base_plugin import (
    BasePlugin
)

from services.rolling_high_service import (
    rolling_high_service
)


class MonthlyBreakoutPlugin(BasePlugin):

    ALERT_TYPE = "ROLLING_HIGH_BREAKOUT"

    def process(
        self,
        symbol,
        candles
    ):

        if len(candles) < 2:

            return []

        current = candles[-2]

        current_high = current["high"]

        high_30 = rolling_high_service.get_high(
            symbol,
            30
        )

        high_60 = rolling_high_service.get_high(
            symbol,
            60
        )

        high_90 = rolling_high_service.get_high(
            symbol,
            90
        )

        if (
            high_30 is None
            or high_60 is None
            or high_90 is None
        ):

            return []
        TEST_PERCENT = 0.96
        broke_30 = current_high > (high_30 * TEST_PERCENT)
        broke_60 = current_high > (high_60 * TEST_PERCENT)
        broke_90 = current_high > (high_90 * TEST_PERCENT)

        if not (
            broke_30
            or broke_60
            or broke_90
        ):

            return []

        if broke_90:

            lookback = 90

            title = "🚀 3 MONTH BREAKOUT"

            breakout_level = high_90

        elif broke_60:

            lookback = 60

            title = "🚀 2 MONTH BREAKOUT"

            breakout_level = high_60

        else:

            lookback = 30

            title = "🔥 MONTHLY BREAKOUT"

            breakout_level = high_30

        last_alerted = (
            rolling_high_service.get_last_alerted_level(
                symbol,
                lookback
            )
        )

        if last_alerted == breakout_level:

            return []

        rolling_high_service.mark_alerted(
            symbol,
            lookback,
            breakout_level
        )

        notes = f"""
{title}

Symbol:
{symbol}

Price:
{current["close"]}

Current High:
{current_high:.8f}

{"✅" if broke_30 else "❌"} 30 Day High: {high_30:.8f}

{"✅" if broke_60 else "❌"} 60 Day High: {high_60:.8f}

{"✅" if broke_90 else "❌"} 90 Day High: {high_90:.8f}

The latest completed 1-minute candle
has broken above the highlighted
rolling high level.
"""

        return [
            {
                "symbol": symbol,
                "price": current["close"],
                "notes": notes
            }
        ]