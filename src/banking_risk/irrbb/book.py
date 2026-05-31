"""
Banking book data model for IRRBB and NII analytics.

This module defines the core balance-sheet abstractions used throughout the
IRRBB framework. It provides a uniform representation of interest-rate
sensitive assets, liabilities, and non-maturity deposits (NMDs), independent
of the downstream calculation engine.

The design separates:

- Data representation (Position, NMD_Portfolio)
- Balance-sheet containers (Banking_Book implementations)
- Risk calculations (EVE, NII, gap analysis, repricing ladders, etc.)

The central abstraction is Banking_Book, an interface exposing the positions
and balance-sheet totals required by risk calculators. Concrete
implementations provide different modelling assumptions while preserving a
common API.

Key concepts
------------
Position
    Atomic interest-rate sensitive instrument. Represents a fixed-rate or
    floating-rate asset or liability with contractual cash-flow and repricing
    characteristics.

Standard_Banking_Book
    Banking book composed solely of Position objects. Suitable for portfolios
    where all instruments have explicit contractual repricing behaviour.

NMD_Portfolio
    Behavioural representation of non-maturity deposits. Models stable and
    volatile balances according to EBA/GL/2022/14 assumptions.

NMD_Banking_Book
    Banking book that combines contractual positions with NMD portfolios.
    NMDs are converted into synthetic Position objects so that calculators
    operate on a homogeneous position representation.

Regulatory context
------------------
The model is designed for Interest Rate Risk in the Banking Book (IRRBB)
analysis under EBA/GL/2022/14. It supports applications such as:

- Economic Value of Equity (EVE)
- Net Interest Income (NII)
- Repricing gap analysis
- Supervisory Outlier Tests (SOT)
- Behavioural modelling of non-maturity deposits

The module intentionally contains no valuation or risk calculations. Its sole
responsibility is to provide validated, reusable balance-sheet data structures
consumed by downstream analytics.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from banking_risk.irrbb.constants import NMD_REPRICING_CAP, NMD_Type, PositionType


@dataclass
class Position:
    """Single banking book position.

    Attributes
    ----------
    name : str
        Unique identifier. Used as index in NII result Series.
    type : PositionType
        Sign convention: ASSET → positive signed_notional.
    currency : str
        ISO 4217 code. Determines which EBA shock scenario applies.
    notional : float
        Outstanding principal, always positive. Sign is encoded in `type`.
    maturity_months : int
        Remaining months to final maturity.
    coupon_months : int
        Coupon payment frequency in months. 0 for zero-coupon / bullet.
    rate : float
        Current rate in decimal (e.g. 0.035 for 3.5 %).
    floating : bool
        True if the rate resets periodically.
    repricing_tenor_months : int
        Reset frequency in months for floating positions (e.g. 3 for 3 M
        EURIBOR). Must be > 0 when floating=True. Ignored for fixed.
    """

    name: str
    type: PositionType
    currency: str
    notional: float
    maturity_months: int
    coupon_months: int
    rate: float
    floating: bool
    repricing_tenor_months: int = 0

    def __post_init__(self) -> None:
        self.type = PositionType(self.type)   # coerce plain string if passed
        if self.notional < 0:
            raise ValueError(
                "notional must be non-negative; encode sign via type=PositionType.LIABILITY"
            )
        if self.floating and self.repricing_tenor_months <= 0:
            raise ValueError(
                "floating positions require repricing_tenor_months > 0"
            )

    @property
    def next_repricing_years(self) -> float:
        """Years until the next rate reset — determines EBA bucket slot.

        Fixed positions do not reprice before maturity; they are slotted at
        their final maturity date. Floating positions are slotted at their
        next repricing date (repricing_tenor_months from now).
        """
        if self.floating:
            return self.repricing_tenor_months / 12.0
        return self.maturity_months / 12.0

    @property
    def signed_notional(self) -> float:
        """Notional with sign: positive for assets, negative for liabilities."""
        return self.notional if self.type == PositionType.ASSET else -self.notional


class Banking_Book(ABC):
    """Abstract banking book — interface consumed by all calculators.

    Implementors supply the position list and balance-sheet totals.
    Calculators depend only on this interface, never on the concrete class.
    """

    @abstractmethod
    def positions(self) -> list[Position]:
        """All interest-rate sensitive positions in the book."""
        ...

    @abstractmethod
    def total_assets(self) -> float:
        """Sum of notionals for all asset positions."""
        ...

    @abstractmethod
    def total_liabilities(self) -> float:
        """Sum of notionals for all liability positions."""
        ...

    @abstractmethod
    def equity(self) -> float:
        """Tier 1 capital — denominator for EVE and NII SOT ratios."""
        ...

    @abstractmethod
    def balance_check(self) -> bool:
        """True if assets ≈ liabilities + equity within rounding tolerance."""
        ...


class Standard_Banking_Book(Banking_Book):
    """Concrete banking book backed by a list of Position objects.

    Parameters
    ----------
    positions : list[Position]
    tier1_capital : float
        Tier 1 capital used as the SOT denominator (must be positive).
    tolerance : float
        Absolute tolerance for balance_check, in currency units. Default 1.0.
    """

    def __init__(
        self,
        positions: list[Position],
        tier1_capital: float,
        tolerance: float = 1.0,
    ) -> None:
        if tier1_capital <= 0:
            raise ValueError("tier1_capital must be positive")
        self._positions = list(positions)
        self._tier1_capital = tier1_capital
        self._tolerance = tolerance

    def positions(self) -> list[Position]:
        return self._positions

    def total_assets(self) -> float:
        return sum(p.notional for p in self._positions if p.type == PositionType.ASSET)

    def total_liabilities(self) -> float:
        return sum(p.notional for p in self._positions if p.type == PositionType.LIABILITY)

    def equity(self) -> float:
        return self._tier1_capital

    def balance_check(self) -> bool:
        gap = abs(self.total_assets() - self.total_liabilities() - self._tier1_capital)
        return gap <= self._tolerance

    @property
    def tier1_capital(self) -> float:
        return self._tier1_capital


# ── NMD data model ────────────────────────────────────────────────────────────

@dataclass
class NMD_Portfolio:
    """A portfolio of non-maturity deposits with behavioural repricing assumptions.

    NMDs have no contractual maturity. Their interest rate sensitivity is
    modelled by splitting volume into a stable (core) and volatile (non-core)
    portion and assigning a behavioural average repricing date to the stable
    portion. EBA/GL/2022/14, Chapter 6.

    Attributes
    ----------
    name : str
        Unique identifier.
    currency : str
        ISO 4217 code.
    volume : float
        Total deposit volume (positive).
    nmd_type : NMD_Type
        Retail or wholesale — determines the EBA repricing cap.
    stable_ratio : float
        Fraction of volume modelled as stable/core deposits (0–1).
    stable_avg_repricing_years : float
        Behavioural average repricing date for the stable portion in years.
        Must not exceed the EBA/GL/2022/14 cap for the deposit type
        (retail ≤ 5Y, wholesale ≤ 4.5Y).
    rate : float
        Current rate paid on deposits in decimal (e.g. 0.01 for 1 %).
    """

    name: str
    currency: str
    volume: float
    nmd_type: NMD_Type
    stable_ratio: float
    stable_avg_repricing_years: float
    rate: float

    def __post_init__(self) -> None:
        self.nmd_type = NMD_Type(self.nmd_type)
        cap = NMD_REPRICING_CAP[self.nmd_type]
        if not 0.0 <= self.stable_ratio <= 1.0:
            raise ValueError("stable_ratio must be in [0, 1]")
        if self.stable_avg_repricing_years > cap:
            raise ValueError(
                f"{self.nmd_type} NMD stable repricing "
                f"{self.stable_avg_repricing_years}Y exceeds "
                f"EBA/GL/2022/14 cap of {cap}Y"
            )
        if self.volume <= 0:
            raise ValueError("volume must be positive")

    @property
    def stable_volume(self) -> float:
        return self.volume * self.stable_ratio

    @property
    def volatile_volume(self) -> float:
        return self.volume * (1 - self.stable_ratio)


# ── NMD banking book ──────────────────────────────────────────────────────────

class NMD_Banking_Book(Banking_Book):
    """Banking book with explicit NMD behavioural modelling.

    Holds regular positions alongside NMD portfolios. The NMD portfolios are
    converted to synthetic Position objects inside positions() so that all
    calculators consume a uniform list without NMD-specific logic.

    Synthetic positions per NMD portfolio
    --------------------------------------
    Volatile portion — short-term floating liability (1M repricing).
        Treated as the nearest approximation to overnight in the current
        Position model. EBA/GL/2022/14 treats non-core NMDs as overnight.
    Stable portion — fixed liability at stable_avg_repricing_years.
        Simplified single-position representation. A more accurate model
        would distribute volume uniformly across buckets up to
        2 × stable_avg_repricing_years to preserve the correct average.

    Parameters
    ----------
    positions : list[Position]
        All non-NMD banking book positions.
    nmd_portfolios : list[NMD_Portfolio]
    tier1_capital : float
    tolerance : float
        Absolute tolerance for balance_check.
    """

    def __init__(
        self,
        positions: list[Position],
        nmd_portfolios: list[NMD_Portfolio],
        tier1_capital: float,
        tolerance: float = 1.0,
    ) -> None:
        if tier1_capital <= 0:
            raise ValueError("tier1_capital must be positive")
        self._positions = list(positions)
        self._nmd_portfolios = list(nmd_portfolios)
        self._tier1_capital = tier1_capital
        self._tolerance = tolerance

    def positions(self) -> list[Position]:
        return self._positions + self._synthetic_nmd_positions()

    def total_assets(self) -> float:
        return sum(p.notional for p in self.positions() if p.type == PositionType.ASSET)

    def total_liabilities(self) -> float:
        return sum(p.notional for p in self.positions() if p.type == PositionType.LIABILITY)

    def equity(self) -> float:
        return self._tier1_capital

    def balance_check(self) -> bool:
        gap = abs(self.total_assets() - self.total_liabilities() - self._tier1_capital)
        return gap <= self._tolerance

    @property
    def tier1_capital(self) -> float:
        return self._tier1_capital

    @property
    def nmd_portfolios(self) -> list[NMD_Portfolio]:
        return self._nmd_portfolios

    def _synthetic_nmd_positions(self) -> list[Position]:
        """Convert NMD portfolios to Position objects for calculator consumption."""
        synthetic: list[Position] = []
        for nmd in self._nmd_portfolios:
            if nmd.volatile_volume > 0:
                synthetic.append(Position(
                    name=f"{nmd.name}_volatile",
                    type=PositionType.LIABILITY,
                    currency=nmd.currency,
                    notional=nmd.volatile_volume,
                    maturity_months=1,
                    coupon_months=0,
                    rate=nmd.rate,
                    floating=True,
                    repricing_tenor_months=1,   # overnight approximated as 1M
                ))
            if nmd.stable_volume > 0:
                stable_months = max(1, round(nmd.stable_avg_repricing_years * 12))
                synthetic.append(Position(
                    name=f"{nmd.name}_stable",
                    type=PositionType.LIABILITY,
                    currency=nmd.currency,
                    notional=nmd.stable_volume,
                    maturity_months=stable_months,
                    coupon_months=0,
                    rate=nmd.rate,
                    floating=False,
                    repricing_tenor_months=0,
                ))
        return synthetic
