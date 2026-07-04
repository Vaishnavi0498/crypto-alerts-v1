from dataclasses import dataclass
from typing import List

from .models import Pivot, PivotType


@dataclass
class ExternalStructure:

    pivots: List[Pivot]

    major_highs: List[Pivot]

    major_lows: List[Pivot]


class ExternalStructureDetector:

    def __init__(self, strength_multiplier: float = 1.5):

        self.multiplier = strength_multiplier

    def detect(self, pivots: List[Pivot]) -> ExternalStructure:

        if not pivots:

            return ExternalStructure(
                pivots=[],
                major_highs=[],
                major_lows=[],
            )

        strengths = [
            p.strength
            for p in pivots
        ]

        avg_strength = (
            sum(strengths) /
            len(strengths)
        )

        threshold = avg_strength * self.multiplier

        major_highs = []
        major_lows = []

        for pivot in pivots:

            if pivot.strength < threshold:
                continue

            if pivot.type == PivotType.HIGH:
                major_highs.append(pivot)

            else:
                major_lows.append(pivot)

        return ExternalStructure(
            pivots=pivots,
            major_highs=major_highs,
            major_lows=major_lows,
        )