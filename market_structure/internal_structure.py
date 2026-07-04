from dataclasses import dataclass
from dataclasses import field


@dataclass
class StructurePoint:

    label: str

    pivot: object


@dataclass
class InternalStructureEvent:

    type: str

    direction: str

    pivot: object

    break_index: int

    break_price: float

    @property
    def index(self):

        return self.break_index

    @property
    def price(self):

        return self.break_price


@dataclass
class InternalStructureResult:

    trend: str = "UNKNOWN"

    points: list = field(default_factory=list)

    bos: list = field(default_factory=list)

    choch: list = field(default_factory=list)

    protected_high: object | None = None

    protected_low: object | None = None


class InternalStructureDetector:

    def detect(
        self,
        pivots,
        candles=None,
        external_trend="UNKNOWN",
    ):

        points = self._label_points(
            pivots,
        )

        result = InternalStructureResult(
            trend=external_trend,
            points=points,
        )

        if candles is None:
            return result

        self._detect_events(
            result,
            pivots,
            candles,
            external_trend,
        )

        return result

    def _label_points(
        self,
        pivots,
    ):

        structure = []

        previous_high = None
        previous_low = None

        for pivot in pivots:

            if pivot.kind == "HIGH":

                if previous_high is None:
                    label = "H?"

                elif pivot.price > previous_high:
                    label = "HH"

                else:
                    label = "LH"

                previous_high = pivot.price

            else:

                if previous_low is None:
                    label = "L?"

                elif pivot.price > previous_low:
                    label = "HL"

                else:
                    label = "LL"

                previous_low = pivot.price

            structure.append(
                StructurePoint(
                    label,
                    pivot,
                )
            )

        return structure

    def _detect_events(
        self,
        result,
        pivots,
        candles,
        external_trend,
    ):

        active_high = None
        active_low = None
        trend = self._normalise_trend(
            external_trend,
        )
        last_break_key = None

        previous_index = 0

        for pivot in pivots:

            for index in range(
                previous_index,
                pivot.index + 1,
            ):

                event = self._detect_break(
                    candles[index],
                    index,
                    active_high,
                    active_low,
                    trend,
                    last_break_key,
                )

                if event is None:
                    continue

                event_type, direction, broken_pivot = event
                last_break_key = (
                    broken_pivot.kind,
                    broken_pivot.index,
                    event_type,
                )

                structure_event = InternalStructureEvent(
                    type=event_type,
                    direction=direction,
                    pivot=broken_pivot,
                    break_index=index,
                    break_price=candles[index].close,
                )

                if event_type == "BOS":
                    result.bos.append(
                        structure_event,
                    )
                    trend = direction

                else:
                    result.choch.append(
                        structure_event,
                    )

            if pivot.kind == "HIGH":
                active_high = pivot

            else:
                active_low = pivot

            previous_index = pivot.index + 1

        result.trend = trend
        result.protected_high = active_high
        result.protected_low = active_low

    def _detect_break(
        self,
        candle,
        index,
        active_high,
        active_low,
        trend,
        last_break_key,
    ):

        if (
            active_high is not None
            and candle.close > active_high.price
        ):

            key = (
                active_high.kind,
                active_high.index,
                self._event_type_for_break(
                    trend,
                    "BULLISH",
                ),
            )

            if key == last_break_key:
                return None

            return (
                key[2],
                "BULLISH",
                active_high,
            )

        if (
            active_low is not None
            and candle.close < active_low.price
        ):

            key = (
                active_low.kind,
                active_low.index,
                self._event_type_for_break(
                    trend,
                    "BEARISH",
                ),
            )

            if key == last_break_key:
                return None

            return (
                key[2],
                "BEARISH",
                active_low,
            )

        return None

    def _event_type_for_break(
        self,
        trend,
        direction,
    ):

        if trend == "UNKNOWN":
            return "BOS"

        if trend == direction:
            return "BOS"

        return "CHOCH"

    def _normalise_trend(
        self,
        trend,
    ):

        if trend in (
            "BULLISH",
            "BEARISH",
        ):
            return trend

        return "UNKNOWN"
