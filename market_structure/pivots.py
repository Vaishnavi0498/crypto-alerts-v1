from market_structure.models import Pivot


class PivotDetector:

    def __init__(
        self,
        left=3,
        right=3,
        min_move_percent=0.20,
        min_separation=2,
    ):
        self.left = left
        self.right = right

        # Minimum percentage movement required
        self.min_move_percent = min_move_percent

        # Prevent pivots from appearing immediately next to each other
        self.min_separation = min_separation

    # --------------------------------------------------------

    def detect(
        self,
        candles,
    ):

        raw = []

        # ---------------------------------------------
        # Find local highs/lows
        # ---------------------------------------------

        for i in range(
            self.left,
            len(candles) - self.right,
        ):

            current = candles[i]

            is_high = True

            is_low = True

            # -----------------------------
            # Check window
            # -----------------------------

            for j in range(
                i - self.left,
                i + self.right + 1,
            ):

                if j == i:
                    continue

                if candles[j].high >= current.high:
                    is_high = False

                if candles[j].low <= current.low:
                    is_low = False

                if not is_high and not is_low:
                    break

            if is_high:

                raw.append(

                    Pivot(

                        index=i,

                        price=current.high,

                        kind="HIGH",

                        candle=current,

                    )

                )

            elif is_low:

                raw.append(

                    Pivot(

                        index=i,

                        price=current.low,

                        kind="LOW",

                        candle=current,

                    )

                )

        # ---------------------------------------------
        # Remove duplicate consecutive highs/lows
        # ---------------------------------------------

        filtered = []

        for pivot in raw:

            if not filtered:

                filtered.append(pivot)

                continue

            previous = filtered[-1]

            # ----------------------------------------
            # Same pivot type
            # ----------------------------------------

            if previous.kind == pivot.kind:

                # Keep stronger one

                if pivot.kind == "HIGH":

                    if pivot.price > previous.price:

                        filtered[-1] = pivot

                else:

                    if pivot.price < previous.price:

                        filtered[-1] = pivot

                continue

            filtered.append(pivot)

        # ---------------------------------------------
        # Remove insignificant swings
        # ---------------------------------------------

        cleaned = []

        for pivot in filtered:

            if not cleaned:

                cleaned.append(pivot)

                continue

            previous = cleaned[-1]

            # distance

            if (

                pivot.index - previous.index

                < self.min_separation

            ):

                continue

            move = abs(

                pivot.price - previous.price

            )

            pct = (

                move / previous.price

            ) * 100

            if pct < self.min_move_percent:

                continue

            cleaned.append(pivot)

        return cleaned