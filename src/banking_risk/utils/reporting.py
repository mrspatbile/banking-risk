"""
Reporting infrastructure — styles and reporters.

Style subclasses own the full color palette and typography constants.
Reporter subclasses receive a Style and a result object and produce plots
or DataFrames. No hex values appear anywhere except inside Style subclasses.

Usage
-----
    # Thin notebook usage (result delegates to default reporter):
    result.plot()
    result.to_table()

    # Production usage with explicit style:
    from banking_risk.utils.reporting import EVE_Reporter, Light_Style
    EVE_Reporter(Light_Style()).plot(result)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from banking_risk.irrbb.eve import EVE_Result
    from banking_risk.irrbb.nii import NII_Result

# ── Style ─────────────────────────────────────────────────────────────────────

class Style(ABC):
    """Abstract style — owns all color, size, and typography constants."""

    @property
    @abstractmethod
    def palette(self) -> dict[str, str]:
        """Named color dict. Required keys: bg_primary, text_body, text_title,
        text_muted, border, grid, cyan, green, red, amber."""
        ...

    @property
    @abstractmethod
    def fig_size(self) -> tuple[float, float]:
        """Default figure (width, height) in inches."""
        ...

    @property
    @abstractmethod
    def dpi(self) -> int: ...

    def apply(self) -> None:
        """Push this style into matplotlib rcParams."""
        p = self.palette
        mpl.rcParams.update(
            {
                "figure.figsize":      self.fig_size,
                "figure.dpi":          self.dpi,
                "figure.facecolor":    p["bg_primary"],
                "axes.facecolor":      p["bg_primary"],
                "axes.edgecolor":      p["border"],
                "axes.labelcolor":     p["text_body"],
                "axes.titlecolor":     p["text_title"],
                "axes.titlesize":      12,
                "axes.titleweight":    "bold",
                "axes.labelsize":      10,
                "axes.spines.right":   False,
                "axes.spines.top":     False,
                "xtick.color":         p["text_muted"],
                "ytick.color":         p["text_muted"],
                "text.color":          p["text_body"],
                "legend.facecolor":    p.get("bg_alternate", p["bg_primary"]),
                "legend.edgecolor":    p["border"],
                "legend.fontsize":     9,
                "grid.color":          p["grid"],
                "grid.alpha":          0.4,
                "font.family":         "sans-serif",
            }
        )


@dataclass(frozen=True)
class Dark_Style(Style):
    """Dark background — for screen, presentation, and notebook output."""

    @property
    def palette(self) -> dict[str, str]:
        return {
            "bg_primary":   "#1a1f2e",
            "bg_alternate": "#141929",
            "bg_header":    "#36394F",
            "text_body":    "#a0aec0",
            "text_title":   "#e2e8f0",
            "text_muted":   "#587580",
            "border":       "#2a2f3e",
            "grid":         "#2a2f3e",
            "cyan":         "#00b4d8",
            "green":        "#38ef7d",
            "red":          "#ff6b6b",
            "amber":        "#f9c74f",
            "blue":         "#4299e1",
            "purple":       "#9f7aea",
        }

    @property
    def fig_size(self) -> tuple[float, float]:
        return (14.0, 5.5)

    @property
    def dpi(self) -> int:
        return 120


@dataclass(frozen=True)
class Light_Style(Style):
    """Light background — for print, regulatory submission, PDF export."""

    @property
    def palette(self) -> dict[str, str]:
        return {
            "bg_primary":   "#ffffff",
            "bg_alternate": "#f7f9fc",
            "bg_header":    "#e8edf4",
            "text_body":    "#1a202c",
            "text_title":   "#0d1117",
            "text_muted":   "#718096",
            "border":       "#cbd5e0",
            "grid":         "#e2e8f0",
            "cyan":         "#0077b6",
            "green":        "#276749",
            "red":          "#c53030",
            "amber":        "#b7791f",
            "blue":         "#2b6cb0",
            "purple":       "#553c9a",
        }

    @property
    def fig_size(self) -> tuple[float, float]:
        return (14.0, 5.5)

    @property
    def dpi(self) -> int:
        return 150


# ── Reporter base ─────────────────────────────────────────────────────────────

class Reporter(ABC):
    """Abstract reporter — plot and table output for a result object."""

    def __init__(self, style: Style) -> None:
        self._s = style
        self._p = style.palette

    @abstractmethod
    def plot(self, result) -> None: ...

    @abstractmethod
    def to_table(self, result) -> pd.DataFrame: ...

    def _fig(self, nrows: int = 1, ncols: int = 1, **kw):
        """Create a styled figure/axes pair."""
        self._s.apply()
        return plt.subplots(nrows, ncols, **kw)


# ── EVE Reporter ──────────────────────────────────────────────────────────────

class EVE_Reporter(Reporter):
    """Two-panel plot and summary table for EVE_Result."""

    def plot(self, result: "EVE_Result") -> None:
        """Panel 1: ΔEVE bar per scenario with SOT line.
           Panel 2: base NPV per EBA bucket."""
        p = self._p
        fig, (ax1, ax2) = self._fig(1, 2, figsize=self._s.fig_size)

        # — Panel 1: ΔEVE per scenario —
        names = list(result.delta_eve.keys())
        vals_m = [result.delta_eve[n] / 1e6 for n in names]
        bar_colors = [p["red"] if v > 0 else p["cyan"] for v in vals_m]
        ax1.bar(range(len(names)), vals_m, color=bar_colors, alpha=0.85, width=0.6)
        ax1.axhline(0, color=p["text_muted"], lw=0.8, ls="--")
        ax1.axhline(
            result.tier1_capital * 0.15 / 1e6,
            color=p["amber"], lw=1.2, ls=":", label="SOT 15%",
        )
        ax1.set_xticks(range(len(names)))
        ax1.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
        ax1.set_ylabel("ΔEVE (€M)")
        ax1.set_title("ΔEVE by Scenario", color=p["text_title"])
        ax1.legend(fontsize=8)

        # — Panel 2: base NPV per bucket —
        npv_m = result.npv_base / 1e6
        bucket_colors = [p["cyan"] if v >= 0 else p["red"] for v in npv_m]
        ax2.bar(range(len(npv_m)), npv_m.values, color=bucket_colors, alpha=0.85, width=0.8)
        ax2.axhline(0, color=p["text_muted"], lw=0.8, ls="--")
        ax2.set_xticks(range(len(npv_m)))
        ax2.set_xticklabels(npv_m.index, rotation=45, ha="right", fontsize=7)
        ax2.set_ylabel("NPV (€M)")
        ax2.set_title("Base NPV per Bucket", color=p["text_title"])

        status_color = p["red"] if result.is_outlier else p["green"]
        status = "OUTLIER" if result.is_outlier else "PASS"
        fig.suptitle(
            f"EVE SOT  |  Worst: {result.worst_scenario}  |  "
            f"SOT {result.sot_ratio:.1%}  |  {status}",
            color=status_color, fontweight="bold",
        )
        fig.tight_layout()
        plt.show()

    def to_table(self, result: "EVE_Result") -> pd.DataFrame:
        """One row per scenario: ΔEVE, SOT ratio, outlier flag."""
        rows = [
            {
                "scenario":  name,
                "delta_eve": dv,
                "sot_ratio": dv / result.tier1_capital,
                "outlier":   dv / result.tier1_capital > 0.15,
            }
            for name, dv in result.delta_eve.items()
        ]
        return pd.DataFrame(rows).set_index("scenario")


# ── NII Reporter ──────────────────────────────────────────────────────────────

class NII_Reporter(Reporter):
    """Bar chart and summary table for NII_Result."""

    def plot(self, result: "NII_Result") -> None:
        """ΔNII bars for parallel up and down with SOT threshold lines."""
        p = self._p
        fig, ax = self._fig(figsize=(8.0, 4.5))

        names = list(result.delta_nii.keys())
        vals_m = [result.delta_nii[n] / 1e6 for n in names]
        bar_colors = [p["red"] if v > 0 else p["cyan"] for v in vals_m]

        ax.bar(names, vals_m, color=bar_colors, alpha=0.85, width=0.4)
        ax.axhline(0, color=p["text_muted"], lw=0.8, ls="--")
        threshold_m = result.tier1_capital * 0.05 / 1e6
        ax.axhline(+threshold_m, color=p["amber"], lw=1.2, ls=":", label="SOT ±5%")
        ax.axhline(-threshold_m, color=p["amber"], lw=1.2, ls=":")

        status_color = p["red"] if result.is_outlier else p["green"]
        status = "OUTLIER" if result.is_outlier else "PASS"
        ax.set_title(
            f"NII SOT  |  SOT {result.sot_ratio:.1%}  |  {status}",
            color=status_color, fontweight="bold",
        )
        ax.set_ylabel("ΔNII (€M)")
        ax.legend(fontsize=8)
        fig.tight_layout()
        plt.show()

    def to_table(self, result: "NII_Result") -> pd.DataFrame:
        rows = [
            {
                "scenario":  name,
                "delta_nii": dn,
                "sot_ratio": abs(dn) / result.tier1_capital,
                "outlier":   abs(dn) / result.tier1_capital > 0.05,
            }
            for name, dn in result.delta_nii.items()
        ]
        return pd.DataFrame(rows).set_index("scenario")


# ── Gap Reporter ──────────────────────────────────────────────────────────────

class Gap_Reporter(Reporter):
    """Grouped bar chart and table for repricing gap DataFrames."""

    def plot(self, gap_df: pd.DataFrame) -> None:
        """Assets/liabilities bars on primary axis; cumulative gap line on secondary."""
        p = self._p
        fig, ax1 = self._fig(figsize=self._s.fig_size)
        ax2 = ax1.twinx()

        x = np.arange(len(gap_df))
        w = 0.35
        ax1.bar(x - w / 2, gap_df["assets"] / 1e6, w, color=p["cyan"], alpha=0.75, label="Assets")
        ax1.bar(x + w / 2, gap_df["liabilities"] / 1e6, w, color=p["red"], alpha=0.75, label="Liabilities")
        ax2.plot(
            x, gap_df["cumulative_gap"] / 1e6,
            color=p["amber"], lw=1.8, marker="o", ms=3, label="Cumulative gap",
        )
        ax2.axhline(0, color=p["text_muted"], lw=0.6, ls="--")

        ax1.set_xticks(x)
        ax1.set_xticklabels(gap_df.index, rotation=45, ha="right", fontsize=7)
        ax1.set_ylabel("Notional (€M)", color=p["text_body"])
        ax2.set_ylabel("Cumulative Gap (€M)", color=p["amber"])
        ax1.set_title("Repricing Gap — EBA 19 Buckets", color=p["text_title"], fontweight="bold")

        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper right")
        fig.tight_layout()
        plt.show()

    def to_table(self, gap_df: pd.DataFrame) -> pd.DataFrame:
        return gap_df


# ── GIRR Reporter ─────────────────────────────────────────────────────────────

class GIRR_Reporter(Reporter):
    """Bar chart and summary table for GIRR_Result and GIRR_Vega_Result."""

    def to_table(self, result) -> pd.DataFrame:
        from banking_risk.frtb.girr.delta import GIRR_Result
        from banking_risk.frtb.girr.vega import GIRR_Vega_Result
        if isinstance(result, GIRR_Result):
            return self._delta_table(result)
        if isinstance(result, GIRR_Vega_Result):
            return self._vega_table(result)
        raise TypeError(f"Unsupported result type: {type(result)}")

    def _delta_table(self, result) -> pd.DataFrame:
        df = pd.DataFrame(result.ws)
        df.loc["K"] = result.K
        df.loc["S"] = result.S
        return df

    def _vega_table(self, result) -> pd.DataFrame:
        from banking_risk.frtb.constants import GIRR_VEGA_LABELS
        n = len(GIRR_VEGA_LABELS)
        frames: dict[str, pd.DataFrame] = {}
        for ccy in result.currencies:
            ws_flat = result.ws[ccy].values
            frames[ccy] = pd.DataFrame(
                ws_flat.reshape(n, n),
                index=pd.Index(GIRR_VEGA_LABELS, name="expiry"),
                columns=pd.Index(GIRR_VEGA_LABELS, name="tenor"),
            )
        if len(frames) == 1:
            return next(iter(frames.values()))
        return pd.concat(frames, axis=1)

    def plot(self, result) -> None:
        from banking_risk.frtb.girr.delta import GIRR_Result
        from banking_risk.frtb.girr.vega import GIRR_Vega_Result
        if isinstance(result, GIRR_Result):
            self._delta_plot(result)
        elif isinstance(result, GIRR_Vega_Result):
            self._vega_plot(result)
        else:
            raise TypeError(f"Unsupported result type: {type(result)}")

    def _delta_plot(self, result) -> None:
        p = self._p
        currencies = result.currencies
        n = len(currencies)
        fig, axes = self._fig(1, n, figsize=(max(10, 6 * n), 5))
        if n == 1:
            axes = [axes]
        for ax, ccy in zip(axes, currencies):
            ws = result.ws[ccy]
            colors = [p["cyan"] if v >= 0 else p["red"] for v in ws.values]
            ax.bar(range(len(ws)), ws.values, color=colors, alpha=0.85, width=0.6)
            ax.axhline(0, color=p["text_muted"], lw=0.8, ls="--")
            k = result.K[ccy]
            ax.axhline(k, color=p["amber"], lw=1.2, ls=":", label=f"K={k:.2f}")
            ax.axhline(-k, color=p["amber"], lw=1.2, ls=":")
            ax.set_xticks(range(len(ws)))
            ax.set_xticklabels(ws.index, rotation=45, ha="right", fontsize=8)
            ax.set_title(f"GIRR delta WS — {ccy}", color=p["text_title"])
            ax.set_ylabel("WS (sensitivity × risk weight)")
            ax.legend(fontsize=8)
        fig.suptitle(
            f"GIRR Delta Capital: {result.capital:.4f}",
            color=p["text_title"], fontweight="bold",
        )
        fig.tight_layout()
        plt.show()

    def _vega_plot(self, result) -> None:
        p = self._p
        currencies = result.currencies
        n_ccy = len(currencies)
        from banking_risk.frtb.constants import GIRR_VEGA_LABELS
        n = len(GIRR_VEGA_LABELS)
        fig, axes = self._fig(1, n_ccy, figsize=(6 * n_ccy, 5))
        if n_ccy == 1:
            axes = [axes]
        for ax, ccy in zip(axes, currencies):
            mat = result.ws[ccy].values.reshape(n, n)
            im = ax.imshow(mat, aspect="auto", cmap="RdYlGn_r")
            ax.set_xticks(range(n))
            ax.set_yticks(range(n))
            ax.set_xticklabels(GIRR_VEGA_LABELS, fontsize=8)
            ax.set_yticklabels(GIRR_VEGA_LABELS, fontsize=8)
            ax.set_xlabel("Tenor")
            ax.set_ylabel("Expiry")
            ax.set_title(f"GIRR vega WS — {ccy}", color=p["text_title"])
            fig.colorbar(im, ax=ax, shrink=0.8)
        fig.suptitle(
            f"GIRR Vega Capital: {result.capital:.4f}",
            color=p["text_title"], fontweight="bold",
        )
        fig.tight_layout()
        plt.show()
