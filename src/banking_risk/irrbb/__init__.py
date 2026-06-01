"""
banking_risk.irrbb — public API.

Import everything a notebook needs from here. Internal modules (constants,
curves internals) are available directly if needed for advanced use.
"""

from banking_risk.irrbb.book import (
    Banking_Book,
    NMD_Banking_Book,
    NMD_Portfolio,
    Position,
    Standard_Banking_Book,
)
from banking_risk.shared.curves import QL_Curve_Adapter, Zero_Curve
from banking_risk.irrbb.eve import EVE_Calculator, EVE_Result, SA_EVE_Calculator
from banking_risk.irrbb.gap import Repricing_Gap
from banking_risk.irrbb.nii import NII_Calculator, NII_Result, SA_NII_Calculator
from banking_risk.irrbb.scenarios import (
    Flattener,
    Parallel_Down,
    Parallel_Up,
    Scenario_Set,
    Shock_Scenario,
    Short_Rate_Down,
    Short_Rate_Up,
    Steepener,
)

__all__ = [
    # data
    "Position",
    "Banking_Book",
    "Standard_Banking_Book",
    "NMD_Portfolio",
    "NMD_Banking_Book",
    # curves
    "Zero_Curve",
    "QL_Curve_Adapter",
    # scenarios
    "Shock_Scenario",
    "Parallel_Up",
    "Parallel_Down",
    "Short_Rate_Up",
    "Short_Rate_Down",
    "Steepener",
    "Flattener",
    "Scenario_Set",
    # calculators
    "EVE_Result",
    "EVE_Calculator",
    "SA_EVE_Calculator",
    "NII_Result",
    "NII_Calculator",
    "SA_NII_Calculator",
    "Repricing_Gap",
]
