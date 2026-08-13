"""One-command demo — every headline number, printed to a terminal.

Venue insurance. If Streamlit will not start on the day, this produces the same
figures the console shows, in the same order as the pitch.

    python run_demo.py
    python run_demo.py --date 2026-06-05 --forecast
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

# A Windows console defaults to cp1252 and cannot encode the block characters
# used by the sparkline. Try UTF-8; fall back to ASCII rather than crash on the
# day. Venue laptops are not a place to discover an encoding error.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    BAR, RULE = "▁▂▃▄▅▆▇█", "─"
except Exception:                                          # pragma: no cover
    BAR, RULE = ".:-=+*#@", "-"

from prana import agent, data, tariff, twins
from prana.backtest import (alt_supply_cost_rs, pf_penalty_rs,
                            verify_schedule, wear_cost_rs)
from prana.config import DEMO_DATE, DT_H, OUT_DIR, SiteConfig
from prana.forecast import QuantileForecaster, perfect_foresight
from prana.optimizer import optimize_day

W = 74


def rule(title: str = "") -> None:
    print("\n" + (f"── {title} " + "─" * (W - len(title) - 4) if title else "─" * W))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=DEMO_DATE)
    ap.add_argument("--forecast", action="store_true")
    ap.add_argument("--site", default="chloralkali",
                    choices=("chloralkali", "refinery", "fertilizer"))
    args = ap.parse_args()

    SITES = {"chloralkali": (twins.fleet_chloralkali, 12.0, 85.0,
                             "Chlor-alkali complex (700 TPD caustic)"),
             "refinery":    (twins.fleet_refinery, 62.0, 110.0,
                             "Refinery utilities block"),
             "fertilizer":  (twins.fleet_fertilizer, 25.0, 52.0,
                             "Ammonia-urea complex")}
    make_fleet, _base, _cd, _site_name = SITES[args.site]

    market = data.load_market()
    d = data.day(market, args.date)
    hours = d["hour"].to_numpy()
    rtm = d["rtm"].to_numpy(float)
    dam = d["dam"].to_numpy(float)
    site = SiteConfig(name=_site_name, base_load_mw=_base)
    site.tariff.contract_demand_mw = _cd

    # ---------------------------------------------------------------- beat 1
    rule("1. THE SHAPE HAS BROKEN  (RTM, Rs/kWh, mean by hour)")
    for fy in ("2022-23", "2025-26", "2026-27"):
        s = market[market.fy == fy]
        if s.empty:
            continue
        prof = s.groupby("hour")["rtm"].mean() / 1000
        spark = "".join(
            BAR[min(7, int(v / max(prof.max(), 1e-9) * 7.99))] for v in prof
        )
        sol = s[s.hour.between(9, 16)].rtm.mean() / 1000
        eve = s[s.hour.between(18, 23)].rtm.mean() / 1000
        star = " *Apr-Aug only" if fy == "2026-27" else ""
        print(f"  FY{fy}  {spark}  solar {sol:4.2f}  evening {eve:4.2f}  "
              f"ratio {eve/sol:4.2f}{star}")
    print(f"\n  Below Rs 2/kWh: "
          f"{(market[market.fy=='2022-23'].rtm < 2000).mean()*100:.1f}% of FY22-23 "
          f"-> {(market[market.fy=='2026-27'].rtm < 2000).mean()*100:.1f}% of FY26-27*")

    # ---------------------------------------------------------------- beat 2
    rule("2. THE BATTERY IS ALREADY BUILT")
    fleet = make_fleet()
    tot_mwh = tot_mw = 0.0
    for t in fleet:
        vb = t.virtual_battery()
        tot_mwh += vb["energy_mwh"]
        tot_mw += vb["power_mw"]
        print(f"  {t.name[:42]:42s} {vb['power_mw']:5.1f} MW x "
              f"{vb['duration_h']:4.1f} h = {vb['energy_mwh']:5.0f} MWh")
    print(f"  {'SITE VIRTUAL BATTERY':42s} {tot_mw:5.1f} MW          "
          f"= {tot_mwh:5.0f} MWh")
    print(f"  Equivalent 4h BESS capex at Rs 0.6-1.1 cr/MWh: "
          f"Rs {tot_mwh*1.1:,.0f} crore  (PRANA capex: zero)")

    # ---------------------------------------------------------------- beat 3
    rule("3. FLEXIBILITY COST CURVE  phi(dMW, 4h), Rs per MWh shifted")
    grid = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    print(f"  {'asset':42s}" + "".join(f"{g:>5.0f}MW" for g in grid))
    for t in twins.all_archetypes():
        phi = t.flexibility_cost_curve(grid, 4.0)
        cells = "".join(f"{v:>7.0f}" if np.isfinite(v) else "    n/a" for v in phi)
        mark = "  <-- this site" if any(t.kind == f.kind for f in fleet) else ""
        print(f"  {t.name[:42]:42s}{cells}{mark}")
    print("  Chlor-alkali is cheapest AND deepest: its specific energy IMPROVES")
    print("  on turn-down. Pipeline sits ~10x higher - that is the cube law,")
    print("  P ~ throughput^3, showing up as a price.")

    # ---------------------------------------------------------------- beat 4
    fc = QuantileForecaster.load() if QuantileForecaster.available() else None
    quant = (fc.predict(d, market) if (args.forecast and fc)
             else perfect_foresight(d))
    mode = "forecast" if (args.forecast and fc) else "perfect foresight"

    rule(f"4. LIVE SOLVE — {args.date} — {_site_name}  ({mode})")
    print(f"  RTM min Rs {rtm.min():,.0f}/MWh @ "
          f"{d.ts[int(np.argmin(rtm))].strftime('%H:%M')}   "
          f"max Rs {rtm.max():,.0f}/MWh @ "
          f"{d.ts[int(np.argmax(rtm))].strftime('%H:%M')}")

    lc = tariff.landed_cost(rtm, hours, site.tariff)
    res = {}
    for label, flat in (("steady state", True), ("PRANA", False)):
        fl = make_fleet()
        s = optimize_day(fl, quant, hours, site, dam_price=dam,
                         flat_baseline=flat, time_limit_s=120)
        b = tariff.bill_summary(s.total_power_mw * DT_H, lc, s.peak_mw, site.tariff)
        b["total_rs"] += (alt_supply_cost_rs(s, fl) + wear_cost_rs(s, fl)
                          + pf_penalty_rs(s, fl, lc, site.tariff))
        res[label] = (s, b, fl)
        print(f"  {label:14s} {b['energy_mwh']:7.1f} MWh  peak {s.peak_mw:6.2f} MW  "
              f"total Rs {b['total_rs']:>12,.0f}  ({s.status}, {s.solve_seconds:.1f}s)")

    sP, bP, flP = res["PRANA"]
    sF, bF, _ = res["steady state"]
    save = bF["total_rs"] - bP["total_rs"]
    print(f"\n  AVOIDED TODAY: Rs {save:,.0f}  = Rs {save/1e5:.2f} lakh  "
          f"({save/bF['total_rs']*100:.2f}% of the day's bill)")
    print(f"  Landed cost paid: Rs {bF['total_rs']/bF['energy_mwh']/1000:.3f} -> "
          f"Rs {bP['total_rs']/bP['energy_mwh']/1000:.3f} /kWh")
    print(f"  Non-energy share of landed cost: {lc.non_energy_share*100:.0f}% "
          f"— the part an MCP-only tool ignores")

    viol = verify_schedule(sP, flP, site, args.date)
    print(f"\n  Deviation from schedule used : {sP.max_deviation_mw:.6f} MW")
    print(f"  Violations vs TRUE physics   : {len(viol)}")

    # ---------------------------------------------------------------- beat 5
    rule("5. THE KILL SHOT — what an MCP-only optimizer would tell them to do")
    s0cfg = SiteConfig(name=_site_name, base_load_mw=_base)
    s0cfg.tariff.contract_demand_mw = _cd
    s0cfg.tariff.demand_charge_rs_kva_month = 0.0
    fl0 = make_fleet()
    s0 = optimize_day(fl0, quant, hours, site=s0cfg, dam_price=dam,
                      time_limit_s=120)
    flex = max(fleet, key=lambda t: t.p_nom_mw)          # the biggest flexible asset
    e_name = flex.name
    thr = flex.q_min_per_h * 1.02
    on_real = int((sP.asset_production[e_name] > thr).sum())
    on_zero = int((s0.asset_production[e_name] > thr).sum())
    print(f"  {'demand charge modelled (reality)':44s} peak {sP.peak_mw:6.2f} MW   "
          f"flex asset >min in {on_real:2d}/96 blocks")
    print(f"  {'demand charge = 0 (MCP-only assumption)':44s} peak {s0.peak_mw:6.2f} MW   "
          f"flex asset >min in {on_zero:2d}/96 blocks")
    print(f"\n  Demand charge is worth Rs "
          f"{tariff.demand_charge_rs_per_mw_day(site.tariff):,.0f} per MW of peak "
          f"per day.\n  Omit it and you get a different — and wrong — answer.")

    # ---------------------------------------------------------------- beat 6
    rule("6. THE OPERATOR CURVEBALL")
    print(f"  agent backend: {agent.backend_status()}")
    now_block = 56                                   # 14:00, mid-afternoon
    utter = {"chloralkali": "Rectifier B tripped, back by 21:00.",
             "refinery":    "Compressor B tripped, back by 21:00.",
             "fertilizer":  "Compressor B tripped, back by 21:00."}[args.site]
    ex = agent.perturb(utter, flP, now_block=now_block)
    print(f"  clock: {now_block//4:02d}:00")
    print(f'  operator: "{utter}"')
    for c in ex.constraints:
        print(f"     -> {c.kind} on {c.asset[:36]} "
              f"{c.start_block//4:02d}:00-{c.end_block//4:02d}:00  "
              f"[{c.source}, sign-off required]")
    fl2 = make_fleet()
    s2 = optimize_day(fl2, quant, hours, site, dam_price=dam,
                      constraints=ex.constraints, time_limit_s=120)
    if s2.status != "Optimal":
        # An infeasible re-solve is a real answer, not a number to print. It
        # means the constraint cannot be met at all -- e.g. the outage would
        # starve the chlorine consumer -- and quoting a rupee figure off an
        # infeasible solve is how a demo tells a lie.
        print(f"     re-solved in {s2.solve_seconds:.1f}s — {s2.status.upper()}: "
              f"this outage cannot be absorbed. The co-product consumer would "
              f"have to be cut too. That is the answer the control room needs.")
    else:
        b2 = tariff.bill_summary(s2.total_power_mw * DT_H, lc, s2.peak_mw,
                                 site.tariff)
        b2["total_rs"] += (alt_supply_cost_rs(s2, fl2) + wear_cost_rs(s2, fl2)
                           + pf_penalty_rs(s2, fl2, lc, site.tariff))
        print(f"     re-solved in {s2.solve_seconds:.1f}s — cost of the outage: "
              f"Rs {b2['total_rs'] - bP['total_rs']:,.0f}")

    # ---------------------------------------------------------------- beat 7
    rule("7. WHY THIS SCHEDULE  (from the solver, not the language model)")
    for b in sP.binding:
        print(f"  - {b}")

    rule("8. REPLAY")
    import pandas as pd
    pre = "" if args.site == "refinery" else f"{args.site}_"
    for m, nice in ((f"{pre}forecast", "with forecast error (realistic)"),
                    (f"{pre}perfect_foresight", "perfect foresight (upper bound)")):
        p = OUT_DIR / f"backtest_{m}.csv"
        if not p.exists():
            continue
        r = pd.read_csv(p)
        print(f"  {nice:36s} {len(r):3d} days  "
              f"Rs {r.saving_rs.mean()/1e5:5.2f} lakh/day  "
              f"Rs {r.saving_rs.sum()/(r.flat_mwh.sum()*1000):.3f}/kWh of load  "
              f"{int((r.saving_rs<0).sum())} bad days")
    print()


if __name__ == "__main__":
    main()
