from __future__ import annotations

from dataclasses import dataclass

from typing import List

from market_structure.config import MarketStructureConfig

@dataclass
class Displacement:

    side: str

    index: int

    open: float

    high: float

    low: float

    close: float

    body: float

    range: float

    body_ratio: float

    atr_ratio: float

    volume_ratio: float

    displacement_score: float

    consecutive_score: float

    bullish: bool

    bearish: bool


class DisplacementDetector:

    def __init__(

        self,

        config: MarketStructureConfig = MarketStructureConfig(),

    ):

        self.config = config

        self.ATR_PERIOD = 14

        self.BODY_PERIOD = 20

        self.VOLUME_PERIOD = 20

        self.MIN_BODY_RATIO = 0.70

        self.MIN_ATR_RATIO = 1.50

        self.MIN_VOLUME_RATIO = 1.50

        self.MIN_SCORE = 65

    # =========================================================

    # ATR

    # =========================================================

    def atr(

        self,

        candles,

        index,

    ):

        if index < self.ATR_PERIOD:

            return None

        trs = []

        for i in range(

            index - self.ATR_PERIOD + 1,

            index + 1,

        ):

            high = candles[i].high

            low = candles[i].low

            prev_close = candles[i - 1].close

            tr = max(

                high - low,

                abs(high - prev_close),

                abs(low - prev_close),

            )

            trs.append(tr)

        return sum(trs) / len(trs)

    # =========================================================

    # Average Body

    # =========================================================

    def average_body(

        self,

        candles,

        index,

    ):

        if index < self.BODY_PERIOD:

            return None

        bodies = []

        for i in range(

            index - self.BODY_PERIOD,

            index,

        ):

            bodies.append(

                abs(

                    candles[i].close -

                    candles[i].open

                )

            )

        return sum(bodies) / len(bodies)

    # =========================================================

    # Average Volume

    # =========================================================

    def average_volume(

        self,

        candles,

        index,

    ):

        if index < self.VOLUME_PERIOD:

            return None

        vols = []

        for i in range(

            index - self.VOLUME_PERIOD,

            index,

        ):

            vols.append(

                candles[i].volume

            )

        return sum(vols) / len(vols)

    # =========================================================

    # Candle Body

    # =========================================================

    def candle_body(

        self,

        candle,

    ):

        return abs(

            candle.close -

            candle.open

        )

    # =========================================================

    # Candle Range

    # =========================================================

    def candle_range(

        self,

        candle,

    ):

        return candle.high - candle.low

    # =========================================================

    # Body Ratio

    # =========================================================

    def body_ratio(

        self,

        candle,

    ):

        r = self.candle_range(candle)

        if r == 0:

            return 0

        return self.candle_body(candle) / r

    # =========================================================

    # Upper Wick

    # =========================================================

    def upper_wick(

        self,

        candle,

    ):

        return candle.high - max(

            candle.open,

            candle.close,

        )

    # =========================================================

    # Lower Wick

    # =========================================================

    def lower_wick(

        self,

        candle,

    ):

        return min(

            candle.open,

            candle.close,

        ) - candle.low

    # =========================================================

    # Bullish

    # =========================================================

    def bullish(

        self,

        candle,

    ):

        return candle.close > candle.open

    # =========================================================

    # Bearish

    # =========================================================

    def bearish(

        self,

        candle,

    ):

        return candle.close < candle.open

    # =========================================================

    # Consecutive Momentum

    # =========================================================

    def consecutive_score(

        self,

        candles,

        index,

    ):

        if index < 3:

            return 0

        score = 0

        direction = None

        current = candles[index]

        if self.bullish(current):

            direction = "bull"

        elif self.bearish(current):

            direction = "bear"

        else:

            return 0

        for i in range(

            index,

            max(

                index - 3,

                -1,

            ),

            -1,

        ):

            c = candles[i]

            if (

                direction == "bull"

                and

                self.bullish(c)

            ):

                score += 1

            elif (

                direction == "bear"

                and

                self.bearish(c)

            ):

                score += 1

            else:

                break

        return score

    # =========================================================

    # Bullish Rejection

    # =========================================================

    def bullish_rejection(

        self,

        candle,

    ):

        lower = self.lower_wick(candle)

        upper = self.upper_wick(candle)

        body = self.candle_body(candle)

        return (

            body > upper

            and

            lower < body

        )

    # =========================================================

    # Bearish Rejection

    # =========================================================

    def bearish_rejection(

        self,

        candle,

    ):

        lower = self.lower_wick(candle)

        upper = self.upper_wick(candle)

        body = self.candle_body(candle)

        return (

            body > lower

            and

            upper < body

        )

    # =========================================================

    # Raw Score

    # =========================================================

    def score(

        self,

        body_ratio,

        atr_ratio,

        volume_ratio,

        consecutive,

    ):

        score = 0

        score += min(

            body_ratio,

            1,

        ) * 30

        score += min(

            atr_ratio / 2,

            1,

        ) * 30

        score += min(

            volume_ratio / 2,

            1,

        ) * 20

        score += min(

            consecutive,

            3,

        ) * 20 / 3

        return score

    # =========================================================

    # Detect

    # =========================================================

    def detect(

        self,

        candles,

    ):

        results = []

        for i in range(

            self.VOLUME_PERIOD,

            len(candles),

        ):

            candle = candles[i]

            body = self.candle_body(candle)

            rng = self.candle_range(candle)

            if rng == 0:
                continue

            body_ratio = self.body_ratio(candle)

            atr = self.atr(candles, i)

            if atr is None or atr == 0:
                continue

            atr_ratio = rng / atr

            avg_volume = self.average_volume(candles, i)

            if avg_volume is None or avg_volume == 0:
                continue

            volume_ratio = candle.volume / avg_volume

            consecutive = self.consecutive_score(
                candles,
                i,
            )

            score = self.score(
                body_ratio,
                atr_ratio,
                volume_ratio,
                consecutive,
            )

            bullish = self.bullish(candle)

            bearish = self.bearish(candle)

            if bullish:

                if not self.bullish_rejection(candle):
                    continue

            elif bearish:

                if not self.bearish_rejection(candle):
                    continue

            else:
                continue

            if body_ratio < self.MIN_BODY_RATIO:
                continue

            if atr_ratio < self.MIN_ATR_RATIO:
                continue

            if volume_ratio < self.MIN_VOLUME_RATIO:
                continue

            if score < self.MIN_SCORE:
                continue

            displacement = Displacement(

                side="bullish" if bullish else "bearish",

                index=i,

                open=candle.open,

                high=candle.high,

                low=candle.low,

                close=candle.close,

                body=body,

                range=rng,

                body_ratio=body_ratio,

                atr_ratio=atr_ratio,

                volume_ratio=volume_ratio,

                displacement_score=score,

                consecutive_score=consecutive,

                bullish=bullish,

                bearish=bearish,

            )

            results.append(displacement)

        return results

    # =========================================================
    # Strongest displacement
    # =========================================================

    def strongest(
        self,
        displacements,
    ):

        if not displacements:
            return None

        return max(
            displacements,
            key=lambda x: x.displacement_score,
        )

    # =========================================================
    # Top N
    # =========================================================

    def top(
        self,
        displacements,
        n=10,
    ):

        return sorted(
            displacements,
            key=lambda x: x.displacement_score,
            reverse=True,
        )[:n]

    # =========================================================
    # Bullish only
    # =========================================================

    def bullish_only(
        self,
        displacements,
    ):

        return [
            d
            for d in displacements
            if d.bullish
        ]

    # =========================================================
    # Bearish only
    # =========================================================

    def bearish_only(
        self,
        displacements,
    ):

        return [
            d
            for d in displacements
            if d.bearish
        ]

    # =========================================================
    # Latest
    # =========================================================

    def latest(
        self,
        displacements,
    ):

        if not displacements:
            return None

        return displacements[-1]

    # =========================================================
    # Run
    # =========================================================

    def run(
        self,
        candles,
    ):

        displacements = self.detect(candles)

        return {

            "all": displacements,

            "strongest": self.strongest(
                displacements,
            ),

            "bullish": self.bullish_only(
                displacements,
            ),

            "bearish": self.bearish_only(
                displacements,
            ),

            "top": self.top(
                displacements,
            ),

            "latest": self.latest(
                displacements,
            ),

        }


if __name__ == "__main__":

    print("=" * 80)

    print("Displacement Detector")

    print("=" * 80)