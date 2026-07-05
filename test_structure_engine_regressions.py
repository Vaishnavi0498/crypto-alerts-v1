import unittest

from market_structure.models import Candle
from market_structure.models import Pivot
from market_structure.structure_engine import StructureEngine


def candle(index, close):
    return Candle(
        open_time=index,
        close_time=index,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1,
    )


def pivot(index, price, kind):
    return Pivot(
        index=index,
        price=price,
        kind=kind,
        candle=candle(index, price),
    )


def bullish_context(low, high):
    return {
        "trend": "BULLISH",
        "phase": "WAITING_BOS",
        "start_pivot": low,
        "end_pivot": high,
        "last_confirmed_HH": high,
        "last_confirmed_HL": low,
        "last_confirmed_LL": None,
        "last_confirmed_LH": None,
        "candidate_direction": None,
        "reversal_snapshot": None,
    }


def bearish_context(high, low):
    return {
        "trend": "BEARISH",
        "phase": "WAITING_BOS",
        "start_pivot": high,
        "end_pivot": low,
        "last_confirmed_HH": None,
        "last_confirmed_HL": None,
        "last_confirmed_LL": low,
        "last_confirmed_LH": high,
        "candidate_direction": None,
        "reversal_snapshot": None,
    }


class StructureEngineRegressionTests(unittest.TestCase):

    def test_bullish_continuation_bos(self):
        engine = StructureEngine(left=1, right=1)
        hl = pivot(1, 100, "LOW")
        hh = pivot(2, 120, "HIGH")
        context = bullish_context(hl, hh)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_PULLBACK")
        self.assertEqual(len(engine.state.bos_events), 1)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_bearish_continuation_bos(self):
        engine = StructureEngine(left=1, right=1)
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_PULLBACK")
        self.assertEqual(len(engine.state.bos_events), 1)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_bullish_to_bearish_reversal_confirms(self):
        engine = StructureEngine(left=1, right=1)
        hl = pivot(1, 100, "LOW")
        hh = pivot(2, 120, "HIGH")
        context = bullish_context(hl, hh)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )
        lh = pivot(3, 110, "HIGH")
        ll = pivot(4, 90, "LOW")
        engine._absorb_external_pivot(context, lh)
        engine._absorb_external_pivot(context, ll)
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 89)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_PULLBACK")
        self.assertEqual(len(engine.state.bos_events), 1)
        self.assertEqual(len(engine.state.choch_events), 1)

    def test_bearish_to_bullish_reversal_confirms(self):
        engine = StructureEngine(left=1, right=1)
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )
        hl = pivot(3, 111, "LOW")
        hh = pivot(4, 130, "HIGH")
        engine._absorb_external_pivot(context, hl)
        engine._absorb_external_pivot(context, hh)
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 131)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_PULLBACK")
        self.assertEqual(len(engine.state.bos_events), 1)
        self.assertEqual(len(engine.state.choch_events), 1)

    def test_failed_bearish_reversal_restores_snapshot(self):
        engine = StructureEngine(left=1, right=1)
        hl = pivot(1, 100, "LOW")
        hh = pivot(2, 120, "HIGH")
        context = bullish_context(hl, hh)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )
        lh = pivot(3, 110, "HIGH")
        engine._absorb_external_pivot(context, lh)
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 111)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_HL"], hl)
        self.assertFalse(hl.broken)
        self.assertEqual(len(engine.state.choch_events), 0)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertEqual(len(engine.state.choch_events), 0)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 101)],
            context,
            1,
            1,
        )
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(
            context["candidate_direction"],
            "BEARISH",
        )
        self.assertEqual(len(engine.state.choch_events), 1)

    def test_failed_bullish_reversal_restores_snapshot(self):
        engine = StructureEngine(left=1, right=1)
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )
        hl = pivot(3, 111, "LOW")
        engine._absorb_external_pivot(context, hl)
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 110)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_LH"], lh)
        self.assertFalse(lh.broken)
        self.assertEqual(len(engine.state.choch_events), 0)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertEqual(len(engine.state.choch_events), 0)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 119)],
            context,
            1,
            1,
        )
        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(
            context["candidate_direction"],
            "BULLISH",
        )
        self.assertEqual(len(engine.state.choch_events), 1)

    def test_bullish_reversal_confirmation_times_out(self):
        engine = StructureEngine(
            left=1,
            right=1,
            reversal_confirmation_timeout=2,
        )
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )
        hl = pivot(3, 111, "LOW")
        hh = pivot(4, 130, "HIGH")
        engine._absorb_external_pivot(context, hl)
        engine._absorb_external_pivot(context, hh)

        self.assertEqual(
            context["phase"],
            "WAITING_REVERSAL_CONFIRMATION",
        )

        engine._scan_external_breaks(
            [candle(i, 125) for i in range(8)],
            context,
            7,
            7,
        )

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_LH"], lh)
        self.assertIs(context["last_confirmed_LL"], ll)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_bearish_reversal_confirmation_times_out(self):
        engine = StructureEngine(
            left=1,
            right=1,
            reversal_confirmation_timeout=2,
        )
        hl = pivot(1, 100, "LOW")
        hh = pivot(2, 120, "HIGH")
        context = bullish_context(hl, hh)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )
        lh = pivot(3, 110, "HIGH")
        ll = pivot(4, 90, "LOW")
        engine._absorb_external_pivot(context, lh)
        engine._absorb_external_pivot(context, ll)

        self.assertEqual(
            context["phase"],
            "WAITING_REVERSAL_CONFIRMATION",
        )

        engine._scan_external_breaks(
            [candle(i, 95) for i in range(8)],
            context,
            7,
            7,
        )

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_HL"], hl)
        self.assertIs(context["last_confirmed_HH"], hh)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_bullish_reversal_confirmation_invalidates_on_lower_low(self):
        engine = StructureEngine(left=1, right=1)
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )
        hl = pivot(3, 111, "LOW")
        hh = pivot(4, 130, "HIGH")
        lower_low = pivot(5, 109, "LOW")
        engine._absorb_external_pivot(context, hl)
        engine._absorb_external_pivot(context, hh)
        engine._absorb_external_pivot(context, lower_low)

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_LH"], lh)
        self.assertIs(context["last_confirmed_LL"], ll)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_bearish_reversal_confirmation_invalidates_on_higher_high(self):
        engine = StructureEngine(left=1, right=1)
        hl = pivot(1, 100, "LOW")
        hh = pivot(2, 120, "HIGH")
        context = bullish_context(hl, hh)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 99)],
            context,
            1,
            1,
        )
        lh = pivot(3, 110, "HIGH")
        ll = pivot(4, 90, "LOW")
        higher_high = pivot(5, 112, "HIGH")
        engine._absorb_external_pivot(context, lh)
        engine._absorb_external_pivot(context, ll)
        engine._absorb_external_pivot(context, higher_high)

        self.assertEqual(context["trend"], "BULLISH")
        self.assertEqual(context["phase"], "WAITING_BOS")
        self.assertIs(context["last_confirmed_HL"], hl)
        self.assertIs(context["last_confirmed_HH"], hh)
        self.assertEqual(len(engine.state.choch_events), 0)

    def test_candidate_reversal_does_not_pollute_confirmed_structure(self):
        engine = StructureEngine(left=1, right=1)
        lh = pivot(1, 120, "HIGH")
        ll = pivot(2, 100, "LOW")
        context = bearish_context(lh, ll)

        engine._scan_external_breaks(
            [candle(0, 110), candle(1, 121)],
            context,
            1,
            1,
        )

        hl = pivot(3, 111, "LOW")
        hh = pivot(4, 130, "HIGH")

        engine._absorb_external_pivot(context, hl)
        engine._absorb_external_pivot(context, hh)

        self.assertEqual(context["trend"], "BEARISH")
        self.assertEqual(
            context["candidate_direction"],
            "BULLISH",
        )
        self.assertIs(context["last_confirmed_LH"], lh)
        self.assertIs(context["last_confirmed_LL"], ll)
        self.assertIsNone(context["last_confirmed_HL"])
        self.assertIsNone(context["last_confirmed_HH"])
        self.assertIs(context["confirmed"]["LH"], lh)
        self.assertIs(context["confirmed"]["LL"], ll)
        self.assertIs(context["candidate"]["HL"], hl)
        self.assertIs(context["candidate"]["HH"], hh)


if __name__ == "__main__":
    unittest.main()
