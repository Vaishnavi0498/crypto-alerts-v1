from dataclasses import dataclass
from typing import List

from .bos import BOS
from .models import Candle
from .models import Pivot


@dataclass
class CHOCH:

    direction: str

    broken_level: float

    index: int

    confidence: float = 0.0


class ChoCHDetector:

    def detect(
        self,
        candles: List[Candle],
        pivots: List[Pivot],
        bos_events: List[BOS],
    ) -> List[CHOCH]:

        choch_events = []

        if len(bos_events) < 2:

            return choch_events

        previous = bos_events[0]

        for current in bos_events[1:]:

            if current.direction != previous.direction:

                confidence = 50.0

                confidence += 25

                if abs(

                    current.price -

                    previous.price

                ) > 0:

                    confidence += 10

                choch_events.append(

                    CHOCH(

                        direction=current.direction,

                        broken_level=current.price,

                        index=current.index,

                        confidence=min(

                            confidence,

                            100,

                        ),

                    )

                )

            previous = current

        return choch_events