import logging

from market_structure.models import (
    ExternalLeg,
    Pivot,
    Swing,
    StructureEvent,
    StructureState,
)


_UNSET = object()

logger = logging.getLogger(__name__)


class StructureEngine:

    def __init__(self, left=3, right=3):

        self.left = left
        self.right = right

        self.state = StructureState()

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def detect(self, candles):

        self.state = StructureState()

        pivots = self._detect_pivots(candles)

        swings = self._classify_swings(pivots)

        self._build_external_structure(
            candles,
            swings,
        )

        return {

            "pivots": pivots,

            "swings": swings,

            "events": self.state.bos_events
            + self.state.choch_events,

            "bos": self.state.bos_events,

            "choch": self.state.choch_events,

            "state": self.state,

        }

    # ==========================================================
    # PIVOTS
    # ==========================================================

    def _detect_pivots(self, candles):

        pivots = []

        for i in range(
            self.left,
            len(candles) - self.right,
        ):

            current = candles[i]

            # -------------------
            # HIGH
            # -------------------

            high = True

            for j in range(
                i - self.left,
                i + self.right + 1,
            ):

                if j == i:
                    continue

                if candles[j].high >= current.high:

                    high = False

                    break

            if high:

                pivots.append(

                    Pivot(

                        index=i,

                        price=current.high,

                        kind="HIGH",

                        candle=current,

                    )

                )

            # -------------------
            # LOW
            # -------------------

            low = True

            for j in range(
                i - self.left,
                i + self.right + 1,
            ):

                if j == i:
                    continue

                if candles[j].low <= current.low:

                    low = False

                    break

            if low:

                pivots.append(

                    Pivot(

                        index=i,

                        price=current.low,

                        kind="LOW",

                        candle=current,

                    )

                )

        pivots.sort(

            key=lambda x: x.index

        )

        return pivots

    # ==========================================================
    # SWING CLASSIFICATION
    # ==========================================================

    def _classify_swings(
        self,
        pivots,
    ):

        swings = []

        previous_high = None
        previous_low = None

        high_history = []
        low_history = []

        for pivot in pivots:

            # ----------------------------------
            # HIGH
            # ----------------------------------

            if pivot.kind == "HIGH":

                if previous_high is None:

                    label = "HH"

                elif pivot.price > previous_high.price:

                    label = "HH"

                else:

                    label = "LH"

                pivot.label = label

                previous_high = pivot

                high_history.append(pivot)

            # ----------------------------------
            # LOW
            # ----------------------------------

            else:

                if previous_low is None:

                    label = "LL"

                elif pivot.price > previous_low.price:

                    label = "HL"

                else:

                    label = "LL"

                pivot.label = label

                previous_low = pivot

                low_history.append(pivot)

            swings.append(

                Swing(

                    pivot=pivot,

                    label=label,

                )

            )

        # ------------------------------------------------
        # INITIAL TREND
        # ------------------------------------------------

        if (

            len(high_history) >= 2

            and

            len(low_history) >= 2

        ):

            if (

                high_history[-1].price > high_history[-2].price

                and

                low_history[-1].price > low_history[-2].price

            ):

                self.state.trend = "BULLISH"

            elif (

                high_history[-1].price < high_history[-2].price

                and

                low_history[-1].price < low_history[-2].price

            ):

                self.state.trend = "BEARISH"

            else:

                self.state.trend = "RANGE"

        else:

            self.state.trend = "UNKNOWN"

        return swings

    # ==========================================================
    # EXTERNAL STRUCTURE
    # ==========================================================

    def _build_external_structure(
        self,
        candles,
        swings,
    ):

        pivots = [
            swing.pivot
            for swing in swings
        ]

        context = self._create_external_context(
            pivots,
        )

        if context is None:
            return

        self._publish_external_context(
            context,
        )

        start_position = self._pivot_position(
            pivots,
            context["end_pivot"],
        ) + 1

        previous_index = context["end_pivot"].index

        for pivot in pivots[start_position:]:

            self._scan_external_breaks(
                candles=candles,
                context=context,
                start_index=previous_index + 1,
                end_index=pivot.index,
            )

            self._absorb_external_pivot(
                context,
                pivot,
            )

            self._publish_external_context(
                context,
            )

            previous_index = pivot.index

        self._scan_external_breaks(
            candles=candles,
            context=context,
            start_index=previous_index + 1,
            end_index=len(candles) - 1,
        )

        self._publish_external_context(
            context,
        )

    def _bos_target(
        self,
        context,
    ):

        direction = (
            context["candidate_direction"]
            or context["trend"]
        )

        if direction == "BULLISH":
            return context["last_confirmed_HH"]

        if direction == "BEARISH":
            return context["last_confirmed_LL"]

        return None

    def _choch_target(
        self,
        context,
    ):

        direction = (
            context["candidate_direction"]
            or context["trend"]
        )

        if direction == "BULLISH":
            return context["last_confirmed_HL"]

        if direction == "BEARISH":
            return context["last_confirmed_LH"]

        return None

    def _protected_high(
        self,
        context,
    ):

        if context["candidate_direction"] == "BEARISH":
            return self._active_pivot(
                context["last_confirmed_LH"],
            )

        if (
            context["candidate_direction"] is None
            and context["trend"] == "BEARISH"
        ):
            return self._active_pivot(
                context["last_confirmed_LH"],
            )

        return None

    def _protected_low(
        self,
        context,
    ):

        if context["candidate_direction"] == "BULLISH":
            return self._active_pivot(
                context["last_confirmed_HL"],
            )

        if (
            context["candidate_direction"] is None
            and context["trend"] == "BULLISH"
        ):
            return self._active_pivot(
                context["last_confirmed_HL"],
            )

        return None

    def _active_pivot(
        self,
        pivot,
    ):

        if (
            pivot is None
            or pivot.broken
        ):
            return None

        return pivot

    def _pivot_index(
        self,
        pivot,
    ):

        if pivot is None:
            return None

        return pivot.index

    def _context_snapshot(
        self,
        context,
    ):

        pivots = []

        for key in (
            "last_confirmed_HH",
            "last_confirmed_HL",
            "last_confirmed_LL",
            "last_confirmed_LH",
        ):

            pivot = context[key]

            if (
                pivot is not None
                and pivot not in pivots
            ):
                pivots.append(
                    pivot,
                )

        pivot_flags = [
            (
                pivot,
                pivot.broken,
                pivot.protected,
            )
            for pivot in pivots
        ]

        return {
            "trend": context["trend"],
            "phase": context["phase"],
            "last_confirmed_HH": context["last_confirmed_HH"],
            "last_confirmed_HL": context["last_confirmed_HL"],
            "last_confirmed_LL": context["last_confirmed_LL"],
            "last_confirmed_LH": context["last_confirmed_LH"],
            "candidate_direction": context["candidate_direction"],
            "bos_count": len(
                self.state.bos_events,
            ),
            "choch_count": len(
                self.state.choch_events,
            ),
            "last_bos_direction": self.state.last_bos_direction,
            "state_trend": self.state.trend,
            "pivot_flags": pivot_flags,
            "protected_high": self.state.protected_high,
            "protected_low": self.state.protected_low,
            "current_leg": self.state.current_leg,
        }

    def _restore_context_snapshot(
        self,
        context,
        snapshot,
    ):
        print("\n==============================")
        print("RESTORE SNAPSHOT")
        print("==============================")

        print("Snapshot Trend :", snapshot["trend"])
        print("Snapshot Phase :", snapshot["phase"])

        print("Snapshot HH :", self._pivot_index(snapshot["last_confirmed_HH"]))
        print("Snapshot HL :", self._pivot_index(snapshot["last_confirmed_HL"]))
        print("Snapshot LH :", self._pivot_index(snapshot["last_confirmed_LH"]))
        print("Snapshot LL :", self._pivot_index(snapshot["last_confirmed_LL"]))

        for pivot, broken, protected in snapshot["pivot_flags"]:
            if pivot.broken and not broken:
                print(
                    f"BROKEN RESET -> idx={pivot.index} "
                    f"kind={pivot.kind}"
                )
            pivot.broken = broken
            pivot.protected = protected

        del self.state.bos_events[
            snapshot["bos_count"]:
        ]
        del self.state.choch_events[
            snapshot["choch_count"]:
        ]

        self.state.last_bos_direction = (
            snapshot["last_bos_direction"]
        )
        self.state.trend = snapshot["state_trend"]
        self.state.protected_high = snapshot["protected_high"]
        self.state.protected_low = snapshot["protected_low"]
        self.state.current_leg = snapshot["current_leg"]

        context.update(
            {
                "trend": snapshot["trend"],
                "phase": snapshot["phase"],
                "last_confirmed_HH": snapshot["last_confirmed_HH"],
                "last_confirmed_HL": snapshot["last_confirmed_HL"],
                "last_confirmed_LL": snapshot["last_confirmed_LL"],
                "last_confirmed_LH": snapshot["last_confirmed_LH"],
                "candidate_direction": snapshot["candidate_direction"],
                "reversal_snapshot": None,
            }
        )
        print(
            "CHOCH TARGET AFTER RESTORE :",
            self._pivot_index(
                self._choch_target(context)
            ),
        )

        print(
            "BOS TARGET AFTER RESTORE :",
            self._pivot_index(
                self._bos_target(context)
            ),
        )

        logger.debug(
            "[RESTORE] trend=%s phase=%s BOS=%d CHOCH=%d",
            context["trend"],
            context["phase"],
            len(self.state.bos_events),
            len(self.state.choch_events),
        )

    def _validate_context(
        self,
        context,
    ):

        trend = context["trend"]
        phase = context["phase"]
        candidate = context["candidate_direction"]

        valid_phases = {
            "WAITING_BOS",
            "WAITING_PULLBACK",
            "WAITING_CONTINUATION",
            "WAITING_REVERSAL_PULLBACK",
            "WAITING_REVERSAL_CONTINUATION",
            "WAITING_REVERSAL_CONFIRMATION",
        }

        if phase not in valid_phases:
            raise ValueError(
                f"Invalid external phase: {phase}"
            )

        if trend not in (
            "BULLISH",
            "BEARISH",
        ):
            raise ValueError(
                f"Invalid external trend: {trend}"
            )

        if candidate not in (
            None,
            "BULLISH",
            "BEARISH",
        ):
            raise ValueError(
                f"Invalid candidate direction: {candidate}"
            )

        if (
            phase.startswith("WAITING_REVERSAL")
            and candidate is None
        ):
            raise ValueError(
                f"{phase} requires candidate_direction"
            )

        if (
            not phase.startswith("WAITING_REVERSAL")
            and candidate is not None
        ):
            raise ValueError(
                f"{phase} cannot have candidate_direction"
            )

        self._validate_normal_context(
            context,
        )

        if phase.startswith("WAITING_REVERSAL"):
            self._validate_reversal_context(
                context,
            )

    def _validate_normal_context(
        self,
        context,
    ):

        if context["candidate_direction"] is not None:
            return

        trend = context["trend"]
        phase = context["phase"]
        choch_target = self._choch_target(
            context,
        )
        bos_target = self._bos_target(
            context,
        )

        if trend == "BULLISH":
            self._require_pivot(
                choch_target,
                "LOW",
                "bullish CHOCH target",
            )

            if phase == "WAITING_BOS":
                self._require_pivot(
                    bos_target,
                    "HIGH",
                    "bullish BOS target",
                )

        elif trend == "BEARISH":
            self._require_pivot(
                choch_target,
                "HIGH",
                "bearish CHOCH target",
            )

            if phase == "WAITING_BOS":
                self._require_pivot(
                    bos_target,
                    "LOW",
                    "bearish BOS target",
                )

    def _validate_reversal_context(
        self,
        context,
    ):

        phase = context["phase"]
        direction = context["candidate_direction"]
        choch_target = self._choch_target(
            context,
        )
        bos_target = self._bos_target(
            context,
        )

        if phase == "WAITING_REVERSAL_PULLBACK":
            return

        if direction == "BULLISH":
            self._require_pivot(
                choch_target,
                "LOW",
                "bullish reversal CHOCH target",
            )

            if phase == "WAITING_REVERSAL_CONFIRMATION":
                self._require_pivot(
                    bos_target,
                    "HIGH",
                    "bullish reversal BOS target",
                )

        elif direction == "BEARISH":
            self._require_pivot(
                choch_target,
                "HIGH",
                "bearish reversal CHOCH target",
            )

            if phase == "WAITING_REVERSAL_CONFIRMATION":
                self._require_pivot(
                    bos_target,
                    "LOW",
                    "bearish reversal BOS target",
                )

    def _require_pivot(
        self,
        pivot,
        kind,
        label,
    ):

        if pivot is None:
            raise ValueError(
                f"Missing {label}"
            )

        if pivot.kind != kind:
            raise ValueError(
                f"Invalid {label}: expected {kind}, "
                f"got {pivot.kind}"
            )

    def _create_external_context(
        self,
        pivots,
    ):

        for index in range(
            1,
            len(pivots),
        ):

            start = pivots[index - 1]
            end = pivots[index]

            if start.kind == end.kind:
                continue

            if start.kind == "LOW":

                trend = "BULLISH"
                last_confirmed_HH = end
                last_confirmed_HL = start
                last_confirmed_LL = None
                last_confirmed_LH = None

            else:

                trend = "BEARISH"
                last_confirmed_HH = None
                last_confirmed_HL = None
                last_confirmed_LL = end
                last_confirmed_LH = start

            leg = ExternalLeg(
                direction=trend,
                start_pivot=start,
                end_pivot=end,
                protected_level=start,
                start_index=start.index,
                confirmed=True,
            )

            self.state.current_leg = leg
            self.state.external_legs.append(
                leg,
            )
            print(
                "INITIAL CONTEXT",
                trend,
                start.index,
                end.index,
                start.kind,
                end.kind,
            )

            return {
                "trend": trend,
                "phase": "WAITING_BOS",
                "start_pivot": start,
                "end_pivot": end,
                "last_confirmed_HH": last_confirmed_HH,
                "last_confirmed_HL": last_confirmed_HL,
                "last_confirmed_LL": last_confirmed_LL,
                "last_confirmed_LH": last_confirmed_LH,
                "candidate_direction": None,
                "reversal_snapshot": None,
            }

        return None

    def _scan_external_breaks(
        self,
        candles,
        context,
        start_index,
        end_index,
    ):

        start_index = max(
            0,
            start_index,
        )

        end_index = min(
            len(candles) - 1,
            end_index,
        )

        self._validate_context(
            context,
        )

        logger.debug(
            "\n===================="
        )
        logger.debug(
            "SCAN CALLED"
        )
        logger.debug(
            "FILE: %s",
            __file__,
        )
        logger.debug(
            "FUNCTION LINE: %s",
            self._scan_external_breaks.__code__.co_firstlineno,
        )
        logger.debug(
            "CONTEXT ID: %s",
            id(context),
        )
        logger.debug(
            "PHASE: %s",
            context["phase"],
        )
        logger.debug(
            "TREND: %s",
            context["trend"],
        )

        logger.debug(
            "PH: %s PL: %s BOS: %s CHOCH: %s",
            self._pivot_index(
                self._protected_high(context),
            ),
            self._pivot_index(
                self._protected_low(context),
            ),
            self._pivot_index(
                self._bos_target(context),
            ),
            self._pivot_index(
                self._choch_target(context),
            ),
        )

        logger.debug(
            "===================="
        )

        for index in range(
            start_index,
            end_index + 1,
        ):

            phase = context["phase"]

            if phase in (
                "WAITING_PULLBACK",
                "WAITING_REVERSAL_PULLBACK",
            ):
                return

            candle = candles[index]

            if phase in (
                "WAITING_REVERSAL_CONTINUATION",
                "WAITING_REVERSAL_CONFIRMATION",
            ):

                if self._scan_reversal_break(
                    candle,
                    context,
                    index,
                ):
                    return

                continue

            if context["trend"] == "BULLISH":

                if self._bullish_bos_break(
                    candle,
                    context,
                    index,
                ):

                    logger.debug(
                        "[SCAN] Bullish BOS detected at candle %s",
                        index,
                    )
                    return

                if self._bearish_choch_break(
                    candle,
                    context,
                    index,
                ):
                    logger.debug(
                        "[SCAN] Bearish CHOCH detected at candle %s",
                        index,
                    )
                    return

            elif context["trend"] == "BEARISH":

                if self._bearish_bos_break(
                    candle,
                    context,
                    index,
                ):
                    logger.debug(
                        "[SCAN] Bearish BOS detected at candle %s",
                        index,
                    )
                    return

                if self._bullish_choch_break(
                    candle,
                    context,
                    index,
                ):
                    logger.debug(
                        "[SCAN] Bullish CHOCH detected at candle %s",
                        index,
                    )
                    return

    def _bullish_bos_break(
        self,
        candle,
        context,
        index,
    ):

        pivot = self._bos_target(
            context,
        )
        logger.debug(
            "[BULL BOS CHECK] "
            "pivot=%s "
            "broken=%s "
            "kind=%s "
            "pivot_price=%s "
            "close=%s",
            self._pivot_index(pivot) if pivot else None,
            pivot.broken if pivot else None,
            pivot.kind if pivot else None,
            pivot.price if pivot else None,
            candle.close,
        )

        if pivot is None:
            logger.debug("FAIL: pivot is None")
            return False

        if pivot.broken:
            logger.debug("FAIL: pivot already broken")
            return False

        if pivot.kind != "HIGH":
            logger.debug("FAIL: pivot kind=%s", pivot.kind)
            return False

        if candle.close <= pivot.price:
            logger.debug(
                "FAIL: close %.2f <= pivot %.2f",
                candle.close,
                pivot.price,
            )
            return False

        self._record_external_event(
            event_type="BOS",
            direction="BULLISH",
            pivot=pivot,
            break_index=index,
            break_price=candle.close,
            context=context,
        )

        self._set_context_state(
            context,
            phase="WAITING_PULLBACK",
            trend="BULLISH",

            last_confirmed_HH=pivot,
            last_confirmed_HL=self._protected_low(context),

            candidate_direction=None,
            reversal_snapshot=None,
        )
        logger.debug(
            "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
            context["phase"],
            context["trend"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
            context["candidate_direction"],
        )

        return True

    def _bearish_bos_break(
        self,
        candle,
        context,
        index,
    ):

        pivot = self._bos_target(
            context,
        )

        if (
            pivot is None
            or pivot.broken
            or pivot.kind != "LOW"
            or candle.close >= pivot.price
        ):
            return False

        self._record_external_event(
            event_type="BOS",
            direction="BEARISH",
            pivot=pivot,
            break_index=index,
            break_price=candle.close,
            context=context,
        )

        self._set_context_state(
            context,
            phase="WAITING_PULLBACK",
            trend="BEARISH",

            last_confirmed_LL=pivot,
            last_confirmed_LH=self._protected_high(context),

            candidate_direction=None,
            reversal_snapshot=None,
        )
        logger.debug(
            "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
            context["phase"],
            context["trend"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
            context["candidate_direction"],
        )

        return True

    def _bearish_choch_break(
        self,
        candle,
        context,
        index,
    ):

        pivot = self._choch_target(
            context,
        )

        if (
            pivot is None
            or pivot.broken
            or pivot.kind != "LOW"
            or candle.close >= pivot.price
        ):
            return False

        reversal_snapshot = self._context_snapshot(
            context,
        )

        self._record_external_event(
            event_type="CHOCH",
            direction="BEARISH",
            pivot=pivot,
            break_index=index,
            break_price=candle.close,
            context=context,
        )

        self._set_context_state(
            context,
            phase="WAITING_REVERSAL_PULLBACK",
            trend=context["trend"],
            candidate_direction="BEARISH",
            reversal_snapshot=reversal_snapshot,
        )
        logger.debug(
            "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
            context["phase"],
            context["trend"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
            context["candidate_direction"],
        )

        return True

    def _bullish_choch_break(
        self,
        candle,
        context,
        index,
    ):

        pivot = self._choch_target(
            context,
        )

        if (
            pivot is None
            or pivot.broken
            or pivot.kind != "HIGH"
            or candle.close <= pivot.price
        ):
            return False

        reversal_snapshot = self._context_snapshot(
            context,
        )

        self._record_external_event(
            event_type="CHOCH",
            direction="BULLISH",
            pivot=pivot,
            break_index=index,
            break_price=candle.close,
            context=context,
        )

        self._set_context_state(
            context,
            phase="WAITING_REVERSAL_PULLBACK",
            trend=context["trend"],
            candidate_direction="BULLISH",
            reversal_snapshot=reversal_snapshot,
        )
        logger.debug(
            "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
            context["phase"],
            context["trend"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
            context["candidate_direction"],
        )

        return True

    def _scan_reversal_break(
        self,
        candle,
        context,
        index,
    ):

        self._log_reversal_scan(
            candle,
            context,
            index,
        )

        if self._check_reversal_cancel(
            candle,
            context,
        ):
            return True

        if context["phase"] != "WAITING_REVERSAL_CONFIRMATION":
            return False

        return self._confirm_reversal_bos(
            candle,
            context,
            index,
        )

    def _log_reversal_scan(
        self,
        candle,
        context,
        index,
    ):

        logger.debug(
            "[REVERSAL] phase=%s PH=%s PL=%s BOS=%s "
            "CHOCH=%s candle=%s close=%s",
            context["phase"],
            self._pivot_index(
                self._protected_high(context),
            ),
            self._pivot_index(
                self._protected_low(context),
            ),
            self._pivot_index(
                self._bos_target(context),
            ),
            self._pivot_index(
                self._choch_target(context),
            ),
            index,
            candle.close,
        )

    def _check_reversal_cancel(
        self,
        candle,
        context,
    ):

        direction = context["candidate_direction"]
        pivot = self._choch_target(
            context,
        )

        if pivot is None:
            return False

        if (
            direction == "BEARISH"
            and pivot.kind == "HIGH"
            and candle.close > pivot.price
        ):
            logger.debug(
                ">>> CANCEL REVERSAL (BEARISH)"
            )
            self._cancel_reversal(
                context,
            )

            return True

        if (
            direction == "BULLISH"
            and pivot.kind == "LOW"
            and candle.close < pivot.price
        ):
            logger.debug(
                ">>> CANCEL REVERSAL (BULLISH)"
            )
            self._cancel_reversal(
                context,
            )

            return True

        return False

    def _confirm_reversal_bos(
        self,
        candle,
        context,
        index,
    ):

        if context["candidate_direction"] == "BEARISH":
            return self._bearish_bos_break(
                candle,
                context,
                index,
            )

        if context["candidate_direction"] == "BULLISH":
            logger.debug(
                ">>> TRY BULLISH BOS CONFIRMATION"
            )
            return self._bullish_bos_break(
                candle,
                context,
                index,
            )

        return False

    def _cancel_reversal(
        self,
        context,
    ):

        snapshot = context.get(
            "reversal_snapshot",
        )

        if snapshot is None:
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend=context["trend"],
                candidate_direction=None,
                reversal_snapshot=None,
            )
            logger.debug(
                "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                context["phase"],
                context["trend"],
                self._pivot_index(context["last_confirmed_HH"]),
                self._pivot_index(context["last_confirmed_HL"]),
                self._pivot_index(context["last_confirmed_LH"]),
                self._pivot_index(context["last_confirmed_LL"]),
                context["candidate_direction"],
            )

            return

        self._restore_context_snapshot(
            context,
            snapshot,
        )

        self._publish_external_context(
            context,
        )

    def _absorb_external_pivot(
        self,
        context,
        pivot,
    ):

        phase = context["phase"]

        # ----------------------------------------------------
        # Normal BOS pullback
        # ----------------------------------------------------
        if phase == "WAITING_PULLBACK":

            if (
                context["trend"] == "BULLISH"
                and pivot.kind == "LOW"
            ):

                self._set_context_state(
                    context,
                    phase="WAITING_CONTINUATION",
                    trend="BULLISH",
                    last_confirmed_HL=pivot,
                    candidate_direction=None,
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )

            elif (
                context["trend"] == "BEARISH"
                and pivot.kind == "HIGH"
            ):

                self._set_context_state(
                    context,
                    phase="WAITING_CONTINUATION",
                    trend="BEARISH",
                    last_confirmed_LH=pivot,
                    candidate_direction=None,
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )

            return

        # ----------------------------------------------------
        # CHOCH → wait for pullback
        # ----------------------------------------------------
        if phase == "WAITING_REVERSAL_PULLBACK":

            if (
                context["candidate_direction"] == "BEARISH"
                and pivot.kind == "HIGH"
            ):
                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONTINUATION",
                    trend=context["trend"],
                    last_confirmed_LH=pivot,
                    candidate_direction="BEARISH",
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )

            elif (
                context["candidate_direction"] == "BULLISH"
                and pivot.kind == "LOW"
            ):
                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONTINUATION",
                    trend=context["trend"],
                    last_confirmed_HL=pivot,
                    candidate_direction="BULLISH",
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )


            return

        # ----------------------------------------------------
        # CHOCH → wait for continuation pivot
        # ----------------------------------------------------
        if phase == "WAITING_REVERSAL_CONTINUATION":

            if (
                context["candidate_direction"] == "BEARISH"
                and pivot.kind == "LOW"
            ):
                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONFIRMATION",
                    trend=context["trend"],
                    last_confirmed_LL=pivot,
                    candidate_direction=context["candidate_direction"],
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )

            elif (
                context["candidate_direction"] == "BULLISH"
                and pivot.kind == "HIGH"
            ):
                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONFIRMATION",
                    trend=context["trend"],
                    last_confirmed_HH=pivot,
                    candidate_direction=context["candidate_direction"],
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )


            return

        # ----------------------------------------------------
        # ONLY normal continuation may create a new BOS target
        # ----------------------------------------------------
        if phase != "WAITING_CONTINUATION":
            return

        if context["trend"] == "BULLISH":

            if pivot.kind == "HIGH":

                # newest HH becomes BOS target
                self._set_context_state(
                    context,
                    phase="WAITING_BOS",
                    trend=context["trend"],
                    last_confirmed_HH=pivot,
                    candidate_direction=None,
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )


        elif context["trend"] == "BEARISH":

            if pivot.kind == "LOW":

                # newest LL becomes BOS target
                self._set_context_state(
                    context,
                    phase="WAITING_BOS",
                    trend=context["trend"],
                    last_confirmed_LL=pivot,
                    candidate_direction=None,
                )
                logger.debug(
                    "[STATE AFTER BOS] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s candidate=%s",
                    context["phase"],
                    context["trend"],
                    self._pivot_index(context["last_confirmed_HH"]),
                    self._pivot_index(context["last_confirmed_HL"]),
                    self._pivot_index(context["last_confirmed_LH"]),
                    self._pivot_index(context["last_confirmed_LL"]),
                    context["candidate_direction"],
                )


    def _record_external_event(
        self,
        event_type,
        direction,
        pivot,
        break_index,
        break_price,
        context=None,
    ):
        logger.debug(
            "Marked pivot %s as broken.",
            pivot.index,
        )
        pivot.broken = True
        pivot.protected = False

        event = StructureEvent(
            type=event_type,
            direction=direction,
            pivot=pivot,
            break_index=break_index,
            break_price=break_price,
            leg=self.state.current_leg,
        )

        logger.debug(
            "\n[%s] %s break=%s pivot=%s idx=%s price=%.2f",
            event_type,
            direction,
            break_index,
            pivot.kind,
            pivot.index,
            pivot.price,
        )

        protected_high = self.state.protected_high
        protected_low = self.state.protected_low
        current_trend = self.state.trend

        if context is not None:
            current_trend = context["trend"]
            protected_high = self._protected_high(
                context,
            )
            protected_low = self._protected_low(
                context,
            )

        logger.debug(
            "Current Trend : %s",
            current_trend,
        )

        logger.debug(
            "Protected High: %s",
            self._pivot_index(protected_high),
        )

        logger.debug(
            "Protected Low : %s",
            self._pivot_index(protected_low),
        )

        if event_type == "BOS":
            self.state.bos_events.append(
                event,
            )
            self.state.last_bos_direction = direction
            self.state.trend = direction

        else:
            self.state.choch_events.append(
                event,
            )

        logger.debug(
            "Total BOS=%s CHOCH=%s",
            len(self.state.bos_events),
            len(self.state.choch_events),
        )


    def _publish_external_context(
        self,
        context,
    ):

        self._validate_context(
            context,
        )

        self.state.trend = context["trend"]

        self._set_protected_pivots(
            self._protected_high(
                context,
            ),
            self._protected_low(
                context,
            ),
        )

    def _pivot_position(
        self,
        pivots,
        target,
    ):

        for index, pivot in enumerate(pivots):

            if pivot is target:
                return index

        return -1

    def _set_protected_pivots(
        self,
        protected_high,
        protected_low,
    ):

        for pivot in (
            self.state.protected_high,
            self.state.protected_low,
        ):

            if pivot is None:
                continue

            if (
                pivot is protected_high
                or pivot is protected_low
            ):
                continue

            pivot.protected = False

        self.state.protected_high = protected_high
        self.state.protected_low = protected_low

        if protected_high is not None:
            protected_high.protected = True

        if protected_low is not None:
            protected_low.protected = True

    def _set_context_state(
        self,
        context,
        *,
        phase,
        trend=None,
        last_confirmed_HH=_UNSET,
        last_confirmed_HL=_UNSET,
        last_confirmed_LL=_UNSET,
        last_confirmed_LH=_UNSET,
        candidate_direction=None,
        reversal_snapshot=_UNSET,
    ):

        if trend is not None:
            context["trend"] = trend

        context["phase"] = phase

        if last_confirmed_HH is not _UNSET:
            context["last_confirmed_HH"] = last_confirmed_HH

        if last_confirmed_HL is not _UNSET:
            context["last_confirmed_HL"] = last_confirmed_HL

        if last_confirmed_LL is not _UNSET:
            context["last_confirmed_LL"] = last_confirmed_LL

        if last_confirmed_LH is not _UNSET:
            context["last_confirmed_LH"] = last_confirmed_LH

        context["candidate_direction"] = candidate_direction

        if reversal_snapshot is not _UNSET:
            context["reversal_snapshot"] = reversal_snapshot
