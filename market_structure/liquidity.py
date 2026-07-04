from dataclasses import dataclass
from typing import List

from .models import Pivot


@dataclass
class LiquidityLevel:
    price: float
    start_index: int
    end_index: int
    touches: int
    side: str              # buy_side / sell_side
    swept: bool = False
    sweep_index: int = -1
    sweep_price: float = 0.0


class LiquidityDetector:
#below 1 line for testing purpose only, change to 0.0015
    PRICE_TOLERANCE = 0.003

    MIN_TOUCHES = 2

    MIN_BODY_PERCENT = 0.50

    def detect(
        self,
        pivots: List[Pivot],
        candles
    ) -> List[LiquidityLevel]:

        buy_side = self._find_equal_highs(
            pivots,
            candles
        )

        sell_side = self._find_equal_lows(
            pivots,
            candles
        )

        levels = buy_side + sell_side

        self._detect_sweeps(
            levels,
            candles
        )

        return levels

    # ---------------------------------------------------------

    def _find_equal_highs(
        self,
        pivots,
        candles
    ):

        highs = [
            p
            for p in pivots
            if p.kind == "HIGH"
        ]

        levels = []

        used = set()

        for i in range(len(highs)):

            if i in used:
                continue

            group = [highs[i]]

            used.add(i)

            for j in range(i + 1, len(highs)):

                if j in used:
                    continue

                diff = abs(
                    highs[i].price -
                    highs[j].price
                )

                if (
                    diff /
                    highs[i].price
                    <= self.PRICE_TOLERANCE
                ):

                    group.append(
                        highs[j]
                    )

                    used.add(j)

            if len(group) >= self.MIN_TOUCHES:

                price = (
                    sum(
                        p.price
                        for p in group
                    )
                    /
                    len(group)
                )

                levels.append(
                    LiquidityLevel(
                        price=price,
                        start_index=min(
                            p.index
                            for p in group
                        ),
                        end_index=max(
                            p.index
                            for p in group
                        ),
                        touches=len(group),
                        side="buy_side",
                    )
                )

        return levels

    # ---------------------------------------------------------

    def _find_equal_lows(
        self,
        pivots,
        candles
    ):

        lows = [
            p
            for p in pivots
            if p.kind == "LOW"
        ]

        levels = []

        used = set()

        for i in range(len(lows)):

            if i in used:
                continue

            group = [lows[i]]

            used.add(i)

            for j in range(i + 1, len(lows)):

                if j in used:
                    continue

                diff = abs(
                    lows[i].price -
                    lows[j].price
                )

                if (
                    diff /
                    lows[i].price
                    <= self.PRICE_TOLERANCE
                ):

                    group.append(
                        lows[j]
                    )

                    used.add(j)

            if len(group) >= self.MIN_TOUCHES:

                price = (
                    sum(
                        p.price
                        for p in group
                    )
                    /
                    len(group)
                )

                levels.append(
                    LiquidityLevel(
                        price=price,
                        start_index=min(
                            p.index
                            for p in group
                        ),
                        end_index=max(
                            p.index
                            for p in group
                        ),
                        touches=len(group),
                        side="sell_side",
                    )
                )

        return levels

    # ---------------------------------------------------------

    def _detect_sweeps(
        self,
        levels,
        candles
    ):

        for level in levels:

            for i in range(
                level.end_index + 1,
                len(candles)
            ):

                candle = candles[i]

                high = (
                    candle.high
                    if hasattr(candle, "high")
                    else candle["high"]
                )

                low = (
                    candle.low
                    if hasattr(candle, "low")
                    else candle["low"]
                )

                close = (
                    candle.close
                    if hasattr(candle, "close")
                    else candle["close"]
                )

                if level.side == "buy_side":

                    if (
                        high > level.price
                        and close < level.price
                    ):

                        level.swept = True
                        level.sweep_index = i
                        level.sweep_price = high
                        break

                else:

                    if (
                        low < level.price
                        and close > level.price
                    ):

                        level.swept = True
                        level.sweep_index = i
                        level.sweep_price = low
                        break

        # Determine whether sweep has displacement
        # ----------------------------------------

        for level in levels:

            if not level.swept:
                continue

            idx = level.sweep_index

            if idx is None:
                continue

            if idx >= len(candles) - 2:
                continue

            sweep_candle = candles[idx]

            body = abs(
                sweep_candle.close
                - sweep_candle.open
            )

            rng = (
                sweep_candle.high
                - sweep_candle.low
            )

            if rng <= 0:
                continue

            body_pct = body / rng

            displacement = False

            # -------------------------------------------------
            # Bullish displacement after bearish liquidity sweep
            # -------------------------------------------------

            if level.side == "LOW":

                if (
                    sweep_candle.close
                    > sweep_candle.open
                    and body_pct
                    >= self.MIN_BODY_PERCENT
                ):
                    displacement = True

            # -------------------------------------------------
            # Bearish displacement after bullish liquidity sweep
            # -------------------------------------------------

            else:

                if (
                    sweep_candle.close
                    < sweep_candle.open
                    and body_pct
                    >= self.MIN_BODY_PERCENT
                ):
                    displacement = True

            level.displacement = displacement

        return levels

    # --------------------------------------------------------
    # Return only valid liquidity grabs
    # --------------------------------------------------------

    def confirmed_sweeps(
        self,
        candles,
        levels,
    ):

        confirmed = []

        for level in levels:

            if not level.swept:
                continue

            if not level.displacement:
                continue

            confirmed.append(level)

        return confirmed

    # --------------------------------------------------------
    # Most recent sweep
    # --------------------------------------------------------

    def latest_sweep(
        self,
        candles,
        levels,
    ):

        confirmed = self.confirmed_sweeps(
            candles,
            levels,
        )

        if not confirmed:
            return None

        confirmed.sort(
            key=lambda x: x.sweep_index
        )

        return confirmed[-1]

    # --------------------------------------------------------
    # Remove old sweeps
    # --------------------------------------------------------

    def active_sweeps(
        self,
        candles,
        levels,
    ):

        latest_index = len(candles) - 1

        active = []

        for level in self.confirmed_sweeps(
            candles,
            levels,
        ):

            if (
                latest_index
                - level.sweep_index
                <= self.max_age
            ):

                active.append(level)

        return active

    # --------------------------------------------------------
    # Is liquidity currently bullish?
    # --------------------------------------------------------

    def bullish_liquidity(
        self,
        candles,
        levels,
    ):

        sweep = self.latest_sweep(
            candles,
            levels,
        )

        if sweep is None:
            return False

        return sweep.side == "LOW"

    # --------------------------------------------------------
    # Is liquidity currently bearish?
    # --------------------------------------------------------

    def bearish_liquidity(
        self,
        candles,
        levels,
    ):

        sweep = self.latest_sweep(
            candles,
            levels,
        )

        if sweep is None:
            return False

        return sweep.side == "HIGH"

    # --------------------------------------------------------
    # Debug helper
    # --------------------------------------------------------

    def print_levels(
        self,
        levels,
    ):

        print("\nLiquidity Levels")

        for level in levels:

            print(
                level.side,
                round(level.price, 6),
                "swept:",
                level.swept,
                "disp:",
                level.displacement,
            )

    # --------------------------------------------------------
    # Debug helper
    # --------------------------------------------------------

    def print_confirmed(
        self,
        candles,
        levels,
    ):

        print("\nConfirmed Sweeps")

        for level in self.confirmed_sweeps(
            candles,
            levels,
        ):

            print(
                level.side,
                round(level.price, 6),
                level.sweep_index,
            )

    # ------------------------------------------------------------
    # Equal Highs / Equal Lows
    # ------------------------------------------------------------

    def equal_highs(
        self,
        levels,
        tolerance=0.0005,
    ):

        result = []

        highs = [
            x for x in levels
            if x.side == "HIGH"
        ]

        highs.sort(
            key=lambda x: x.price
        )

        for i in range(len(highs) - 1):

            if (
                abs(
                    highs[i].price
                    - highs[i + 1].price
                )
                / highs[i].price
                <= tolerance
            ):

                result.append(
                    (
                        highs[i],
                        highs[i + 1],
                    )
                )

        return result

    def equal_lows(
        self,
        levels,
        tolerance=0.0005,
    ):

        result = []

        lows = [
            x for x in levels
            if x.side == "LOW"
        ]

        lows.sort(
            key=lambda x: x.price
        )

        for i in range(len(lows) - 1):

            if (
                abs(
                    lows[i].price
                    - lows[i + 1].price
                )
                / lows[i].price
                <= tolerance
            ):

                result.append(
                    (
                        lows[i],
                        lows[i + 1],
                    )
                )

        return result

    # ------------------------------------------------------------
    # Liquidity Density
    # ------------------------------------------------------------

    def liquidity_density(
        self,
        levels,
        tolerance=0.001,
    ):

        density = {}

        for level in levels:

            found = False

            for key in density.keys():

                if (
                    abs(key - level.price)
                    / key
                    <= tolerance
                ):

                    density[key].append(level)
                    found = True
                    break

            if not found:

                density[level.price] = [level]

        return density

    # ------------------------------------------------------------
    # Score every liquidity level
    # ------------------------------------------------------------

    def score_levels(
        self,
        levels,
    ):

        for level in levels:

            score = 0

            if level.swept:
                score += 3

            if level.displacement:
                score += 5

            if level.side == "HIGH":
                score += 1

            if level.side == "LOW":
                score += 1

            level.score = score

        return levels

    # ------------------------------------------------------------
    # Best liquidity level
    # ------------------------------------------------------------

    def strongest_level(
        self,
        levels,
    ):

        if not levels:
            return None

        levels = self.score_levels(levels)

        levels.sort(
            key=lambda x: x.score,
            reverse=True,
        )

        return levels[0]

    # ------------------------------------------------------------
    # Premium / Discount
    # ------------------------------------------------------------

    def premium_discount(
        self,
        swing_low,
        swing_high,
        current_price,
    ):

        midpoint = (
            swing_high
            + swing_low
        ) / 2

        if current_price > midpoint:
            return "PREMIUM"

        return "DISCOUNT"

    # ------------------------------------------------------------
    # Inducement
    # ------------------------------------------------------------

    def inducement_present(
        self,
        candles,
        levels,
    ):

        sweep = self.latest_sweep(
            candles,
            levels,
        )

        if sweep is None:
            return False

        idx = sweep.sweep_index

        if idx < 3:
            return False

        previous = candles[idx - 3:idx]

        highest = max(
            x.high
            for x in previous
        )

        lowest = min(
            x.low
            for x in previous
        )

        candle = candles[idx]

        if sweep.side == "HIGH":

            return (
                candle.high > highest
            )

        return (
            candle.low < lowest
        )

    # ------------------------------------------------------------
    # Final Institutional Filter
    # ------------------------------------------------------------

    def institutional_liquidity(
        self,
        candles,
        levels,
    ):

        sweep = self.latest_sweep(
            candles,
            levels,
        )

        if sweep is None:
            return None

        if not sweep.displacement:
            return None

        if not self.inducement_present(
            candles,
            levels,
        ):
            return None

        return sweep

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def analyze(
        self,
        candles,
        levels,
    ):

        levels = self.detect_sweeps(
            candles,
            levels,
        )

        strongest = self.institutional_liquidity(
            candles,
            levels,
        )

        return {
            "levels": levels,
            "equal_highs": self.equal_highs(levels),
            "equal_lows": self.equal_lows(levels),
            "strongest": strongest,
            "bullish": self.bullish_liquidity(
                candles,
                levels,
            ),
            "bearish": self.bearish_liquidity(
                candles,
                levels,
            ),
        }