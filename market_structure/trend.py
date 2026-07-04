from market_structure.models import Pivot


class TrendDetector:

    def detect(
        self,
        pivots,
    ):

        highs = [
            p
            for p in pivots
            if p.kind == "HIGH"
        ]

        lows = [
            p
            for p in pivots
            if p.kind == "LOW"
        ]

        if len(highs) < 2 or len(lows) < 2:
            return "UNKNOWN"

        last_high = highs[-1].price
        prev_high = highs[-2].price

        last_low = lows[-1].price
        prev_low = lows[-2].price

        if (
            last_high > prev_high
            and last_low > prev_low
        ):
            return "BULLISH"

        if (
            last_high < prev_high
            and last_low < prev_low
        ):
            return "BEARISH"

        return "RANGE"