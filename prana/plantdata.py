"""Plant energy-sheet loader — turns a real site's meter log into twin inputs.

WHY THIS EXISTS. Every parameter in `twins.py` was, until now, chosen rather
than measured. This module is the other end: give it a plant's own energy
sheet and it returns the subset of those parameters that the sheet can
honestly support, plus an explicit statement of what it CANNOT support.

THE DESIGN RULE THAT MATTERS: this module is **column-map driven**. It knows
nothing about any particular plant. You hand it a mapping from your sheet's
column names to the canonical roles below, and it works. A loader that only
works on the one sheet it was written against is not a loader, it is a
transcription — and it is how a model gets overfitted to its first site.

Canonical roles (all optional except `date` and at least one load column):

    date            timestamp of the reading
    site_total      total electrical energy supplied to the site
    grid_import     energy imported from the utility  <- the PRANA-exposed part
    captive         list of on-site generation columns (GT, ST, DG, solar)
    isbl            in-battery-limits process consumption
    osbl            outside-battery-limits / utilities consumption
    units           dict of {unit name: column} for individual process units

VALIDITY IS DECLARED, NOT TUNED. A day is used only if every mapped column is
finite and non-negative, the site total sits within `scale_band` of the record
median (this is what rejects cumulative-meter rollovers, which appear as
values orders of magnitude out), and — where both sides are mapped — the
energy balance closes to within `balance_tol`. Rejected days are counted and
reported, never silently dropped or interpolated. If you cannot say why a row
was excluded, you do not have a dataset, you have an opinion.

WHAT A METER SHEET CAN AND CANNOT GROUND. Read this before quoting anything:

  CAN:  site electrical load and its variability; the grid-exposed fraction
        (the only part PRANA's market layer acts on); the ISBL/OSBL split;
        per-unit electrical load; captive-vs-import mix.
  CANNOT: the power curve P(q), specific energy consumption, turndown,
        minimum stable load, ramp rate, or buffer size. Every one of those
        needs PRODUCTION RATE alongside energy, and a meter sheet has no
        production column. Daily readings additionally cannot ground any
        intraday claim, because PRANA dispatches 96 blocks and a daily total
        is one number.

`PlantProfile.cannot_ground` returns that second list at runtime so it ends up
in front of whoever reads the output, rather than in a docstring nobody opens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HOURS_PER_DAY = 24.0


@dataclass
class ColumnMap:
    """How one plant's sheet maps onto the canonical roles."""

    date: str
    site_total: str | None = None
    grid_import: str | None = None
    captive: tuple[str, ...] = ()
    isbl: str | None = None
    osbl: str | None = None
    units: dict[str, str] = field(default_factory=dict)

    def energy_columns(self) -> list[str]:
        cols = [self.site_total, self.grid_import, self.isbl, self.osbl]
        cols += list(self.captive) + list(self.units.values())
        return [c for c in cols if c]


@dataclass
class PlantProfile:
    """What a real meter sheet supports — and what it does not."""

    name: str
    span: tuple[pd.Timestamp, pd.Timestamp]
    n_rows: int
    n_used: int
    reject_reasons: dict[str, int]
    period_hours: float                 # hours each row represents
    load_mw: dict[str, float]           # role -> mean MW
    load_p10_p90: dict[str, tuple[float, float]]
    load_cv: dict[str, float]
    grid_share: float | None
    days_zero_import: float | None

    @property
    def coverage(self) -> float:
        return self.n_used / self.n_rows if self.n_rows else 0.0

    @property
    def exposed_mw(self) -> float:
        """Average load actually exposed to the market. PRANA acts on this and
        nothing else — a site that self-generates has little for us to do."""
        return self.load_mw.get("grid_import", 0.0)

    def cannot_ground(self) -> list[str]:
        """Stated at runtime so it travels with the numbers."""
        out = [
            "power curve P(q) / coefficients — needs production rate, absent",
            "specific energy consumption — needs production rate, absent",
            "minimum stable load / turndown — needs production rate, absent",
            "buffer size and inventory dynamics — needs a level or stock log",
        ]
        if self.period_hours >= 12.0:
            out.append(
                f"ANY intraday behaviour, incl. ramp rate — readings are "
                f"{self.period_hours:.0f} h apart; PRANA dispatches 96 blocks/day"
            )
        else:
            out.append("ramp rate — needs a observed load-change event log")
        return out

    def grounds(self) -> list[str]:
        out = [f"site electrical load: {self.load_mw.get('site_total', float('nan')):.2f} MW mean"]
        if self.grid_share is not None:
            out.append(f"grid-exposed fraction: {self.grid_share:.1%} of supply")
        if "osbl" in self.load_mw:
            out.append(f"OSBL (non-flexible base) load: {self.load_mw['osbl']:.2f} MW")
        for u in self.units_measured():
            out.append(f"unit load '{u}': {self.load_mw[u]:.2f} MW mean")
        return out

    def units_measured(self) -> list[str]:
        known = {"site_total", "grid_import", "isbl", "osbl", "captive"}
        return [k for k in self.load_mw if k not in known]

    def as_site_inputs(self) -> dict[str, float]:
        """The handful of SiteConfig numbers a meter sheet legitimately sets."""
        return {
            "base_load_mw": round(self.load_mw.get("osbl", float("nan")), 2),
            "exposed_load_mw": round(self.exposed_mw, 2),
            "site_load_mw": round(self.load_mw.get("site_total", float("nan")), 2),
        }


def load_plant_sheet(
    path: str | Path,
    cmap: ColumnMap,
    sheet: str | int = 0,
    header: int = 0,
    name: str = "unnamed site",
    scale_band: tuple[float, float] = (0.3, 3.0),
    balance_tol: float = 0.10,
) -> PlantProfile:
    """Read any plant energy sheet through `cmap` and report what it supports.

    `scale_band` rejects cumulative-meter rollovers relative to the record
    median. `balance_tol` is the fraction by which ISBL+OSBL may miss the site
    total before the row is rejected. Both are arguments, not constants, so a
    site with different instrumentation can be loaded without editing code.
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet, header=header)
    else:
        df = pd.read_csv(path, header=header)
    df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in [cmap.date] + cmap.energy_columns() if c not in df.columns]
    if missing:
        raise KeyError(f"columns not in sheet: {missing}. Present: {list(df.columns)[:25]}")

    df[cmap.date] = pd.to_datetime(df[cmap.date], errors="coerce")
    df = df.dropna(subset=[cmap.date]).sort_values(cmap.date).reset_index(drop=True)
    n_rows = len(df)
    if n_rows < 2:
        raise ValueError("need at least two dated rows")

    cols = cmap.energy_columns()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Reading interval, from the data rather than assumed.
    period_h = float(np.median(np.diff(df[cmap.date].values).astype("timedelta64[m]")
                               .astype(float)) / 60.0)
    if not np.isfinite(period_h) or period_h <= 0:
        period_h = HOURS_PER_DAY

    reasons: dict[str, int] = {}
    keep = pd.Series(True, index=df.index)

    bad = df[cols].isna().any(axis=1)
    reasons["missing value"] = int((bad & keep).sum()); keep &= ~bad

    bad = (df[cols] < 0).any(axis=1)
    reasons["negative energy"] = int((bad & keep).sum()); keep &= ~bad

    ref = cmap.site_total or cmap.grid_import or cols[0]
    med = float(df.loc[keep, ref].median())
    if np.isfinite(med) and med > 0:
        bad = ~df[ref].between(scale_band[0] * med, scale_band[1] * med)
        reasons["out of plant scale (meter rollover)"] = int((bad & keep).sum())
        keep &= ~bad

    if cmap.site_total and cmap.isbl and cmap.osbl:
        tot = df[cmap.site_total].replace(0, np.nan)
        err = (df[cmap.isbl] + df[cmap.osbl] - df[cmap.site_total]).abs() / tot.abs()
        bad = ~(err <= balance_tol)
        reasons[f"energy balance off >{balance_tol:.0%}"] = int((bad & keep).sum())
        keep &= ~bad

    g = df[keep]
    if g.empty:
        raise ValueError(f"no rows survived validity rules: {reasons}")

    def mw(col: str) -> pd.Series:
        return g[col] / period_h

    roles: dict[str, str] = {}
    if cmap.site_total: roles["site_total"] = cmap.site_total
    if cmap.grid_import: roles["grid_import"] = cmap.grid_import
    if cmap.isbl: roles["isbl"] = cmap.isbl
    if cmap.osbl: roles["osbl"] = cmap.osbl
    roles.update(cmap.units)

    load_mw, p1090, cv = {}, {}, {}
    for role, col in roles.items():
        s = mw(col)
        load_mw[role] = float(s.mean())
        p1090[role] = (float(s.quantile(0.10)), float(s.quantile(0.90)))
        cv[role] = float(s.std() / s.mean()) if s.mean() else float("nan")
    if cmap.captive:
        s = g[list(cmap.captive)].sum(axis=1) / period_h
        load_mw["captive"] = float(s.mean())
        p1090["captive"] = (float(s.quantile(0.10)), float(s.quantile(0.90)))
        cv["captive"] = float(s.std() / s.mean()) if s.mean() else float("nan")

    grid_share = days_zero = None
    if cmap.grid_import and cmap.site_total:
        tot = float(g[cmap.site_total].sum())
        grid_share = float(g[cmap.grid_import].sum() / tot) if tot else None
        days_zero = float((g[cmap.grid_import] == 0).mean())

    return PlantProfile(
        name=name,
        span=(g[cmap.date].min(), g[cmap.date].max()),
        n_rows=n_rows,
        n_used=int(keep.sum()),
        reject_reasons={k: v for k, v in reasons.items() if v},
        period_hours=period_h,
        load_mw=load_mw,
        load_p10_p90=p1090,
        load_cv=cv,
        grid_share=grid_share,
        days_zero_import=days_zero,
    )


def report(p: PlantProfile) -> str:
    """Human-readable summary, grounds and non-grounds together."""
    L = [f"PLANT PROFILE — {p.name}",
         f"  span            {p.span[0].date()} -> {p.span[1].date()}",
         f"  rows used       {p.n_used:,} of {p.n_rows:,} ({p.coverage:.0%})",
         f"  reading interval{p.period_hours:>6.1f} h"]
    if p.reject_reasons:
        L.append("  rejected:")
        for k, v in p.reject_reasons.items():
            L.append(f"      {v:>6,}  {k}")
    L.append("  load (MW):")
    for role in p.load_mw:
        lo, hi = p.load_p10_p90[role]
        L.append(f"      {role:<14} {p.load_mw[role]:>7.2f}   p10 {lo:>6.2f}  "
                 f"p90 {hi:>6.2f}   cv {p.load_cv[role]:.2f}")
    if p.grid_share is not None:
        L.append(f"  grid-exposed    {p.grid_share:.1%} of supply "
                 f"({p.exposed_mw:.2f} MW avg); zero-import rows {p.days_zero_import:.0%}")
    L.append("  GROUNDS:")
    L += [f"      + {x}" for x in p.grounds()]
    L.append("  CANNOT GROUND:")
    L += [f"      - {x}" for x in p.cannot_ground()]
    return "\n".join(L)
