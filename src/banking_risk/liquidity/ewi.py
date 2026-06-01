"""
Early Warning Indicators (EWI) and Liquidity Contingency Plan triggers.

EWIs are forward-looking metrics that signal deteriorating liquidity
before a crisis materialises. Monitoring EWIs allows management to
activate the Contingency Funding Plan (CFP) at the earliest opportunity.

Each indicator has three thresholds defining a traffic-light status:
  Green  : normal operating range
  Amber  : elevated risk — management action required
  Red    : stressed — CFP escalation triggered

The overall dashboard status is the worst individual indicator status.

References
----------
EBA/GL/2019/02   : Internal governance — liquidity risk, §§ 78–88
EBA/GL/2021/01   : ILAAP — EWI monitoring and CFP triggers
"""

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


# ── Status ────────────────────────────────────────────────────────────────────

class EWI_Status(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"


_STATUS_ORDER = {EWI_Status.GREEN: 0, EWI_Status.AMBER: 1, EWI_Status.RED: 2}


# ── Indicator definition ──────────────────────────────────────────────────────

@dataclass
class EWI:
    """A single early warning indicator.

    Parameters
    ----------
    name : str
    value : float
        Current observed value of the metric.
    green_threshold : float
        Boundary between green and amber.
    amber_threshold : float
        Boundary between amber and red.
    direction : str
        'above_is_bad'  — higher values signal more risk (e.g. encumbrance %).
        'below_is_bad'  — lower values signal more risk (e.g. LCR, NSFR).
    description : str, optional
        Human-readable description of the indicator.
    """

    name             : str
    value            : float
    green_threshold  : float
    amber_threshold  : float
    direction        : str            # "above_is_bad" or "below_is_bad"
    description      : str = ""

    def __post_init__(self) -> None:
        if self.direction not in ("above_is_bad", "below_is_bad"):
            raise ValueError(
                f"direction must be 'above_is_bad' or 'below_is_bad', "
                f"got '{self.direction}'"
            )

    @property
    def status(self) -> EWI_Status:
        if self.direction == "below_is_bad":
            if self.value >= self.green_threshold:
                return EWI_Status.GREEN
            if self.value >= self.amber_threshold:
                return EWI_Status.AMBER
            return EWI_Status.RED
        else:  # above_is_bad
            if self.value <= self.green_threshold:
                return EWI_Status.GREEN
            if self.value <= self.amber_threshold:
                return EWI_Status.AMBER
            return EWI_Status.RED


# ── Standard indicators ───────────────────────────────────────────────────────
# Factory functions to construct typical bank EWIs from computed values.

def lcr_indicator(lcr_ratio: float) -> EWI:
    """LCR — regulatory minimum 100%; internal buffer target typically ≥ 130%."""
    return EWI(
        name="LCR",
        value=lcr_ratio * 100,
        green_threshold=130,
        amber_threshold=100,
        direction="below_is_bad",
        description="Liquidity Coverage Ratio (%)",
    )


def nsfr_indicator(nsfr_ratio: float) -> EWI:
    """NSFR — regulatory minimum 100%; internal target ≥ 110%."""
    return EWI(
        name="NSFR",
        value=nsfr_ratio * 100,
        green_threshold=110,
        amber_threshold=100,
        direction="below_is_bad",
        description="Net Stable Funding Ratio (%)",
    )


def encumbrance_indicator(enc_ratio: float) -> EWI:
    """Asset encumbrance ratio — high encumbrance limits contingency capacity."""
    return EWI(
        name="Encumbrance ratio",
        value=enc_ratio * 100,
        green_threshold=30,
        amber_threshold=50,
        direction="above_is_bad",
        description="Encumbered assets / total assets (%)",
    )


def rollover_indicator(rollover_ratio_30d: float) -> EWI:
    """30-day rollover ratio — short-term funding concentration risk."""
    return EWI(
        name="30D rollover ratio",
        value=rollover_ratio_30d * 100,
        green_threshold=15,
        amber_threshold=25,
        direction="above_is_bad",
        description="Liabilities maturing in 30 days / total liabilities (%)",
    )


def intraday_utilisation_indicator(utilisation: float) -> EWI:
    """Intraday utilisation — high usage may signal intraday liquidity stress."""
    return EWI(
        name="Intraday utilisation",
        value=utilisation * 100,
        green_threshold=50,
        amber_threshold=75,
        direction="above_is_bad",
        description="Max intraday usage / available intraday liquidity (%)",
    )


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class EWI_Dashboard:
    """Output of EWI_Monitor.evaluate().

    Attributes
    ----------
    indicators : pd.DataFrame
        name, value, green_threshold, amber_threshold, status, description.
    green_count, amber_count, red_count : int
    overall_status : EWI_Status
        Worst individual indicator status.
    """

    indicators     : pd.DataFrame
    green_count    : int
    amber_count    : int
    red_count      : int
    overall_status : EWI_Status


# ── Monitor ───────────────────────────────────────────────────────────────────

class EWI_Monitor:
    """Evaluate a set of EWIs and produce a traffic-light dashboard."""

    def evaluate(self, indicators: list[EWI]) -> EWI_Dashboard:
        rows = []
        for ind in indicators:
            rows.append(
                {
                    "name"             : ind.name,
                    "value"            : ind.value,
                    "green_threshold"  : ind.green_threshold,
                    "amber_threshold"  : ind.amber_threshold,
                    "direction"        : ind.direction,
                    "status"           : ind.status.value,
                    "description"      : ind.description,
                }
            )

        df     = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["name", "value", "green_threshold", "amber_threshold",
                     "direction", "status", "description"]
        )
        counts = df["status"].value_counts().to_dict() if not df.empty else {}
        green  = int(counts.get("green", 0))
        amber  = int(counts.get("amber", 0))
        red    = int(counts.get("red",   0))

        statuses = [ind.status for ind in indicators]
        overall  = max(statuses, key=lambda s: _STATUS_ORDER[s]) if statuses else EWI_Status.GREEN

        return EWI_Dashboard(
            indicators=df,
            green_count=green,
            amber_count=amber,
            red_count=red,
            overall_status=overall,
        )
