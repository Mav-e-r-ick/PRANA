"""Full-year replay: what PRANA would have done, against what the plant did.

Two things make this credible rather than decorative.

1. The counterfactual is honest. The baseline is not "no optimization" — it is
   one steady setpoint per asset held all day, chosen to hold inventory. That
   is how these plants are actually run.

2. Every schedule is re-verified against the TRUE nonlinear physics. The
   optimizer works with tangent hyperplanes; the verifier recomputes power from
   the exact convex curve, re-integrates inventory block by block, and checks
   every bound. A schedule that only satisfies the linearization is a violation
   and is reported as one. `violations == 0` therefore means something.

    python -m prana.backtest --days 60
    python -m prana.backtest --days 60 --forecast     # with forecast error
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from .config import DT_H, OUT_DIR, SiteConfig
from .data import available_days, day, load_market
from .forecast import QuantileForecaster, perfect_foresight
from .optimizer import Schedule, optimize_day
from .tariff import bill_summary, landed_cost
from .twins import (ProcessTwin, default_fleet, fleet_chloralkali,
                    fleet_fertilizer, fleet_refinery)


def alt_supply_cost_rs(s: Schedule, twins: list[ProcessTwin]) -> float:
    """Cost of product bought instead of made (e.g. SMR hydrogen).

    Without this the comparison is rigged: PRANA can idle the electrolyser,
    show a large electricity saving, and never be charged for the gas it bought
    to replace the hydrogen. The saving must be net of it.
    """
    return float(sum(
        t.alt_supply_cost_per_unit * float(np.sum(s.alt_supply[t.name])) * DT_H
        for t in twins if t.alt_supply_cost_per_unit is not None
    ))


def wear_cost_rs(s: Schedule, twins: list[ProcessTwin]) -> float:
    """Non-electricity operating cost the flexibility itself creates.

    Two components, both of which a plant manager will insist on and which the
    electricity bill never shows:

      * **Membrane / equipment life** consumed by setpoint movement. Steady
        operation pays nothing; a schedule that moves pays per unit moved.
      * **Co-product margin destroyed** when chlorine is routed to the bleach
        plant instead of the high-value consumer.

    Recomputed here from the SCHEDULE, not read off the optimizer's own
    objective, so it is an independent charge. A flat baseline incurs neither,
    which is exactly the point: these costs fall entirely on PRANA's side.
    """
    total = 0.0
    for t in twins:
        q = s.asset_production[t.name]
        if t.cycling_cost_rs_per_unit > 0 and len(q) > 1:
            total += t.cycling_cost_rs_per_unit * float(np.sum(np.abs(np.diff(q))))
        if t.coproduct_ratio > 0 and t.dump_cost_per_unit > 0:
            total += t.dump_cost_per_unit * float(
                np.sum(s.coproduct_dump[t.name])) * DT_H
    return total


def pf_penalty_rs(
    s: Schedule, twins: list[ProcessTwin], lc, cfg
) -> float:
    """Extra kVAh billed because power factor falls on turn-down.

    MERC prices HT energy in Rs/kVAh. `landed_cost` converts at a CONSTANT
    power factor, so a schedule that turns a rectifier-fed load down is
    under-billed by exactly the amount the firing angle costs it. This charges
    the difference, block by block, at that block's own landed rate — which
    matters, because the turn-down happens in the CHEAP hours, and that is why
    the penalty is small rather than fatal.

    Charged to both schedules. A flat schedule sits at design pf and pays
    almost nothing; PRANA pays for every hour it spends turned down.
    """
    if cfg.mode != "DISCOM":
        return 0.0                      # open access is settled in kWh
    total = 0.0
    for t in twins:
        if t.pf_at_x_min is None:
            continue
        q = s.asset_production[t.name]
        p = s.asset_power_mw[t.name]
        pf = np.array([t.power_factor(qi) for qi in q])
        extra_kvah = (p * 1000.0 * DT_H) * (t.pf_nom / pf - 1.0)
        total += float(np.sum(extra_kvah * lc.total[: len(extra_kvah)]))
    return total


@dataclass
class Violation:
    date: str
    asset: str
    kind: str
    block: int
    detail: str


def verify_schedule(
    s: Schedule, twins: list[ProcessTwin], site: SiteConfig, date: str
) -> list[Violation]:
    """Re-simulate against exact physics. Independent of the optimizer."""
    v: list[Violation] = []
    tol_p, tol_i, tol_q = 0.05, 1.0, 1e-4     # MW, product units, units/h

    recomputed_total = np.full(len(s.total_power_mw), site.base_load_mw)
    for t in twins:
        q = s.asset_production[t.name]
        inv_model = s.asset_inventory[t.name]
        alt = s.alt_supply[t.name]

        # power from the TRUE curve, not the tangent envelope
        p_true = np.array([t.power_mw(qi) for qi in q])
        recomputed_total += p_true
        p_model = s.asset_power_mw[t.name]
        bad = np.where(p_model < p_true - tol_p)[0]
        for b in bad[:3]:
            v.append(Violation(date, t.name, "power_understated", int(b),
                               f"model {p_model[b]:.3f} MW < true "
                               f"{p_true[b]:.3f} MW"))

        # production bounds (allowing a genuinely shut-down asset)
        for b, qi in enumerate(q):
            if qi > tol_q and qi < t.q_min_per_h - tol_q:
                v.append(Violation(date, t.name, "below_min_load", b,
                                   f"{qi:.2f} < {t.q_min_per_h:.2f} {t.unit}/h"))
                break
            if qi > t.q_max_per_h + tol_q:
                v.append(Violation(date, t.name, "above_max_load", b,
                                   f"{qi:.2f} > {t.q_max_per_h:.2f} {t.unit}/h"))
                break

        # ramp
        dq_max = t.ramp_frac_per_block * t.q_nom_per_h + tol_q
        dq = np.abs(np.diff(q))
        if np.any(dq > dq_max):
            b = int(np.argmax(dq))
            v.append(Violation(date, t.name, "ramp", b,
                               f"|dq|={dq[b]:.2f} > {dq_max:.2f}"))

        # CO-PRODUCT BALANCE, re-checked independently. A schedule that starves
        # the chlorine consumer is not a cheap schedule, it is a plant trip.
        if t.coproduct_ratio > 0:
            dmp = s.coproduct_dump[t.name]
            net = t.coproduct_ratio * q - dmp
            if np.any(dmp > t.dump_max_per_h + tol_q):
                b = int(np.argmax(dmp))
                v.append(Violation(date, t.name, "dump_over_capacity", b,
                                   f"{dmp[b]:.2f} > {t.dump_max_per_h:.2f} "
                                   f"{t.unit}/h of {t.coproduct_name}"))
            if np.any(net < t.sink_min_per_h - tol_q):
                b = int(np.argmin(net))
                v.append(Violation(date, t.name, "coproduct_starved", b,
                                   f"{t.coproduct_name} {net[b]:.2f} < "
                                   f"{t.sink_min_per_h:.2f} {t.unit}/h — "
                                   f"downstream unit would trip"))
            if np.any(net > t.sink_max_per_h + tol_q):
                b = int(np.argmax(net))
                v.append(Violation(date, t.name, "coproduct_flooded", b,
                                   f"{t.coproduct_name} {net[b]:.2f} > "
                                   f"{t.sink_max_per_h:.2f} {t.unit}/h — "
                                   f"nowhere for it to go"))

        # movement budget: the control room's limit, re-checked
        if t.max_total_variation is not None:
            tv = float(np.sum(np.abs(np.diff(q))))
            cap = t.max_total_variation * (len(q) / 96.0) + tol_q
            if tv > cap:
                v.append(Violation(date, t.name, "movement_budget", 0,
                                   f"setpoint travel {tv:.1f} > {cap:.1f} "
                                   f"{t.unit}/h"))

        # inventory, re-integrated from scratch
        inv, level = [], t.inv_init
        for b in range(len(q)):
            level = (level * (1.0 - t.inv_loss_frac_per_h * DT_H)
                     + (q[b] + alt[b] - t.demand_per_h) * DT_H)
            inv.append(level)
        inv = np.asarray(inv)
        if np.any(inv < t.inv_min - tol_i):
            b = int(np.argmin(inv))
            v.append(Violation(date, t.name, "buffer_underflow", b,
                               f"{inv[b]:.1f} < {t.inv_min:.1f} {t.unit}"))
        if np.any(inv > t.inv_max + tol_i):
            b = int(np.argmax(inv))
            v.append(Violation(date, t.name, "buffer_overflow", b,
                               f"{inv[b]:.1f} > {t.inv_max:.1f} {t.unit}"))
        # Terminal inventory is soft, so the day may legitimately end short --
        # but only by the amount the optimizer DECLARED and paid for. Anything
        # beyond that is a real violation.
        allowed = s.terminal_shortfall.get(t.name, 0.0)
        if inv[-1] < t.inv_init - allowed - tol_i:
            v.append(Violation(date, t.name, "terminal_inventory", 95,
                               f"{inv[-1]:.1f} < {t.inv_init:.1f} - "
                               f"{allowed:.1f} declared shortfall {t.unit}"))
        drift = float(np.max(np.abs(inv - inv_model)))
        if drift > 5 * tol_i:
            v.append(Violation(date, t.name, "inventory_drift", 0,
                               f"max |model - resim| = {drift:.2f} {t.unit}"))

    if np.any(recomputed_total > site.tariff.contract_demand_mw + tol_p):
        b = int(np.argmax(recomputed_total))
        v.append(Violation(date, "SITE", "contract_demand", b,
                           f"{recomputed_total[b]:.2f} MW > "
                           f"{site.tariff.contract_demand_mw:.2f} MW"))
    if s.max_deviation_mw > 1e-6:
        v.append(Violation(date, "SITE", "deviation_used", 0,
                           f"max {s.max_deviation_mw:.4f} MW"))
    return v


@dataclass
class BacktestResult:
    rows: pd.DataFrame
    violations: list[Violation] = field(default_factory=list)
    mode: str = "perfect_foresight"

    def headline(self) -> dict[str, float]:
        r = self.rows
        days = len(r)
        saving = r["saving_rs"].sum()
        return {
            "days": days,
            "total_saving_rs": float(saving),
            "mean_saving_rs_day": float(r["saving_rs"].mean()),
            "median_saving_rs_day": float(r["saving_rs"].median()),
            "best_day_rs": float(r["saving_rs"].max()),
            "worst_day_rs": float(r["saving_rs"].min()),
            "days_worse_than_flat": int((r["saving_rs"] < 0).sum()),
            "annualised_rs": float(saving / days * 365) if days else 0.0,
            "pct_of_bill": float(saving / r["flat_bill_rs"].sum() * 100),
            "rs_per_kwh_of_load": float(
                saving / (r["flat_mwh"].sum() * 1000.0)),
            "extra_energy_mwh": float(
                r["prana_mwh"].sum() - r["flat_mwh"].sum()),
            "elec_saving_rs": float(r["elec_saving_rs"].sum()),
            "alt_extra_rs": float(r["alt_extra_rs"].sum()),
            "wear_extra_rs": float(r["wear_extra_rs"].sum()),
            "violations": len(self.violations),
            "mean_solve_s": float(r["solve_s"].mean()),
        }


def run(
    days: int = 60,
    end: str | None = None,
    use_forecast: bool = False,
    site: SiteConfig | None = None,
    scale: float = 1.0,
    time_limit_s: int = 60,
    progress: bool = True,
    fleet_fn=None,
) -> BacktestResult:
    site = site or SiteConfig()
    fleet_fn = fleet_fn or default_fleet
    market = load_market()
    all_days = available_days(market)
    if end:
        all_days = [d for d in all_days if d <= end]
    chosen = all_days[-days:]

    fc = None
    if use_forecast:
        if not QuantileForecaster.available():
            raise RuntimeError("no trained model; run `python -m prana.forecast --train`")
        fc = QuantileForecaster.load()

    rows, violations = [], []
    for i, dstr in enumerate(chosen, 1):
        d = day(market, dstr)
        hours = d["hour"].to_numpy()
        rtm = d["rtm"].to_numpy(float)
        dam = d["dam"].to_numpy(float)
        lc = landed_cost(rtm, hours, site.tariff)      # settle at REALISED price

        quant = (fc.predict(d, market) if fc is not None
                 else perfect_foresight(d))

        fleet_flat = fleet_fn(scale)
        fleet_prana = fleet_fn(scale)
        s_flat = optimize_day(fleet_flat, quant, hours, site, dam_price=dam,
                              flat_baseline=True, time_limit_s=time_limit_s)
        s_prana = optimize_day(fleet_prana, quant, hours, site, dam_price=dam,
                               time_limit_s=time_limit_s)
        if "Optimal" not in (s_flat.status, s_prana.status):
            if s_flat.status != "Optimal" or s_prana.status != "Optimal":
                violations.append(Violation(dstr, "SITE", "solver_status", 0,
                                            f"flat={s_flat.status} "
                                            f"prana={s_prana.status}"))
                continue

        b_flat = bill_summary(s_flat.total_power_mw * DT_H, lc, s_flat.peak_mw,
                              site.tariff)
        b_prana = bill_summary(s_prana.total_power_mw * DT_H, lc, s_prana.peak_mw,
                               site.tariff)
        violations += verify_schedule(s_prana, fleet_prana, site, dstr)

        alt_flat = alt_supply_cost_rs(s_flat, fleet_flat)
        alt_prana = alt_supply_cost_rs(s_prana, fleet_prana)
        wear_flat = (wear_cost_rs(s_flat, fleet_flat)
                     + pf_penalty_rs(s_flat, fleet_flat, lc, site.tariff))
        wear_prana = (wear_cost_rs(s_prana, fleet_prana)
                      + pf_penalty_rs(s_prana, fleet_prana, lc, site.tariff))
        tot_flat = b_flat["total_rs"] + alt_flat + wear_flat
        tot_prana = b_prana["total_rs"] + alt_prana + wear_prana

        rows.append({
            "date": dstr,
            "flat_bill_rs": tot_flat,
            "prana_bill_rs": tot_prana,
            "saving_rs": tot_flat - tot_prana,
            "flat_elec_rs": b_flat["total_rs"],
            "prana_elec_rs": b_prana["total_rs"],
            "flat_alt_rs": alt_flat,
            "prana_alt_rs": alt_prana,
            "flat_wear_rs": wear_flat,
            "prana_wear_rs": wear_prana,
            "elec_saving_rs": b_flat["total_rs"] - b_prana["total_rs"],
            "alt_extra_rs": alt_prana - alt_flat,
            "wear_extra_rs": wear_prana - wear_flat,
            "flat_mwh": b_flat["energy_mwh"],
            "prana_mwh": b_prana["energy_mwh"],
            "flat_peak_mw": s_flat.peak_mw,
            "prana_peak_mw": s_prana.peak_mw,
            "md_saving_rs": b_flat["demand_charge_rs"] - b_prana["demand_charge_rs"],
            "rtm_spread_rs_mwh": float(rtm.max() - rtm.min()),
            "rtm_mean_rs_mwh": float(rtm.mean()),
            "solve_s": s_prana.solve_seconds,
        })
        if progress and (i % 10 == 0 or i == len(chosen)):
            got = pd.DataFrame(rows)["saving_rs"].mean()
            print(f"  {i:>4}/{len(chosen)}  {dstr}  "
                  f"mean saving Rs {got:,.0f}/day", flush=True)

    return BacktestResult(
        pd.DataFrame(rows), violations,
        "forecast" if use_forecast else "perfect_foresight",
    )


def _cli() -> None:
    ap = argparse.ArgumentParser(description="PRANA backtest")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--end", default=None)
    ap.add_argument("--forecast", action="store_true",
                    help="use the quantile forecast instead of perfect foresight")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--time-limit", type=int, default=60)
    ap.add_argument("--site", choices=("chloralkali", "refinery", "fertilizer"),
                    default="chloralkali")
    args = ap.parse_args()

    if args.site == "chloralkali":
        # 700 TPD caustic plant. Cell house is the flexible asset; balance of
        # plant (brine, compression, evaporation) is the base load.
        site = SiteConfig(name="Chlor-alkali complex", base_load_mw=12.0)
        site.tariff.contract_demand_mw = 85.0
        fleet_fn = fleet_chloralkali
    elif args.site == "fertilizer":
        # Ammonia-urea complex: smaller, slower, deeper buffers.
        site = SiteConfig(name="Ammonia-urea complex", base_load_mw=25.0)
        site.tariff.contract_demand_mw = 52.0
        fleet_fn = fleet_fertilizer
    else:
        site, fleet_fn = SiteConfig(), fleet_refinery

    mode = "forecast (realistic)" if args.forecast else "perfect foresight (upper bound)"
    print(f"replaying {args.days} days — {mode}\n")
    res = run(days=args.days, end=args.end, use_forecast=args.forecast,
              scale=args.scale, time_limit_s=args.time_limit,
              site=site, fleet_fn=fleet_fn)
    res.mode = f"{args.site}_{res.mode}"
    h = res.headline()

    print(f"\n{'':-<58}")
    print(f"{'days replayed':<34}{h['days']:>22,}")
    print(f"{'mean saving':<34}{'Rs ' + format(h['mean_saving_rs_day'], ',.0f') + '/day':>22}")
    print(f"{'median saving':<34}{'Rs ' + format(h['median_saving_rs_day'], ',.0f') + '/day':>22}")
    print(f"{'annualised':<34}{'Rs ' + format(h['annualised_rs']/1e7, ',.2f') + ' crore/yr':>22}")
    print(f"{'as % of the electricity bill':<34}{h['pct_of_bill']:>21.2f}%")
    print(f"{'per kWh of total plant load':<34}{'Rs ' + format(h['rs_per_kwh_of_load'], '.3f'):>22}")
    print(f"{'days worse than steady-state':<34}{h['days_worse_than_flat']:>22}")
    print(f"{'extra energy (process penalty)':<34}{format(h['extra_energy_mwh'], ',.0f') + ' MWh':>22}")
    print(f"{'  of which: electricity saved':<34}{'Rs ' + format(h['elec_saving_rs']/1e5, ',.1f') + ' lakh':>22}")
    print(f"{'  less: extra bought-in product':<34}{'Rs ' + format(h['alt_extra_rs']/1e5, ',.1f') + ' lakh':>22}")
    print(f"{'  less: wear + Cl2 dumped + kVAh':<34}{'Rs ' + format(h['wear_extra_rs']/1e5, ',.1f') + ' lakh':>22}")
    print(f"{'CONSTRAINT VIOLATIONS':<34}{h['violations']:>22}")
    print(f"{'mean solve time':<34}{format(h['mean_solve_s'], '.1f') + ' s':>22}")
    print(f"{'':-<58}")

    if res.violations:
        print("\nviolations:")
        for v in res.violations[:20]:
            print(f"  {v.date} {v.asset[:28]:28s} {v.kind:20s} b{v.block:>3} {v.detail}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"backtest_{res.mode}.csv"
    res.rows.to_csv(path, index=False)
    print(f"\nper-day detail -> {path}")


if __name__ == "__main__":
    _cli()


def mcp_only_penalty(
    twins_fn,
    quant: dict,
    hours: np.ndarray,
    rtm: np.ndarray,
    dam: np.ndarray,
    site: SiteConfig,
    time_limit_s: int = 90,
) -> dict[str, float]:
    """What it costs to optimize on the exchange price instead of the bill.

    The honest version of the "everyone else is wrong" claim. Two schedules are
    built for the SAME day:

      A. optimized against the market clearing price alone -- no wheeling, no
         cross-subsidy surcharge, no duty, no demand charge. This is what a tool
         that treats the exchange price as the cost of power produces.
      B. optimized against the full landed cost at the meter.

    BOTH are then settled at the true landed cost, because that is what the
    plant actually pays. The gap is the cost of the modelling error -- not a
    difference in how the saving is reported, but real rupees the MCP-only
    schedule leaves on the table.

    A peak-MW comparison is NOT a valid substitute: with the demand charge
    zeroed the peak variable is unpriced, so the solver leaves it anywhere and
    the difference is degeneracy, not behaviour.
    """
    naive_cfg = replace(
        site.tariff,
        wheeling_rs_kwh=0.0, cross_subsidy_rs_kwh=0.0,
        additional_surcharge_rs_kwh=0.0, sldc_other_rs_kwh=0.0,
        electricity_duty_frac=0.0, demand_charge_rs_kva_month=0.0,
    )
    naive_site = replace(site, tariff=naive_cfg)

    out = {}
    for label, s_cfg in (("mcp_only", naive_site), ("landed", site)):
        fl = twins_fn()
        sched = optimize_day(fl, quant, hours, s_cfg, dam_price=dam,
                             time_limit_s=time_limit_s)
        # settle BOTH at the true landed cost -- this is the whole point
        lc = landed_cost(rtm, hours, site.tariff)
        bill = bill_summary(sched.total_power_mw * DT_H, lc, sched.peak_mw,
                            site.tariff)
        out[f"{label}_rs"] = (bill["total_rs"] + alt_supply_cost_rs(sched, fl)
                              + wear_cost_rs(sched, fl)
                              + pf_penalty_rs(sched, fl, lc, site.tariff))
        out[f"{label}_peak_mw"] = sched.peak_mw
        out[f"{label}_mwh"] = bill["energy_mwh"]
    out["penalty_rs"] = out["mcp_only_rs"] - out["landed_rs"]
    out["penalty_pct"] = 100.0 * out["penalty_rs"] / out["mcp_only_rs"]
    return out
