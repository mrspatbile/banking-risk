# src/banking_risk/utils/style.py

# -----------------------------------------------------------------------
# notebook setup -- call at top of every notebook
# from banking_risk.utils.style import base
# np, pd, plt = base()
# -----------------------------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np


def apply_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    mpl.rcParams.update({
        "figure.figsize"    : (12, 5),
        "figure.dpi"        : 120,
        "axes.spines.right" : False,
        "axes.spines.top"   : False,
        "axes.titlesize"    : 12,
        "axes.titleweight"  : "bold",
        "axes.labelsize"    : 10,
        "font.family"       : "sans-serif",
        "legend.frameon"    : True,
        "legend.facecolor"  : "white",
        "legend.edgecolor"  : "white",
        "legend.fontsize"   : 9,
    })


def base():
    """Standard notebook setup — call at top of every notebook."""
    apply_style()
    pd.set_option("display.float_format", "{:.6f}".format)
    pd.set_option("display.max_columns", 20)
    return np, pd, plt
