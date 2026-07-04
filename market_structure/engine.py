from __future__ import annotations

from typing import List
from typing import Optional

from market_structure.models import Candle
from market_structure.models import MarketContext

from market_structure.pivots import PivotDetector
from market_structure.trend import TrendDetector
from market_structure.bos import BOSDetector
from market_structure.choch import ChoCHDetector

from market_structure.displacement import DisplacementDetector
from market_structure.fair_value_gap import FairValueGapDetector
from market_structure.order_blocks import OrderBlockDetector
from market_structure.liquidity import LiquidityDetector
from market_structure.structure_engine import StructureEngine
from market_structure.internal_structure import InternalStructureDetector


class MarketStructureEngine:

    def __init__(self):

        self.structure_engine = StructureEngine()

        self.internal_structure_detector = (
            InternalStructureDetector()
        )

        self.pivot_detector = PivotDetector()

        self.trend_detector = TrendDetector()

        self.bos_detector = BOSDetector()

        self.choch_detector = ChoCHDetector()

        self.liquidity_detector = LiquidityDetector()

        self.displacement_detector = (
            DisplacementDetector()
        )

        self.fvg_detector = (
            FairValueGapDetector()
        )

        self.order_block_detector = (
            OrderBlockDetector()
        )

    # =====================================================
    # BUILD CONTEXT
    # =====================================================

    def build_context(

        self,

        candles: List[Candle]

    ) -> MarketContext:

        context = MarketContext(

            candles=candles,

            pivots=[]

        )

        return context

    # =====================================================
    # PIVOTS
    # =====================================================

    def detect_pivots(

        self,

        context: MarketContext

    ) -> MarketContext:

        pivots = self.pivot_detector.detect(

            context.candles

        )

        context.pivots = pivots

        return context

    # =====================================================
    # TREND
    # =====================================================

    def detect_trend(

        self,

        context: MarketContext

    ) -> MarketContext:

        trend = self.trend_detector.detect(

            context.pivots

        )

        context.trend = trend

        context.internal_trend = trend

        context.external_trend = trend

        return context

    # =====================================================
    # LIQUIDITY
    # =====================================================

    def detect_liquidity(

        self,

        context: MarketContext,

    ) -> MarketContext:

        liquidity = self.liquidity_detector.detect(

            context.pivots,

            context.candles,

        )

        context.liquidity = liquidity

        return context

    # =====================================================
    # DISPLACEMENT
    # =====================================================

    def detect_displacement(

        self,

        context: MarketContext

    ) -> MarketContext:

        displacement_result = (

            self.displacement_detector.run(

                context.candles

            )

        )

        context.displacement = (

            displacement_result["all"]

        )

        return context

    # =====================================================
    # BOS
    # =====================================================

    def detect_bos(

        self,

        context: MarketContext

    ) -> MarketContext:

        bos_events = self.bos_detector.detect(

            context.candles,

            context.pivots

        )

        context.bos = bos_events

        return context

    # =====================================================
    # CHOCH
    # =====================================================

    def detect_choch(

        self,

        context: MarketContext

    ) -> MarketContext:

        choch_events = self.choch_detector.detect(

            context.candles,

            context.pivots,

            context.bos

        )

        context.choch = choch_events

        return context


    # =====================================================
    # FVG
    # =====================================================

    def detect_fvg(

        self,

        context: MarketContext,

    ) -> MarketContext:

        gaps = self.fvg_detector.detect(

            context.candles,

        )

        context.fvgs = gaps

        return context

    # =====================================================
    # ORDER BLOCKS
    # =====================================================

    def detect_order_blocks(

        self,

        context: MarketContext

    ) -> MarketContext:

        order_blocks = self.order_block_detector.detect(

            context.candles,

            context.bos or [],

            context.choch or [],

            context.liquidity or [],

        )

        context.order_blocks = order_blocks

        return context

    # =====================================================
    # PIPELINE
    # =====================================================

    def analyse(

        self,

        candles: List[Candle]

    ) -> MarketContext:

        context = self.build_context(

            candles

        )

        structure = self.structure_engine.detect(
            candles
        )

        context.pivots = structure["pivots"]
        context.trend = structure["state"].trend
        context.external_trend = structure["state"].trend
        context.bos = structure["bos"]
        context.choch = structure["choch"]

        internal_structure = (
            self.internal_structure_detector.detect(
                context.pivots,
                context.candles,
                context.external_trend,
            )
        )

        context.internal_trend = internal_structure.trend
        context.internal_structure = internal_structure.points
        context.internal_bos = internal_structure.bos
        context.internal_choch = internal_structure.choch

        context = self.detect_liquidity(

            context

        )

        context = self.detect_displacement(

            context

        )

        context = self.detect_fvg(

            context

        )

        context = self.detect_order_blocks(

            context

        )
#below 1 line for testing purpose only, remove it in production
        self.validate_context(context)

        return context

    # =====================================================
    # LATEST BOS
    # =====================================================

    def latest_bos(

        self,

        context: MarketContext,

    ):

        if not context.bos:

            return None

        return context.bos[-1]

    # =====================================================
    # LATEST CHOCH
    # =====================================================

    def latest_choch(

        self,

        context: MarketContext,

    ):

        if not context.choch:

            return None

        return context.choch[-1]

    # =====================================================
    # LATEST FVG
    # =====================================================

    def latest_fvg(

        self,

        context: MarketContext,

    ):

        if not context.fvgs:

            return None

        return context.fvgs[-1]

    # =====================================================
    # LATEST ORDER BLOCK
    # =====================================================

    def latest_order_block(

        self,

        context: MarketContext,

    ):

        if not context.order_blocks:

            return None

        return context.order_blocks[-1]

    # =====================================================
    # LATEST DISPLACEMENT
    # =====================================================

    def latest_displacement(

        self,

        context: MarketContext,

    ):

        if not context.displacement:

            return None

        return context.displacement[-1]

    # =====================================================
    # CONFLUENCE SCORE
    # =====================================================

    def confluence_score(

        self,

        context: MarketContext,

    ):

        score = 0

        reasons = []

        if context.trend == "BULLISH":

            score += 10

            reasons.append(

                "Bullish Trend"

            )

        elif context.trend == "BEARISH":

            score += 10

            reasons.append(

                "Bearish Trend"

            )

        if context.bos:

            score += 20

            reasons.append(

                "Break Of Structure"

            )

        if context.choch:

            score += 20

            reasons.append(

                "ChoCH"

            )

        if context.displacement:

            score += 15

            reasons.append(

                "Displacement"

            )

        if context.fvgs:

            score += 10

            reasons.append(

                "Fair Value Gap"

            )

        if context.order_blocks:

            score += 15

            reasons.append(

                "Order Block"

            )

        if context.liquidity:

            score += 10

            reasons.append(

                "Liquidity"

            )

        return {

            "score": score,

            "reasons": reasons,

        }

    # =====================================================
    # MARKET BIAS
    # =====================================================

    def market_bias(

        self,

        context: MarketContext,

    ):

        score = self.confluence_score(

            context

        )["score"]

        if score >= 75:

            return "VERY_STRONG"

        if score >= 60:

            return "STRONG"

        if score >= 45:

            return "MODERATE"

        if score >= 30:

            return "WEAK"

        return "NONE"

    # =====================================================
    # ENTRY ZONE
    # =====================================================

    def entry_zone(
        self,
        context: MarketContext,
    ):

        ob = self.latest_order_block(context)

        if ob is not None:

            return {
                "type": "ORDER_BLOCK",
                "price": (ob.high + ob.low) / 2,
                "high": ob.high,
                "low": ob.low,
            }

        fvg = self.latest_fvg(context)

        if fvg is not None:

            return {
                "type": "FVG",
                "price": (
                    fvg.start_price +
                    fvg.end_price
                ) / 2,
                "high": fvg.start_price,
                "low": fvg.end_price,
            }

        return None

    # =====================================================
    # STOP LOSS
    # =====================================================

    def stop_loss(
        self,
        context: MarketContext,
    ):

        liquidity = context.liquidity

        if liquidity:

            level = liquidity[-1]

            if context.trend == "BULLISH":

                return level.price * 0.998

            return level.price * 1.002

        entry = self.entry_zone(context)

        if entry is None:
            return None

        if context.trend == "BULLISH":

            return entry["low"]

        return entry["high"]

    # =====================================================
    # TAKE PROFIT
    # =====================================================

    def take_profit(
        self,
        context: MarketContext,
    ):

        sl = self.stop_loss(context)

        entry = self.entry_zone(context)

        if sl is None or entry is None:

            return None

        risk = abs(
            entry["price"] - sl
        )

        if context.trend == "BULLISH":

            return entry["price"] + risk * 3

        return entry["price"] - risk * 3

    # =====================================================
    # BUILD SIGNAL
    # =====================================================

    def build_signal(
        self,
        context: MarketContext,
    ):

        confidence = self.confluence_score(
            context
        )

        return {

            "trend": context.trend,

            "bias": self.market_bias(
                context
            ),

            "confidence": confidence,

            "entry": self.entry_zone(
                context
            ),

            "stop_loss": self.stop_loss(
                context
            ),

            "take_profit": self.take_profit(
                context
            ),

            "bos": self.latest_bos(
                context
            ),

            "choch": self.latest_choch(
                context
            ),

            "displacement": self.latest_displacement(
                context
            ),

            "order_block": self.latest_order_block(
                context
            ),

            "fvg": self.latest_fvg(
                context
            ),

        }

    # =====================================================
    # DEBUG
    # =====================================================

    def debug(
        self,
        context: MarketContext,
    ):

        print("=" * 80)

        print("TREND")

        print(context.trend)

        print()

        print("PIVOTS")

        print(len(context.pivots))

        print("BOS")

        print(len(context.bos or []))

        print("CHOCH")

        print(len(context.choch or []))

        print("INTERNAL BOS")

        print(len(context.internal_bos or []))

        print("INTERNAL CHOCH")

        print(len(context.internal_choch or []))

        print("LIQUIDITY")

        print(len(context.liquidity or []))

        print("DISPLACEMENT")

        print(len(context.displacement or []))

        print("FVG")

        print(len(context.fvgs or []))

        print("ORDER BLOCKS")

        print(len(context.order_blocks or []))

        print()

        confidence = self.confluence_score(
            context
        )

        print(

            "CONFIDENCE",

            confidence["score"],

            confidence["reasons"],

        )

        signal = self.build_signal(
            context
        )

        print()

        print("SIGNAL")

        for key, value in signal.items():

            print(

                key,

                ":",

                value,

            )

        print("=" * 80)

    # =====================================================
    # PUBLIC API
    # =====================================================

    def run(
        self,
        candles: List[Candle],
    ):

        context = self.analyse(
            candles
        )

        signal = self.build_signal(
            context
        )

        return {

            "context": context,

            "signal": signal,

        }

        #below method for testing purpose only, remove it in production

    def validate_context(
        self,
        context,
    ):

        # -----------------------------------
        # Trend
        # -----------------------------------

        assert context.trend in (
            "BULLISH",
            "BEARISH",
            "RANGE",
            "UNKNOWN",
        ), f"Invalid trend: {context.trend}"

        # -----------------------------------
        # Collections exist
        # -----------------------------------

        assert context.pivots is not None

        assert context.bos is not None

        assert context.choch is not None

        assert context.internal_structure is not None

        assert context.internal_bos is not None

        assert context.internal_choch is not None

        assert context.liquidity is not None

        assert context.fvgs is not None

        assert context.order_blocks is not None

        # -----------------------------------
        # BOS / CHOCH consistency
        # -----------------------------------

        assert len(context.bos) >= len(
            context.choch
        ), (
            "CHOCH count exceeds BOS count"
        )

        # -----------------------------------
        # Pivot sanity
        # -----------------------------------

        for pivot in context.pivots:

            assert pivot.kind in (
                "HIGH",
                "LOW",
            ), (
                f"Invalid pivot kind: {pivot.kind}"
            )

        # -----------------------------------
        # BOS sanity
        # -----------------------------------

        for bos in context.bos:

            assert bos.direction in (
                "BULLISH",
                "BEARISH",
            )

        # -----------------------------------
        # CHOCH sanity
        # -----------------------------------

        for choch in context.choch:

            assert choch.direction in (
                "BULLISH",
                "BEARISH",
            )

            assert (
                0
                <= choch.confidence
                <= 100
            )

        # -----------------------------------
        # Internal structure sanity
        # -----------------------------------

        for event in (
            context.internal_bos
            + context.internal_choch
        ):

            assert event.type in (
                "BOS",
                "CHOCH",
            )

            assert event.direction in (
                "BULLISH",
                "BEARISH",
            )

        # -----------------------------------
        # Order Block sanity
        # -----------------------------------

        for ob in context.order_blocks:

            assert ob.side in (
                "BULLISH",
                "BEARISH",
            )

            assert ob.high >= ob.low

        # -----------------------------------
        # FVG sanity
        # -----------------------------------

        for gap in context.fvgs:

            assert gap.side in (
                "BULLISH",
                "BEARISH",
            )

            assert gap.upper >= gap.lower


if __name__ == "__main__":

    print("Market Structure Engine Loaded")
