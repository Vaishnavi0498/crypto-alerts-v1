from __future__ import annotations

from dataclasses import dataclass
from typing import List

from market_structure.models import Candle


# ============================================================
# FAIR VALUE GAP MODEL
# ============================================================


@dataclass
class FairValueGap:

    side: str

    start_index: int

    middle_index: int

    end_index: int

    upper: float

    lower: float

    size: float

    percentage: float

    impulse_size: float

    displacement_score: float

    body_ratio: float

    filled: bool = False

    fill_index: int | None = None

    partial_fill: bool = False

    partial_fill_percentage: float = 0.0

    invalidated: bool = False

    respected: bool = False

    score: float = 0.0

    premium_discount: str = ""

    associated_ob = None

    associated_liquidity = None

    associated_bos = None

    associated_choch = None


# ============================================================
# DETECTOR
# ============================================================


class FairValueGapDetector:

    MIN_GAP_PERCENT = 0.0004

    MIN_BODY_RATIO = 0.60

    MIN_IMPULSE = 0.40

    MIN_SCORE = 40

    MAX_GAPS = 25

    LOOKAHEAD_FILL = 120

    PREMIUM_DISCOUNT_LOOKBACK = 250

    # --------------------------------------------------------

    def candle_body_ratio(
        self,
        candle: Candle,
    ):

        total = candle.high - candle.low

        if total <= 0:
            return 0

        body = abs(
            candle.close - candle.open
        )

        return body / total

    # --------------------------------------------------------

    def bullish_gap(
        self,
        candles: List[Candle],
        i: int,
    ):

        left = candles[i]

        middle = candles[i + 1]

        right = candles[i + 2]

        if right.low <= left.high:
            return None

        gap = right.low - left.high

        pct = gap / middle.close

        if pct < self.MIN_GAP_PERCENT:
            return None

        impulse = abs(
            middle.close - middle.open
        )

        body_ratio = self.candle_body_ratio(
            middle,
        )

        if body_ratio < self.MIN_BODY_RATIO:
            return None

        return FairValueGap(

            side="BULLISH",

            start_index=i,

            middle_index=i + 1,

            end_index=i + 2,

            upper=right.low,

            lower=left.high,

            size=gap,

            percentage=pct,

            impulse_size=impulse,

            displacement_score=0,

            body_ratio=body_ratio,
        )

    # --------------------------------------------------------

    def bearish_gap(
        self,
        candles: List[Candle],
        i: int,
    ):

        left = candles[i]

        middle = candles[i + 1]

        right = candles[i + 2]

        if right.high >= left.low:
            return None

        gap = left.low - right.high

        pct = gap / middle.close

        if pct < self.MIN_GAP_PERCENT:
            return None

        impulse = abs(
            middle.close - middle.open
        )

        body_ratio = self.candle_body_ratio(
            middle,
        )

        if body_ratio < self.MIN_BODY_RATIO:
            return None

        return FairValueGap(

            side="BEARISH",

            start_index=i,

            middle_index=i + 1,

            end_index=i + 2,

            upper=left.low,

            lower=right.high,

            size=gap,

            percentage=pct,

            impulse_size=impulse,

            displacement_score=0,

            body_ratio=body_ratio,
        )

    # --------------------------------------------------------

    def raw_gaps(
        self,
        candles: List[Candle],
    ):

        gaps = []

        for i in range(
            len(candles) - 2
        ):

            bullish = self.bullish_gap(
                candles,
                i,
            )

            if bullish is not None:
                gaps.append(bullish)

            bearish = self.bearish_gap(
                candles,
                i,
            )

            if bearish is not None:
                gaps.append(bearish)

        return gaps

    # --------------------------------------------------------

    def displacement_score(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        for gap in gaps:

            candle = candles[
                gap.middle_index
            ]

            rng = (
                candle.high - candle.low
            )

            if rng <= 0:

                gap.displacement_score = 0

                continue

            gap.displacement_score = (
                gap.impulse_size
                / rng
            )

        return gaps

    # --------------------------------------------------------

    def remove_small_impulse(
        self,
        gaps: List[FairValueGap],
    ):

        return [

            gap

            for gap in gaps

            if gap.displacement_score >= self.MIN_IMPULSE

        ]

    # --------------------------------------------------------

    def detect_fill(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        for gap in gaps:

            end = min(
                len(candles),
                gap.end_index + self.LOOKAHEAD_FILL,
            )

            for i in range(
                gap.end_index + 1,
                end,
            ):

                candle = candles[i]

                if gap.side == "BULLISH":

                    # complete fill

                    if candle.low <= gap.lower:

                        gap.filled = True
                        gap.fill_index = i
                        break

                    # partial fill

                    elif candle.low < gap.upper:

                        gap.partial_fill = True

                        penetration = (
                            gap.upper - candle.low
                        )

                        gap.partial_fill_percentage = (
                            penetration / gap.size
                        )

                else:

                    if candle.high >= gap.upper:

                        gap.filled = True
                        gap.fill_index = i
                        break

                    elif candle.high > gap.lower:

                        gap.partial_fill = True

                        penetration = (
                            candle.high - gap.lower
                        )

                        gap.partial_fill_percentage = (
                            penetration / gap.size
                        )

        return gaps

    # --------------------------------------------------------

    def detect_respect(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        for gap in gaps:

            if gap.filled:
                continue

            end = min(
                len(candles),
                gap.end_index + 30,
            )

            for i in range(
                gap.end_index + 1,
                end,
            ):

                candle = candles[i]

                if gap.side == "BULLISH":

                    if (
                        candle.low <= gap.upper
                        and candle.close > gap.upper
                    ):

                        gap.respected = True
                        break

                else:

                    if (
                        candle.high >= gap.lower
                        and candle.close < gap.lower
                    ):

                        gap.respected = True
                        break

        return gaps

    # --------------------------------------------------------

    def detect_invalidation(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        for gap in gaps:

            end = min(
                len(candles),
                gap.end_index + 150,
            )

            for i in range(
                gap.end_index + 1,
                end,
            ):

                candle = candles[i]

                if gap.side == "BULLISH":

                    if candle.close < gap.lower:

                        gap.invalidated = True
                        break

                else:

                    if candle.close > gap.upper:

                        gap.invalidated = True
                        break

        return gaps

    # --------------------------------------------------------

    def premium_discount(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        lookback = candles[
            -self.PREMIUM_DISCOUNT_LOOKBACK:
        ]

        highest = max(
            c.high
            for c in lookback
        )

        lowest = min(
            c.low
            for c in lookback
        )

        equilibrium = (
            highest + lowest
        ) / 2

        for gap in gaps:

            midpoint = (
                gap.upper + gap.lower
            ) / 2

            if midpoint > equilibrium:

                gap.premium_discount = "PREMIUM"

            else:

                gap.premium_discount = "DISCOUNT"

        return gaps

    # --------------------------------------------------------

    def score(
        self,
        candles: List[Candle],
        gaps: List[FairValueGap],
    ):

        for gap in gaps:

            score = 0

            score += min(
                gap.displacement_score * 40,
                40,
            )

            score += min(
                gap.body_ratio * 20,
                20,
            )

            score += min(
                gap.percentage * 8000,
                20,
            )

            if gap.respected:
                score += 10

            if gap.partial_fill:
                score += 5

            if gap.filled:
                score -= 30

            if gap.invalidated:
                score -= 40

            gap.score = score

        return gaps

    # --------------------------------------------------------

    def remove_invalid(
        self,
        gaps: List[FairValueGap],
    ):

        return [

            gap

            for gap in gaps

            if (
                not gap.invalidated
                and gap.score >= self.MIN_SCORE
            )

        ]

    # --------------------------------------------------------

    def sort(
        self,
        gaps: List[FairValueGap],
    ):

        return sorted(

            gaps,

            key=lambda g: (

                g.score,

                g.displacement_score,

                g.percentage,

            ),

            reverse=True,

        )

    # ============================================================
    # Merge overlapping FVGs
    # ============================================================

    def merge_overlapping(
        self,
        gaps: list[FairValueGap],
    ) -> list[FairValueGap]:

        if not gaps:
            return []

        gaps = sorted(
            gaps,
            key=lambda x: (
                x.side,
                x.lower,
            ),
        )

        merged = []

        current = gaps[0]

        for gap in gaps[1:]:

            if gap.side != current.side:

                merged.append(current)

                current = gap

                continue

            overlap = (
                gap.lower <= current.upper
            )

            if overlap:

                current.upper = max(
                    current.upper,
                    gap.upper,
                )

                current.lower = min(
                    current.lower,
                    gap.lower,
                )

                current.score = max(
                    current.score,
                    gap.score,
                )

                current.displacement_score = max(
                    current.displacement_score,
                    gap.displacement_score,
                )

                current.end_index = max(
                    current.end_index,
                    gap.end_index,
                )

            else:

                merged.append(current)

                current = gap

        merged.append(current)

        return merged

    # ============================================================
    # Nearby FVG search
    # ============================================================

    def nearest_gap(

        self,

        price: float,

        side: str,

        gaps: list[FairValueGap],

    ):

        best = None

        best_distance = float("inf")

        for gap in gaps:

            if gap.side != side:

                continue

            center = (

                gap.upper +

                gap.lower

            ) / 2

            distance = abs(

                center -

                price

            )

            if distance < best_distance:

                best_distance = distance

                best = gap

        return best

    # ============================================================
    # Gap quality
    # ============================================================

    def quality_score(

        self,

        gap: FairValueGap,

    ):

        score = 0

        score += gap.displacement_score * 40

        score += gap.percentage * 30

        score += gap.score * 30

        return score

    # ============================================================
    # Filter weak gaps
    # ============================================================

    def strongest(

        self,

        gaps,

        limit=20,

    ):

        gaps = sorted(

            gaps,

            key=self.quality_score,

            reverse=True,

        )

        return gaps[:limit]

    # ============================================================
    # Bullish only
    # ============================================================

    def bullish(

        self,

        gaps,

    ):

        return [

            g

            for g in gaps

            if g.side == "bullish"

        ]

    # ============================================================
    # Bearish only
    # ============================================================

    def bearish(

        self,

        gaps,

    ):

        return [

            g

            for g in gaps

            if g.side == "bearish"

        ]

    # ============================================================
    # Untouched gaps
    # ============================================================

    def untouched(

        self,

        gaps,

    ):

        return [

            g

            for g in gaps

            if not g.filled

        ]

    # ============================================================
    # Filled gaps
    # ============================================================

    def filled(

        self,

        gaps,

    ):

        return [

            g

            for g in gaps

            if g.filled

        ]

    # ============================================================
    # Active trading gaps
    # ============================================================

    def active(

        self,

        gaps,

    ):

        return [

            g

            for g in gaps

            if (

                not g.filled

                and

                not g.invalidated

            )

        ]

    # ============================================================
    # Gap statistics
    # ============================================================

    def statistics(

        self,

        gaps,

    ):

        return {

            "total": len(gaps),

            "bullish": len(

                self.bullish(gaps)

            ),

            "bearish": len(

                self.bearish(gaps)

            ),

            "active": len(

                self.active(gaps)

            ),

            "filled": len(

                self.filled(gaps)

            ),

            "untouched": len(

                self.untouched(gaps)

            ),

        }

    # ============================================================
    # Master API
    # ============================================================

    def detect(

        self,

        candles,

    ):

        gaps = self.raw_gaps(candles)

        gaps = self.score(candles, gaps)

        gaps = self.detect_fill(candles, gaps)

        gaps = self.detect_invalidation(candles, gaps)

        gaps = self.merge_overlapping(gaps)

        strongest = self.strongest(gaps)

        return gaps