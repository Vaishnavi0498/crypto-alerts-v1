from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Candle:

    open_time: int
    close_time: int

    open: float
    high: float
    low: float
    close: float

    volume: float


@dataclass
class Pivot:

    index: int

    price: float

    kind: str

    candle: Candle

    # --------------------------
    # New fields
    # --------------------------

    label: str = ""

    protected: bool = False

    broken: bool = False

@dataclass
class Swing:

    pivot: Pivot

    label: str

    protected: bool = False


@dataclass
class BreakOfStructure:

    direction: str

    pivot: Pivot

    break_index: int

    break_price: float


@dataclass
class ExternalLeg:

    direction: str

    start_pivot: Pivot

    end_pivot: Pivot

    protected_level: Pivot

    start_index: int

    end_index: int | None = None

    bos_history: list = field(default_factory=list)

    choch_history: list = field(default_factory=list)

    active: bool = True

    waiting_for_protected: bool = False

    confirmed: bool = True

    @property
    def protected_high(self):

        if self.protected_level.kind == "HIGH":
            return self.protected_level

        return None

    @property
    def protected_low(self):

        if self.protected_level.kind == "LOW":
            return self.protected_level

        return None

@dataclass
class StructureState:

    trend: str = "UNKNOWN"

    protected_high: Pivot | None = None
    protected_low: Pivot | None = None

    last_high: Pivot | None = None
    last_low: Pivot | None = None

    current_leg: ExternalLeg | None = None
    external_legs: list = field(default_factory=list)

    bos_events: list = field(default_factory=list)
    choch_events: list = field(default_factory=list)

    liquidity: list = field(default_factory=list)

    displacement: list = field(default_factory=list)

    fvgs: list = field(default_factory=list)

    order_blocks: list = field(default_factory=list)

    last_bos_direction: str | None = None

@dataclass
class StructureEvent:

    type: str

    direction: str

    pivot: Pivot

    break_index: int

    break_price: float

    leg: ExternalLeg | None = None

    @property
    def index(self):

        return self.break_index

    @property
    def price(self):

        return self.break_price

    @property
    def confidence(self):

        return 100


@dataclass
class LiquidityZone:

    direction: str

    price: float

    start_index: int

    end_index: int


@dataclass
class Displacement:

    direction: str

    index: int

    body_size: float

    atr_multiple: float


@dataclass
class FairValueGap:

    direction: str

    start_price: float

    end_price: float

    index: int


@dataclass
class OrderBlock:

    direction: str

    candle_index: int

    high: float

    low: float


@dataclass
class ChoCHSignal:

    direction: str

    index: int

    confidence: float

@dataclass
class BOS:

    direction: str

    pivot: Pivot

    break_index: int

    break_price: float


@dataclass
class MarketContext:

    candles: List[Candle]

    pivots: List[Pivot]

    trend: str = "UNKNOWN"

    internal_trend: str = "UNKNOWN"

    external_trend: str = "UNKNOWN"

    internal_structure: list = None

    internal_bos: list = None

    internal_choch: list = None

    bos: List[BreakOfStructure] = None

    liquidity: List[LiquidityZone] = None

    displacement: List[Displacement] = None

    fvgs: List[FairValueGap] = None

    order_blocks: List[OrderBlock] = None

    choch: List[ChoCHSignal] = None
