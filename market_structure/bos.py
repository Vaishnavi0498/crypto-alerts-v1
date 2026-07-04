from dataclasses import dataclass
from typing import List

from .models import Candle
from .models import Pivot
from .models import StructureState


@dataclass
class BOS:

    direction: str

    price: float

    index: int

    pivot: Pivot


class BOSDetector:

    def detect(
        self,
        candles: List[Candle],
        pivots: List[Pivot],
    ) -> List[BOS]:

        state = StructureState()

        events = []

        for pivot in pivots:

            # --------------------------
            # Update current swings
            # --------------------------

            if pivot.kind == "HIGH":

                state.last_high = pivot

                if state.protected_high is None:

                    state.protected_high = pivot

            else:

                state.last_low = pivot

                if state.protected_low is None:

                    state.protected_low = pivot

            # --------------------------
            # Look forward only until
            # next pivot
            # --------------------------

            start = pivot.index + 1

            end = len(candles)

            if start >= end:

                continue

            # --------------------------
            # Bull BOS
            # --------------------------

            if (

                state.protected_high

                and

                pivot == state.protected_high

            ):

                for i in range(start, end):

                    if candles[i].close > pivot.price:

                        events.append(

                            BOS(

                                direction="BULLISH",

                                price=pivot.price,

                                index=i,

                                pivot=pivot,

                            )

                        )

                        state.trend = "BULLISH"

                        state.protected_high = None

                        break

            # --------------------------
            # Bear BOS
            # --------------------------

            if (

                state.protected_low

                and

                pivot == state.protected_low

            ):

                for i in range(start, end):

                    if candles[i].close < pivot.price:

                        events.append(

                            BOS(

                                direction="BEARISH",

                                price=pivot.price,

                                index=i,

                                pivot=pivot,

                            )

                        )

                        state.trend = "BEARISH"

                        state.protected_low = None

                        break

        return events