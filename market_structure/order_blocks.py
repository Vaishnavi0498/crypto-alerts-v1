from dataclasses import dataclass
from typing import List, Optional

from market_structure.models import Candle
from market_structure.bos import BOS
from market_structure.choch import CHOCH
from market_structure.liquidity import LiquidityLevel


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class OrderBlock:

    side: str

    candle_index: int

    candle_time: int

    open: float

    high: float

    low: float

    close: float

    volume: float

    body_size: float

    range_size: float

    mitigation_level: float

    validity_level: float

    impulse_index: int

    impulse_size: float

    bos_index: Optional[int]

    choch_index: Optional[int]

    liquidity_index: Optional[int]

    mitigated: bool = False

    mitigation_index: Optional[int] = None

    breaker: bool = False

    invalidated: bool = False

    score: float = 0.0

    fresh: bool = True

    @property
    def price(self):
        return (self.high + self.low) / 2


# ============================================================
# ORDER BLOCK DETECTOR
# ============================================================

class OrderBlockDetector:

    BODY_THRESHOLD = 0.35

    IMPULSE_MULTIPLIER = 1.5

    LOOKAHEAD = 8

    MAX_MITIGATION_LOOKAHEAD = 300

    MIN_SCORE = 45

    MAX_BLOCKS = 8

    # ---------------------------------------------------------

    def body_ratio(
        self,
        candle: Candle,
    ):

        rng = candle.high - candle.low

        if rng <= 0:
            return 0

        return abs(
            candle.close - candle.open
        ) / rng

    # ---------------------------------------------------------

    def bullish_candle(
        self,
        candle: Candle,
    ):

        return candle.close > candle.open

    # ---------------------------------------------------------

    def bearish_candle(
        self,
        candle: Candle,
    ):

        return candle.close < candle.open

    # ---------------------------------------------------------

    def average_range(
        self,
        candles: List[Candle],
        end_index: int,
        period: int = 20,
    ):

        start = max(
            0,
            end_index - period,
        )

        values = []

        for c in candles[start:end_index]:

            values.append(
                c.high - c.low
            )

        if not values:
            return 0

        return sum(values) / len(values)

    # ---------------------------------------------------------

    def impulse_after(
        self,
        candles,
        index,
        bullish=True,
    ):

        avg_range = self.average_range(
            candles,
            index,
        )

        if avg_range == 0:
            return None

        current_high = candles[index].high
        current_low = candles[index].low

        for j in range(
            index + 1,
            min(
                len(candles),
                index + self.LOOKAHEAD,
            ),
        ):

            move = (
                candles[j].close
                - candles[index].close
            )

            if bullish:

                if move > avg_range * self.IMPULSE_MULTIPLIER:

                    return (
                        j,
                        move,
                    )

            else:

                if -move > avg_range * self.IMPULSE_MULTIPLIER:

                    return (
                        j,
                        -move,
                    )

        return None

    # =========================================================
    # BULLISH ORDER BLOCK
    # =========================================================

    def bullish_candidates(
        self,
        candles: List[Candle],
    ):

        obs = []

        for i in range(
            20,
            len(candles) - self.LOOKAHEAD,
        ):

            candle = candles[i]

            if not self.bearish_candle(
                candle
            ):
                continue

            ratio = self.body_ratio(
                candle
            )

            if ratio < self.BODY_THRESHOLD:
                continue

            impulse = self.impulse_after(
                candles,
                i,
                bullish=True,
            )

            if impulse is None:
                continue

            impulse_index, impulse_size = impulse

            ob = OrderBlock(

                side="BULLISH",

                candle_index=i,

                candle_time=candle.close_time,

                open=candle.open,

                high=candle.high,

                low=candle.low,

                close=candle.close,

                volume=candle.volume,

                body_size=abs(
                    candle.close
                    - candle.open
                ),

                range_size=(
                    candle.high
                    - candle.low
                ),

                mitigation_level=candle.high,

                validity_level=candle.low,

                impulse_index=impulse_index,

                impulse_size=impulse_size,

                bos_index=None,

                choch_index=None,

                liquidity_index=None,
            )

            obs.append(ob)

        return obs

    # =========================================================
    # BEARISH ORDER BLOCK
    # =========================================================

    def bearish_candidates(
        self,
        candles,
    ):

        obs = []

        for i in range(
            20,
            len(candles)
            - self.LOOKAHEAD,
        ):

            candle = candles[i]

            if not self.bullish_candle(
                candle
            ):
                continue

            ratio = self.body_ratio(
                candle
            )

            if ratio < self.BODY_THRESHOLD:
                continue

            impulse = self.impulse_after(
                candles,
                i,
                bullish=False,
            )

            if impulse is None:
                continue

            impulse_index, impulse_size = impulse

            ob = OrderBlock(

                side="BEARISH",

                candle_index=i,

                candle_time=candle.close_time,

                open=candle.open,

                high=candle.high,

                low=candle.low,

                close=candle.close,

                volume=candle.volume,

                body_size=abs(
                    candle.close
                    - candle.open
                ),

                range_size=(
                    candle.high
                    - candle.low
                ),

                mitigation_level=candle.low,

                validity_level=candle.high,

                impulse_index=impulse_index,

                impulse_size=impulse_size,

                bos_index=None,

                choch_index=None,

                liquidity_index=None,
            )

            obs.append(ob)

        return obs

    # =========================================================
    # BOS CONFIRMATION
    # =========================================================

    def attach_bos(
        self,
        order_blocks: List[OrderBlock],
        bos_events: List[BOS],
    ):

        for ob in order_blocks:

            for bos in bos_events:

                if bos.index <= ob.candle_index:
                    continue

                if ob.side == "BULLISH":

                    if bos.direction != "BULLISH":
                        continue

                else:

                    if bos.direction != "BEARISH":
                        continue

                ob.bos_index = bos.index
                break

        return order_blocks

    # =========================================================
    # CHOCH CONFIRMATION
    # =========================================================

    def attach_choch(
        self,
        order_blocks: List[OrderBlock],
        choch_events: List[CHOCH],
    ):

        for ob in order_blocks:

            for choch in choch_events:

                if choch.index <= ob.candle_index:
                    continue

                if ob.side == "BULLISH":

                    if choch.direction != "BULLISH":
                        continue

                else:

                    if choch.direction != "BEARISH":
                        continue

                ob.choch_index = choch.index
                break

        return order_blocks

    # =========================================================
    # LIQUIDITY ATTACHMENT
    # =========================================================

    def attach_liquidity(
        self,
        order_blocks: List[OrderBlock],
        liquidity: List[LiquidityLevel],
    ):

        for ob in order_blocks:

            nearest = None
            distance = 10 ** 18

            for level in liquidity:

                if level.sweep_index is None:
                    continue

                if level.sweep_index <= ob.candle_index:
                    continue

                d = (
                    level.sweep_index
                    - ob.candle_index
                )

                if d < distance:

                    distance = d
                    nearest = level

            if nearest is not None:

                ob.liquidity_index = (
                    nearest.sweep_index
                )

        return order_blocks

    # =========================================================
    # MITIGATION
    # =========================================================

    def detect_mitigation(
        self,
        candles: List[Candle],
        order_blocks: List[OrderBlock],
    ):

        last_index = len(candles)

        for ob in order_blocks:

            end = min(
                last_index,
                ob.candle_index
                + self.MAX_MITIGATION_LOOKAHEAD,
            )

            if ob.side == "BULLISH":

                for i in range(
                    ob.impulse_index,
                    end,
                ):

                    candle = candles[i]

                    if (
                        candle.low
                        <= ob.mitigation_level
                    ):

                        ob.mitigated = True

                        ob.mitigation_index = i

                        break

            else:

                for i in range(
                    ob.impulse_index,
                    end,
                ):

                    candle = candles[i]

                    if (
                        candle.high
                        >= ob.mitigation_level
                    ):

                        ob.mitigated = True

                        ob.mitigation_index = i

                        break

        return order_blocks

    # =========================================================
    # INVALIDATION
    # =========================================================

    def detect_invalidation(
        self,
        candles: List[Candle],
        order_blocks: List[OrderBlock],
    ):

        for ob in order_blocks:

            if ob.side == "BULLISH":

                start = (
                    ob.mitigation_index
                    if ob.mitigation_index
                    else ob.impulse_index
                )

                for i in range(
                    start,
                    len(candles),
                ):

                    if (
                        candles[i].close
                        < ob.validity_level
                    ):

                        ob.invalidated = True
                        break

            else:

                start = (
                    ob.mitigation_index
                    if ob.mitigation_index
                    else ob.impulse_index
                )

                for i in range(
                    start,
                    len(candles),
                ):

                    if (
                        candles[i].close
                        > ob.validity_level
                    ):

                        ob.invalidated = True
                        break

        return order_blocks

    # =========================================================
    # BREAKER BLOCK
    # =========================================================

    def detect_breakers(
        self,
        order_blocks: List[OrderBlock],
    ):

        for ob in order_blocks:

            if (
                ob.invalidated
                and ob.mitigated
            ):

                ob.breaker = True

        return order_blocks

    # =========================================================
    # QUALITY SCORE
    # =========================================================

    def score_order_blocks(
        self,
        candles: List[Candle],
        order_blocks: List[OrderBlock],
    ):

        for ob in order_blocks:

            score = 0.0

            # -------------------------
            # BOS confirmation
            # -------------------------

            if ob.bos_index is not None:
                score += 20

            # -------------------------
            # CHOCH confirmation
            # -------------------------

            if ob.choch_index is not None:
                score += 15

            # -------------------------
            # Liquidity sweep
            # -------------------------

            if ob.liquidity_index is not None:
                score += 15

            # -------------------------
            # Fresh block
            # -------------------------

            if not ob.mitigated:
                score += 20

            # -------------------------
            # Breaker penalty
            # -------------------------

            if ob.breaker:
                score -= 20

            # -------------------------
            # Invalidated penalty
            # -------------------------

            if ob.invalidated:
                score -= 40

            # -------------------------
            # Large impulse bonus
            # -------------------------

            score += min(
                20,
                ob.impulse_size * 3,
            )

            ob.score = round(score, 2)

        return order_blocks

    # =========================================================
    # REMOVE INVALID BLOCKS
    # =========================================================

    def remove_invalid(
        self,
        order_blocks: List[OrderBlock],
    ):

        return [
            ob
            for ob in order_blocks
            if not ob.invalidated
        ]

    # =========================================================
    # REMOVE WEAK BLOCKS
    # =========================================================

    def remove_low_score(
        self,
        order_blocks: List[OrderBlock],
    ):

        return [
            ob
            for ob in order_blocks
            if ob.score >= self.MIN_SCORE
        ]

    # =========================================================
    # SORT
    # =========================================================

    def sort_blocks(
        self,
        order_blocks: List[OrderBlock],
    ):

        return sorted(
            order_blocks,
            key=lambda x: (
                x.score,
                x.impulse_size,
            ),
            reverse=True,
        )

    # =========================================================
    # LIMIT
    # =========================================================

    def top_blocks(
        self,
        order_blocks: List[OrderBlock],
    ):

        return order_blocks[: self.MAX_BLOCKS]

    # =========================================================
    # PREMIUM / DISCOUNT
    # =========================================================

    def premium_discount_filter(
        self,
        candles: List[Candle],
        order_blocks: List[OrderBlock],
    ):

        if len(candles) < 20:
            return order_blocks

        highest = max(
            c.high
            for c in candles[-150:]
        )

        lowest = min(
            c.low
            for c in candles[-150:]
        )

        equilibrium = (
            highest + lowest
        ) / 2

        filtered = []

        for ob in order_blocks:

            if ob.side == "BULLISH":

                if ob.price <= equilibrium:
                    filtered.append(ob)

            else:

                if ob.price >= equilibrium:
                    filtered.append(ob)

        return filtered

    # =========================================================
    # CLUSTERING
    # =========================================================

    def cluster_blocks(
        self,
        order_blocks: List[OrderBlock],
    ):

        if not order_blocks:
            return []

        clustered = []

        used = set()

        tolerance = 0.0025

        for i, current in enumerate(order_blocks):

            if i in used:
                continue

            cluster = [current]

            for j in range(i + 1, len(order_blocks)):

                if j in used:
                    continue

                other = order_blocks[j]

                diff = abs(
                    other.price
                    - current.price
                )

                pct = (
                    diff
                    / current.price
                )

                if pct <= tolerance:

                    cluster.append(other)
                    used.add(j)

            best = max(
                cluster,
                key=lambda x: x.score,
            )

            clustered.append(best)

        return clustered

    # =========================================================
    # PRINT
    # =========================================================

    def print_blocks(
        self,
        order_blocks: List[OrderBlock],
    ):

        print()

        print("=" * 80)
        print("ORDER BLOCKS")
        print("=" * 80)

        for ob in order_blocks:

            print(
                ob.side,
                round(ob.price, 6),
                "score",
                ob.score,
                "mitigated",
                ob.mitigated,
                "breaker",
                ob.breaker,
            )

        print("=" * 80)

    # =========================================================
    # COMPLETE DETECTOR
    # =========================================================

    def detect(
        self,
        candles: List[Candle],
        bos_events: List[BOS],
        choch_events: List[CHOCH],
        liquidity_levels: List[LiquidityLevel],
    ) -> List[OrderBlock]:

        if len(candles) < 30:
            return []

        # ---------------------------------------------------
        # 1 Raw detection
        # ---------------------------------------------------

        order_blocks = self.detect_raw_blocks(
            candles
        )

        if not order_blocks:
            return []

        # ---------------------------------------------------
        # 2 Attach BOS
        # ---------------------------------------------------

        order_blocks = self.attach_bos(
            order_blocks,
            bos_events,
        )

        # ---------------------------------------------------
        # 3 Attach CHOCH
        # ---------------------------------------------------

        order_blocks = self.attach_choch(
            order_blocks,
            choch_events,
        )

        # ---------------------------------------------------
        # 4 Attach Liquidity
        # ---------------------------------------------------

        order_blocks = self.attach_liquidity(
            order_blocks,
            liquidity_levels,
        )

        # ---------------------------------------------------
        # 5 Mitigation
        # ---------------------------------------------------

        order_blocks = self.detect_mitigation(
            candles,
            order_blocks,
        )

        # ---------------------------------------------------
        # 6 Invalidation
        # ---------------------------------------------------

        order_blocks = self.detect_invalidation(
            candles,
            order_blocks,
        )

        # ---------------------------------------------------
        # 7 Breakers
        # ---------------------------------------------------

        order_blocks = self.detect_breakers(
            order_blocks,
        )

        # ---------------------------------------------------
        # 8 Score
        # ---------------------------------------------------

        order_blocks = self.score_order_blocks(
            candles,
            order_blocks,
        )

        # ---------------------------------------------------
        # 9 Remove invalid
        # ---------------------------------------------------

        order_blocks = self.remove_invalid(
            order_blocks,
        )

        # ---------------------------------------------------
        # 10 Remove weak
        # ---------------------------------------------------

        order_blocks = self.remove_low_score(
            order_blocks,
        )

        # ---------------------------------------------------
        # 11 Premium / Discount
        # ---------------------------------------------------

        order_blocks = self.premium_discount_filter(
            candles,
            order_blocks,
        )

        # ---------------------------------------------------
        # 12 Cluster nearby blocks
        # ---------------------------------------------------

        order_blocks = self.cluster_blocks(
            order_blocks,
        )

        # ---------------------------------------------------
        # 13 Sort
        # ---------------------------------------------------

        order_blocks = self.sort_blocks(
            order_blocks,
        )

        # ---------------------------------------------------
        # 14 Limit
        # ---------------------------------------------------

        order_blocks = self.top_blocks(
            order_blocks,
        )

        return order_blocks

    # =========================================================
    # Convenience API
    # =========================================================

    def strongest(
        self,
        candles: List[Candle],
        bos_events: List[BOS],
        choch_events: List[CHOCH],
        liquidity_levels: List[LiquidityLevel],
    ):

        obs = self.detect(
            candles,
            bos_events,
            choch_events,
            liquidity_levels,
        )

        if not obs:
            return None

        return obs[0]

    # =========================================================
    # Multi Timeframe Merge
    # =========================================================

    def merge_timeframes(
        self,
        lower_tf_blocks: List[OrderBlock],
        higher_tf_blocks: List[OrderBlock],
    ):

        merged = []

        merged.extend(higher_tf_blocks)
        merged.extend(lower_tf_blocks)

        merged = self.sort_blocks(
            merged,
        )

        return self.cluster_blocks(
            merged,
        )

    # =========================================================
    # Statistics
    # =========================================================

    def statistics(
        self,
        order_blocks: List[OrderBlock],
    ):

        bullish = 0
        bearish = 0
        mitigated = 0
        breakers = 0

        for ob in order_blocks:

            if ob.side == "BULLISH":
                bullish += 1
            else:
                bearish += 1

            if ob.mitigated:
                mitigated += 1

            if ob.breaker:
                breakers += 1

        return {
            "bullish": bullish,
            "bearish": bearish,
            "mitigated": mitigated,
            "breakers": breakers,
            "total": len(order_blocks),
        }

    def detect_raw_blocks(
        self,
        candles,
    ):

        bullish = self.bullish_candidates(
            candles,
        )

        bearish = self.bearish_candidates(
            candles,
        )

        return bullish + bearish

    # =========================================================
    # Debug
    # =========================================================

    def debug(
        self,
        order_blocks: List[OrderBlock],
    ):

        print()
        print("=" * 100)
        print("ORDER BLOCK DEBUG")
        print("=" * 100)

        for ob in order_blocks:

            print(
                f"{ob.side:<8}"
                f" price={ob.price:.6f}"
                f" score={ob.score:>5}"
                f" impulse={ob.impulse_size:.2f}"
                f" mitigated={ob.mitigated}"
                f" invalidated={ob.invalidated}"
                f" breaker={ob.breaker}"
                f" bos={ob.bos_index}"
                f" choch={ob.choch_index}"
                f" liquidity={ob.liquidity_index}"
            )

        print("=" * 100)