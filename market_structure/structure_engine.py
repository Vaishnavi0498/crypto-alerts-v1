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

    def __init__(
        self,
        left=3,
        right=3,
        reversal_confirmation_timeout=15,
    ):

        self.left = left
        self.right = right
        self.reversal_confirmation_timeout = (
            reversal_confirmation_timeout
        )

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

        structure = self._target_structure(
            context,
        )
        direction = structure["trend"]

        if direction == "BULLISH":
            return structure["HH"]

        if direction == "BEARISH":
            return structure["LL"]

        return None

    def _choch_target(
        self,
        context,
    ):

        structure = self._target_structure(
            context,
        )
        direction = structure["trend"]

        if direction == "BULLISH":
            return structure["HL"]

        if direction == "BEARISH":
            return structure["LH"]

        return None

    def _target_structure(
        self,
        context,
    ):

        self._ensure_structures(
            context,
        )

        if context["phase"].startswith(
            "WAITING_REVERSAL"
        ):
            return context["candidate"] or {
                "trend": context["candidate_direction"],
                "HH": None,
                "HL": None,
                "LL": None,
                "LH": None,
            }

        return context["confirmed"]

    def _ensure_structures(
        self,
        context,
    ):

        if "confirmed" not in context:
            context["confirmed"] = {
                "trend": context["trend"],
                "HH": context["last_confirmed_HH"],
                "HL": context["last_confirmed_HL"],
                "LL": context["last_confirmed_LL"],
                "LH": context["last_confirmed_LH"],
            }

        if "candidate" not in context:
            context["candidate"] = None

    def _empty_structure(
        self,
        direction,
    ):

        return {
            "trend": direction,
            "HH": None,
            "HL": None,
            "LL": None,
            "LH": None,
        }

    def _candidate_structure(
        self,
        context,
    ):

        self._ensure_structures(
            context,
        )

        if context["candidate"] is None:
            context["candidate"] = self._empty_structure(
                context["candidate_direction"],
            )

        return context["candidate"]

    def _promote_candidate(
        self,
        context,
    ):

        candidate = context["candidate"]

        if candidate is None:
            raise ValueError(
                "Cannot promote missing candidate structure"
            )

        context["confirmed"] = candidate.copy()
        context["candidate"] = None

        context["last_confirmed_HH"] = candidate["HH"]
        context["last_confirmed_HL"] = candidate["HL"]
        context["last_confirmed_LL"] = candidate["LL"]
        context["last_confirmed_LH"] = candidate["LH"]

    def _protected_high(
        self,
        context,
    ):

        structure = self._target_structure(
            context,
        )

        if structure["trend"] == "BEARISH":
            return self._active_pivot(
                structure["LH"],
            )

        return None

    def _protected_low(
        self,
        context,
    ):

        structure = self._target_structure(
            context,
        )

        if structure["trend"] == "BULLISH":
            return self._active_pivot(
                structure["HL"],
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

    def _log_context_state(
        self,
        label,
        context,
    ):

        logger.debug(
            "[%s] phase=%s trend=%s HH=%s HL=%s LH=%s LL=%s "
            "candidate=%s candidate_HH=%s candidate_HL=%s "
            "candidate_LH=%s candidate_LL=%s",
            label,
            context["phase"],
            context["trend"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
            context["candidate_direction"],
            self._pivot_index(
                context["candidate"]["HH"]
                if context.get("candidate")
                else None
            ),
            self._pivot_index(
                context["candidate"]["HL"]
                if context.get("candidate")
                else None
            ),
            self._pivot_index(
                context["candidate"]["LH"]
                if context.get("candidate")
                else None
            ),
            self._pivot_index(
                context["candidate"]["LL"]
                if context.get("candidate")
                else None
            ),
        )

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
            "confirmed": context["confirmed"].copy(),
            "candidate": (
                context["candidate"].copy()
                if context["candidate"] is not None
                else None
            ),
            "last_confirmed_HH": context["last_confirmed_HH"],
            "last_confirmed_HL": context["last_confirmed_HL"],
            "last_confirmed_LL": context["last_confirmed_LL"],
            "last_confirmed_LH": context["last_confirmed_LH"],
            "candidate_direction": context["candidate_direction"],
            "reversal_attempt": context.get("reversal_attempt"),
            "reversal_confirmation_start_index": context.get(
                "reversal_confirmation_start_index",
            ),
            "failed_reversals": set(
                context.get(
                    "failed_reversals",
                    set(),
                )
            ),
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

        for pivot, broken, protected in snapshot["pivot_flags"]:
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
                "confirmed": snapshot["confirmed"].copy(),
                "candidate": (
                    snapshot["candidate"].copy()
                    if snapshot["candidate"] is not None
                    else None
                ),
                "last_confirmed_HH": snapshot["last_confirmed_HH"],
                "last_confirmed_HL": snapshot["last_confirmed_HL"],
                "last_confirmed_LL": snapshot["last_confirmed_LL"],
                "last_confirmed_LH": snapshot["last_confirmed_LH"],
                "candidate_direction": snapshot["candidate_direction"],
                "reversal_attempt": snapshot.get("reversal_attempt"),
                "reversal_confirmation_start_index": snapshot.get(
                    "reversal_confirmation_start_index",
                ),
                "failed_reversals": set(
                    snapshot["failed_reversals"],
                ),
                "reversal_snapshot": None,
            }
        )

        logger.debug(
            "[RESTORE] trend=%s phase=%s HH=%s HL=%s LH=%s LL=%s BOS=%d CHOCH=%d",
            context["trend"],
            context["phase"],
            self._pivot_index(context["last_confirmed_HH"]),
            self._pivot_index(context["last_confirmed_HL"]),
            self._pivot_index(context["last_confirmed_LH"]),
            self._pivot_index(context["last_confirmed_LL"]),
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
            logger.debug(
                "INITIAL CONTEXT %s %s %s %s %s",
                trend,
                start.index,
                end.index,
                start.kind,
                end.kind,
            )

            confirmed = {
                "trend": trend,
                "HH": last_confirmed_HH,
                "HL": last_confirmed_HL,
                "LL": last_confirmed_LL,
                "LH": last_confirmed_LH,
            }

            return {
                "trend": trend,
                "phase": "WAITING_BOS",
                "start_pivot": start,
                "end_pivot": end,
                "confirmed": confirmed,
                "candidate": None,
                "last_confirmed_HH": last_confirmed_HH,
                "last_confirmed_HL": last_confirmed_HL,
                "last_confirmed_LL": last_confirmed_LL,
                "last_confirmed_LH": last_confirmed_LH,
                "candidate_direction": None,
                "reversal_snapshot": None,
                "reversal_attempt": None,
                "reversal_confirmation_start_index": None,
                "failed_reversals": set(),
            }

        return None

    def _reversal_key(
        self,
        direction,
        pivot,
    ):

        if pivot is None:
            return None

        return (
            direction,
            pivot.index,
            pivot.kind,
            pivot.price,
        )

    def _failed_reversal_blocks_break(
        self,
        context,
        direction,
        pivot,
        candle,
    ):

        key = self._reversal_key(
            direction,
            pivot,
        )

        if key is None:
            return False

        failed_reversals = context.setdefault(
            "failed_reversals",
            set(),
        )

        if key not in failed_reversals:
            return False

        if (
            direction == "BULLISH"
            and candle.close <= pivot.price
        ):
            failed_reversals.remove(
                key,
            )
            return False

        if (
            direction == "BEARISH"
            and candle.close >= pivot.price
        ):
            failed_reversals.remove(
                key,
            )
            return False

        return True

    def _mark_failed_reversal_key(
        self,
        context,
        key,
    ):

        if key is None:
            return

        context.setdefault(
            "failed_reversals",
            set(),
        ).add(
            key,
        )

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
            "[SCAN] start=%s end=%s phase=%s trend=%s PH=%s PL=%s BOS=%s CHOCH=%s",
            start_index,
            end_index,
            context["phase"],
            context["trend"],
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

        if context["phase"].startswith(
            "WAITING_REVERSAL"
        ):
            self._promote_candidate(
                context,
            )
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend="BULLISH",
                candidate_direction=None,
                reversal_snapshot=None,
                reversal_attempt=None,
                reversal_confirmation_start_index=None,
            )
        else:
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend="BULLISH",

                last_confirmed_HH=pivot,
                last_confirmed_HL=self._protected_low(context),

                candidate_direction=None,
                reversal_snapshot=None,
                reversal_attempt=None,
                reversal_confirmation_start_index=None,
            )
        self._log_context_state(
            "STATE AFTER BULLISH BOS",
            context,
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

        if context["phase"].startswith(
            "WAITING_REVERSAL"
        ):
            self._promote_candidate(
                context,
            )
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend="BEARISH",
                candidate_direction=None,
                reversal_snapshot=None,
                reversal_attempt=None,
                reversal_confirmation_start_index=None,
            )
        else:
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend="BEARISH",

                last_confirmed_LL=pivot,
                last_confirmed_LH=self._protected_high(context),

                candidate_direction=None,
                reversal_snapshot=None,
                reversal_attempt=None,
                reversal_confirmation_start_index=None,
            )
        self._log_context_state(
            "STATE AFTER BEARISH BOS",
            context,
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

        logger.debug(
            "[BEAR CHOCH CHECK] "
            "index=%s "
            "pivot=%s "
            "broken=%s "
            "kind=%s "
            "pivot_price=%s "
            "close=%s "
            "phase=%s "
            "trend=%s",
            index,
            self._pivot_index(pivot) if pivot else None,
            pivot.broken if pivot else None,
            pivot.kind if pivot else None,
            pivot.price if pivot else None,
            candle.close,
            context["phase"],
            context["trend"],
        )
        if pivot is None:
            logger.debug("FAIL: pivot is None")
            return False

        if self._failed_reversal_blocks_break(
            context,
            "BEARISH",
            pivot,
            candle,
        ):
            logger.debug(
                "FAIL: bearish reversal not re-armed for pivot %s",
                pivot.index,
            )
            return False

        if pivot.broken:
            logger.debug("FAIL: pivot already broken")
            return False

        if pivot.kind != "LOW":
            logger.debug("FAIL: pivot kind=%s", pivot.kind)
            return False

        if candle.close >= pivot.price:
            logger.debug(
                "FAIL: close %.2f >= pivot %.2f",
                candle.close,
                pivot.price,
            )
            return False

        logger.debug(
            "SUCCESS: BEARISH CHOCH at candle %s under pivot %s",
            index,
            pivot.index,
        )

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
            candidate=self._empty_structure(
                "BEARISH",
            ),
            reversal_snapshot=reversal_snapshot,
            reversal_attempt=self._reversal_key(
                "BEARISH",
                pivot,
            ),
            reversal_confirmation_start_index=None,
        )

        self._log_context_state(
            "STATE AFTER BEARISH CHOCH",
            context,
        )

        return True

    def _bullish_choch_break(
        self,
        candle,
        context,
        index,
    ):

        pivot = self._choch_target(context)

        logger.debug(
            "[BULL CHOCH CHECK] index=%s pivot=%s close=%s phase=%s trend=%s",
            index,
            None if pivot is None else (
                pivot.index,
                pivot.kind,
                pivot.price,
                pivot.broken,
            ),
            candle.close,
            context["phase"],
            context["trend"],
        )

        if pivot is None:
            logger.debug("FAIL: pivot is None")
            return False

        if self._failed_reversal_blocks_break(
            context,
            "BULLISH",
            pivot,
            candle,
        ):
            logger.debug(
                "FAIL: bullish reversal not re-armed for pivot %s",
                pivot.index,
            )
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

        logger.debug(
            "SUCCESS: BULLISH CHOCH at candle %s over pivot %s",
            index,
            pivot.index,
        )

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
            candidate=self._empty_structure(
                "BULLISH",
            ),
            reversal_snapshot=reversal_snapshot,
            reversal_attempt=self._reversal_key(
                "BULLISH",
                pivot,
            ),
            reversal_confirmation_start_index=None,
        )

        self._log_context_state(
            "STATE AFTER BULLISH CHOCH",
            context,
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

        if self._check_reversal_timeout(
            context,
            index,
        ):
            return True

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

        confirmed = context["confirmed"]
        candidate = context.get("candidate") or {}

        logger.debug(
            "[REVERSAL] phase=%s "
            "confirmed_HH=%s confirmed_HL=%s confirmed_LH=%s confirmed_LL=%s "
            "candidate_HH=%s candidate_HL=%s candidate_LH=%s candidate_LL=%s "
            "BOS=%s CHOCH=%s candle=%s close=%s",
            context["phase"],
            self._pivot_index(
                confirmed.get("HH"),
            ),
            self._pivot_index(
                confirmed.get("HL"),
            ),
            self._pivot_index(
                confirmed.get("LH"),
            ),
            self._pivot_index(
                confirmed.get("LL"),
            ),
            self._pivot_index(
                candidate.get("HH"),
            ),
            self._pivot_index(
                candidate.get("HL"),
            ),
            self._pivot_index(
                candidate.get("LH"),
            ),
            self._pivot_index(
                candidate.get("LL"),
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

    def _check_reversal_timeout(
        self,
        context,
        index,
    ):

        timeout = self.reversal_confirmation_timeout

        if timeout is None:
            return False

        start_index = context.get(
            "reversal_confirmation_start_index",
        )

        if start_index is None:
            return False

        if index - start_index <= timeout:
            return False

        logger.debug(
            ">>> CANCEL REVERSAL (%s timeout after %s candles)",
            context["candidate_direction"],
            index - start_index,
        )
        self._cancel_reversal(
            context,
        )

        return True

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
                direction,
                pivot,
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
                direction,
                pivot,
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
        failed_direction=None,
        failed_pivot=None,
    ):

        snapshot = context.get(
            "reversal_snapshot",
        )
        failed_key = context.get(
            "reversal_attempt",
        )

        if snapshot is None:
            self._set_context_state(
                context,
                phase="WAITING_PULLBACK",
                trend=context["trend"],
                candidate_direction=None,
                reversal_snapshot=None,
                reversal_attempt=None,
                reversal_confirmation_start_index=None,
            )
            if failed_key is None:
                failed_key = self._reversal_key(
                    failed_direction,
                    failed_pivot,
                )
            self._mark_failed_reversal_key(
                context,
                failed_key,
            )
            self._log_context_state(
                "STATE AFTER CANCEL REVERSAL",
                context,
            )

            return

        self._restore_context_snapshot(
            context,
            snapshot,
        )

        if failed_key is None:
            failed_key = self._reversal_key(
                failed_direction,
                failed_pivot,
            )
        self._mark_failed_reversal_key(
            context,
            failed_key,
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
                self._log_context_state(
                    "STATE AFTER BULLISH PULLBACK",
                    context,
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
                self._log_context_state(
                    "STATE AFTER BEARISH PULLBACK",
                    context,
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
                candidate = self._candidate_structure(
                    context,
                )
                candidate["LH"] = pivot

                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONTINUATION",
                    trend=context["trend"],
                    candidate_direction="BEARISH",
                )
                self._log_context_state(
                    "STATE AFTER BEARISH REVERSAL PULLBACK",
                    context,
                )

            elif (
                context["candidate_direction"] == "BULLISH"
                and pivot.kind == "LOW"
            ):
                candidate = self._candidate_structure(
                    context,
                )
                candidate["HL"] = pivot

                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONTINUATION",
                    trend=context["trend"],
                    candidate_direction="BULLISH",
                )
                self._log_context_state(
                    "STATE AFTER BULLISH REVERSAL PULLBACK",
                    context,
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
                candidate = self._candidate_structure(
                    context,
                )
                candidate["LL"] = pivot

                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONFIRMATION",
                    trend=context["trend"],
                    candidate_direction=context["candidate_direction"],
                    reversal_confirmation_start_index=pivot.index,
                )
                self._log_context_state(
                    "STATE AFTER BEARISH REVERSAL CONTINUATION",
                    context,
                )

            elif (
                context["candidate_direction"] == "BULLISH"
                and pivot.kind == "HIGH"
            ):
                candidate = self._candidate_structure(
                    context,
                )
                candidate["HH"] = pivot

                self._set_context_state(
                    context,
                    phase="WAITING_REVERSAL_CONFIRMATION",
                    trend=context["trend"],
                    candidate_direction=context["candidate_direction"],
                    reversal_confirmation_start_index=pivot.index,
                )
                self._log_context_state(
                    "STATE AFTER BULLISH REVERSAL CONTINUATION",
                    context,
                )


            return

        # ----------------------------------------------------
        # Candidate invalidation before reversal confirmation
        # ----------------------------------------------------
        if phase == "WAITING_REVERSAL_CONFIRMATION":

            candidate = context.get("candidate") or {}

            if (
                context["candidate_direction"] == "BULLISH"
                and pivot.kind == "LOW"
                and candidate.get("HL") is not None
                and pivot.price < candidate["HL"].price
            ):
                logger.debug(
                    ">>> CANCEL REVERSAL (BULLISH invalidated by lower low %s)",
                    pivot.index,
                )
                self._cancel_reversal(
                    context,
                )
                return

            if (
                context["candidate_direction"] == "BEARISH"
                and pivot.kind == "HIGH"
                and candidate.get("LH") is not None
                and pivot.price > candidate["LH"].price
            ):
                logger.debug(
                    ">>> CANCEL REVERSAL (BEARISH invalidated by higher high %s)",
                    pivot.index,
                )
                self._cancel_reversal(
                    context,
                )
                return

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
                self._log_context_state(
                    "STATE AFTER BULLISH CONTINUATION PIVOT",
                    context,
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
                self._log_context_state(
                    "STATE AFTER BEARISH CONTINUATION PIVOT",
                    context,
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
        protected_high = self.state.protected_high
        protected_low = self.state.protected_low
        current_trend = self.state.trend
        confirmed = None
        candidate = None

        if context is not None:
            current_trend = context["trend"]
            protected_high = self._protected_high(
                context,
            )
            protected_low = self._protected_low(
                context,
            )
            confirmed = context.get(
                "confirmed",
            )
            candidate = context.get(
                "candidate",
            )

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

        logger.debug(
            "Current Trend : %s",
            current_trend,
        )

        logger.debug(
            "Protected High before break: %s",
            self._pivot_index(protected_high),
        )

        logger.debug(
            "Protected Low before break : %s",
            self._pivot_index(protected_low),
        )

        if confirmed is not None:
            logger.debug(
                "Confirmed structure before break: "
                "HH=%s HL=%s LH=%s LL=%s",
                self._pivot_index(
                    confirmed.get("HH"),
                ),
                self._pivot_index(
                    confirmed.get("HL"),
                ),
                self._pivot_index(
                    confirmed.get("LH"),
                ),
                self._pivot_index(
                    confirmed.get("LL"),
                ),
            )

        if candidate is not None:
            logger.debug(
                "Candidate structure before break : "
                "HH=%s HL=%s LH=%s LL=%s",
                self._pivot_index(
                    candidate.get("HH"),
                ),
                self._pivot_index(
                    candidate.get("HL"),
                ),
                self._pivot_index(
                    candidate.get("LH"),
                ),
                self._pivot_index(
                    candidate.get("LL"),
                ),
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
        confirmed=_UNSET,
        candidate=_UNSET,
        candidate_direction=None,
        reversal_snapshot=_UNSET,
        reversal_attempt=_UNSET,
        reversal_confirmation_start_index=_UNSET,
    ):

        if trend is not None:
            context["trend"] = trend
            if (
                "confirmed" in context
                and context["confirmed"] is not None
                and candidate_direction is None
            ):
                context["confirmed"]["trend"] = trend

        context["phase"] = phase

        if confirmed is not _UNSET:
            context["confirmed"] = confirmed

        if candidate is not _UNSET:
            context["candidate"] = candidate

        self._ensure_structures(
            context,
        )

        if last_confirmed_HH is not _UNSET:
            context["last_confirmed_HH"] = last_confirmed_HH
            context["confirmed"]["HH"] = last_confirmed_HH

        if last_confirmed_HL is not _UNSET:
            context["last_confirmed_HL"] = last_confirmed_HL
            context["confirmed"]["HL"] = last_confirmed_HL

        if last_confirmed_LL is not _UNSET:
            context["last_confirmed_LL"] = last_confirmed_LL
            context["confirmed"]["LL"] = last_confirmed_LL

        if last_confirmed_LH is not _UNSET:
            context["last_confirmed_LH"] = last_confirmed_LH
            context["confirmed"]["LH"] = last_confirmed_LH

        context["candidate_direction"] = candidate_direction

        if reversal_snapshot is not _UNSET:
            context["reversal_snapshot"] = reversal_snapshot

        if reversal_attempt is not _UNSET:
            context["reversal_attempt"] = reversal_attempt

        if reversal_confirmation_start_index is not _UNSET:
            context["reversal_confirmation_start_index"] = (
                reversal_confirmation_start_index
            )
