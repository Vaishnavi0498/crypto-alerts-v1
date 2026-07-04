from dataclasses import dataclass


@dataclass
class MarketStructureConfig:

    # Swing detection

    LEFT_BARS = 3
    RIGHT_BARS = 3

    # Internal structure

    INTERNAL_LOOKBACK = 30

    # External structure

    EXTERNAL_LOOKBACK = 150

    # BOS

    BOS_CONFIRMATION_CLOSE = True

    # Liquidity

    EQUAL_HIGH_THRESHOLD = 0.0015
    EQUAL_LOW_THRESHOLD = 0.0015

    # Displacement

    DISPLACEMENT_BODY_MULTIPLIER = 2.0
    DISPLACEMENT_VOLUME_MULTIPLIER = 1.5

    # ATR

    ATR_PERIOD = 14

    # FVG

    MIN_FVG_SIZE = 0.0005

    # Order Block

    MAX_OB_LOOKBACK = 20