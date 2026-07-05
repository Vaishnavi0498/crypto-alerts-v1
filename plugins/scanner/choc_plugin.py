from plugins.scanner.base_plugin import BasePlugin
from datetime import datetime, timezone

from market_structure.models import Candle
from market_structure.structure_engine import StructureEngine


class ChoCHPlugin(BasePlugin):

    ALERT_TYPE = "CHOCH_15M"

    LOOKBACK = 300

    VOLUME_PERIOD = 20
    VOLUME_MULTIPLIER = 2.0

    MIN_BODY_RATIO = 0.60

    ATR_PERIOD = 14
    MIN_ATR_BREAK = 0.25

    def __init__(self):

        self.engine = StructureEngine(
            left=3,
            right=3,
        )

    def process(
        self,
        symbol,
        candles,
    ):

        if len(candles) < self.LOOKBACK:
            return []

        completed = candles[:-1]

        if len(completed) < self.VOLUME_PERIOD + 2:
            return []

        structure_candles = self._to_candles(
            completed,
        )

        result = self.engine.detect(
            structure_candles,
        )

        if not result["choch"]:
            return []

        latest_event = result["choch"][-1]
        latest_index = len(structure_candles) - 1

        last_closed = structure_candles[-1]

        break_candle = structure_candles[latest_event.break_index]

        if break_candle.close_time != structure_candles[-1].close_time:
            return []

        metrics = self._filter_metrics(
            structure_candles,
            latest_event,
        )

        if not metrics["valid"]:
            return []

        latest_candle = structure_candles[latest_index]
        candle_time = latest_candle.close_time

        if self.already_triggered(
            symbol,
            candle_time,
        ):
            return []

        self.mark_triggered(
            symbol,
            candle_time,
        )

        return [
            {
                "symbol": symbol,
                "price": latest_candle.close,
                "notes": self.build_notes(
                    symbol,
                    result,
                    latest_event,
                    metrics,
                    structure_candles,
                ),
                "type": "choch",
            }
        ]

    # =====================================================
    # INPUT NORMALIZATION
    # =====================================================

    def _to_candles(
        self,
        candles,
    ):

        converted = []

        for candle in candles:

            if isinstance(candle, Candle):
                converted.append(candle)
                continue

            converted.append(
                Candle(
                    open_time=int(candle["open_time"]),
                    close_time=int(candle["close_time"]),
                    open=float(candle["open"]),
                    high=float(candle["high"]),
                    low=float(candle["low"]),
                    close=float(candle["close"]),
                    volume=float(candle["volume"]),
                )
            )

        return converted

    # =====================================================
    # FILTERS
    # =====================================================

    def _filter_metrics(
        self,
        candles,
        event,
    ):

        index = event.break_index
        candle = candles[index]

        body = abs(
            candle.close - candle.open
        )

        candle_range = candle.high - candle.low

        body_ratio = (
            body / candle_range
            if candle_range > 0
            else 0
        )

        avg_volume = self._average_volume(
            candles,
            index,
        )

        volume_ratio = (
            candle.volume / avg_volume
            if avg_volume
            else 0
        )

        atr = self._atr(
            candles,
            index,
        )

        break_distance = abs(
            candle.close - event.pivot.price
        )

        min_break_distance = (
            atr * self.MIN_ATR_BREAK
            if atr
            else 0
        )

        passed = []
        failed = []

        self._record_filter(
            body_ratio >= self.MIN_BODY_RATIO,
            "Body >= 60%",
            passed,
            failed,
        )

        self._record_filter(
            volume_ratio > self.VOLUME_MULTIPLIER,
            "Volume > 2x 20-candle average",
            passed,
            failed,
        )

        self._record_filter(
            atr is not None
            and break_distance > min_break_distance,
            "Break distance > 0.25 ATR(14)",
            passed,
            failed,
        )

        return {
            "valid": not failed,
            "passed": passed,
            "failed": failed,
            "body_ratio": body_ratio,
            "volume_ratio": volume_ratio,
            "atr": atr,
            "break_distance": break_distance,
            "min_break_distance": min_break_distance,
        }

    def _record_filter(
        self,
        condition,
        label,
        passed,
        failed,
    ):

        if condition:
            passed.append(label)
        else:
            failed.append(label)

    def _average_volume(
        self,
        candles,
        index,
    ):

        if index < self.VOLUME_PERIOD:
            return None

        values = [
            candle.volume
            for candle in candles[
                index - self.VOLUME_PERIOD:index
            ]
        ]

        if not values:
            return None

        return sum(values) / len(values)

    def _atr(
        self,
        candles,
        index,
    ):

        if index < self.ATR_PERIOD:
            return None

        true_ranges = []

        for i in range(
            index - self.ATR_PERIOD + 1,
            index + 1,
        ):

            candle = candles[i]
            previous = candles[i - 1]

            true_ranges.append(
                max(
                    candle.high - candle.low,
                    abs(candle.high - previous.close),
                    abs(candle.low - previous.close),
                )
            )

        return sum(true_ranges) / len(true_ranges)

    # =====================================================
    # ALERT MESSAGE
    # =====================================================

    def build_notes(
        self,
        symbol,
        result,
        event,
        metrics,
        candles,
    ):

        direction = event.direction
        swing = event.pivot
        state = result["state"]

        break_candle = candles[event.break_index]
        break_time = datetime.fromtimestamp(
            break_candle.close_time / 1000,
            tz=timezone.utc,
        ).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            "🚨 Smart Money CHOCH",
            "",
            f"Symbol: {symbol}",
            "Timeframe: 15m",
            f"Direction: {direction}",
            f"Trend Before Break: {state.trend}",
            "",
            "Structure Break",
            f"Break Candle: {break_time}",
            f"Pivot Index: {swing.index}",
            f"Break Index: {event.break_index}",
            "",
            f"Broken Swing: {swing.label} ({swing.kind})",
            f"Swing Price: {swing.price:.2f}",
            f"Break Close: {event.break_price:.2f}",
            f"Break Distance: {metrics['break_distance']:.2f}",
            "",
            "Filters",
            f"Body Ratio: {metrics['body_ratio'] * 100:.1f}%",
            f"Volume: {metrics['volume_ratio']:.2f}× Avg",
        ]

        if metrics["atr"] is not None:
            lines.extend([
                f"ATR(14): {metrics['atr']:.2f}",
                f"Minimum Break: {metrics['min_break_distance']:.2f}",
            ])

        lines.append("")
        lines.append("✅ Passed Filters")

        for reason in metrics["passed"]:
            lines.append(f"• {reason}")

        if metrics["failed"]:
            lines.append("")
            lines.append("❌ Failed Filters")
            for reason in metrics["failed"]:
                lines.append(f"• {reason}")

        lines.extend([
            "",
            "Generated by Smart Money Structure Engine",
        ])

        return "\n".join(lines)
