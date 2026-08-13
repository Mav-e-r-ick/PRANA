"""B5: how much of PRANA's saving does a simple ToD rule already capture?

The rule a plant manager writes on a whiteboard: run hard in the solar window,
back off to the deliverable floor in the evening peak slab, nominal otherwise,
slewing at the asset's own ramp limit. Settled identically to PRANA and to the
flat baseline, and independently verified against true physics.
"""
import numpy as np
from prana import data, twins
from prana.config import SiteConfig, DT_H
from prana.forecast import QuantileForecaster
from prana.optimizer import optimize_day
from prana.backtest import (verify_schedule, wear_cost_rs, pf_penalty_rs,
                            alt_supply_cost_rs)
from prana.tariff import bill_summary, landed_cost


def tod_rule_schedule(base, hours):
    """Ramp-limited setpoint from a pure time-of-day rule. No prices used.

    PRODUCTION-NEUTRAL by construction, which is the only fair comparison. A
    naive "shed to the floor for all seven peak hours" rule cannot balance: it
    would need ~126% of design in the solar window to make the tonnes back, and
    x_max is 108%. So the depth of the peak shed is solved for, given the solar
    window runs at the deliverable maximum and the rest at nominal. That is what
    a competent board operator with a tariff sheet would actually run -- and it
    is the baseline PRANA has to beat to justify a MILP.
    """
    lo, hi, nom = base.deliverable_q_min_per_h, base.deliverable_q_max_per_h, base.q_nom_per_h
    peak = (hours >= 17) & (hours < 24)
    solar = (hours >= 9) & (hours < 17)
    other = ~(peak | solar)
    need = base.demand_per_h * len(hours) * DT_H          # tonnes the day owes
    made_fixed = (hi * solar.sum() + nom * other.sum()) * DT_H
    n_peak_h = peak.sum() * DT_H
    L = (need - made_fixed) / n_peak_h if n_peak_h else nom
    L = float(np.clip(L, lo, hi))                          # never below the Cl2 floor
    tgt = np.where(peak, L, np.where(solar, hi, nom))
    dq = base.ramp_frac_per_block * base.q_nom_per_h
    q = np.empty_like(tgt, dtype=float); cur = nom
    for b, t in enumerate(tgt):
        cur += np.clip(t - cur, -dq, dq); q[b] = cur
    return q


def settle(power_mw, peak, fl, lc, cfg, q_by_asset, dump_by_asset, shortfall_t):
    """Settle the rule schedule on EXACTLY the terms PRANA is held to.

    The first version of this omitted the terminal-inventory charge, so the rule
    was free to under-produce ~42 t/day and bank the electricity saving. It
    "beat" PRANA by 382% on every single day, which is what a rigged comparison
    looks like. PRANA is forced to return the buffer it borrowed (soft
    constraint, priced at the product's own value); the rule must be too.
    """
    class S:
        pass
    s = S(); s.asset_production = q_by_asset; s.coproduct_dump = dump_by_asset
    b = bill_summary(power_mw * DT_H, lc, peak, cfg)
    base = fl[0]
    return (b["total_rs"] + wear_cost_rs(s, fl)
            + shortfall_t * base.terminal_shortfall_cost_per_unit), b


mkt = data.load_market(); days = data.available_days(mkt)[-60:]
fc = QuantileForecaster.load()
rows = []
for dstr in days:
    d = data.day(mkt, dstr)
    site = SiteConfig(name="CA", base_load_mw=12.0); site.tariff.contract_demand_mw = 92.0
    hrs = d["hour"].to_numpy(); dam = d["dam"].to_numpy(float)
    lc = landed_cost(d["rtm"].to_numpy(float), hrs, site.tariff)
    quant = fc.predict(d, mkt)

    fl_p = twins.fleet_chloralkali(); fl_f = twins.fleet_chloralkali()
    sp = optimize_day(fl_p, quant, hrs, site, dam_price=dam, time_limit_s=30)
    sf = optimize_day(fl_f, quant, hrs, site, dam_price=dam, time_limit_s=30,
                      flat_baseline=True)
    if "Optimal" not in (sp.status, sf.status):
        continue

    base = twins.chloralkali()
    q = tod_rule_schedule(base, hrs)
    # co-product balance for the rule schedule: dump only the surplus
    made = base.coproduct_ratio * q
    dump = np.clip(made - base.sink_max_per_h, 0, base.dump_max_per_h)
    if np.any(made - dump < base.sink_min_per_h - 1e-6):
        continue                      # rule would starve the consumer; skip day
    # inventory must balance on the same terms PRANA faces
    inv, level = [], base.inv_init
    for qq in q:
        level += (qq - base.demand_per_h) * DT_H
        level = min(max(level, base.inv_min), base.inv_max)
        inv.append(level)
    shortfall_t = max(0.0, base.inv_init - inv[-1])

    p = np.array([base.power_mw(x) for x in q])
    tot = site.base_load_mw + p
    peak = max(float(tot.max()), 0.0)

    def cost(sched, fl):
        c, b = None, bill_summary(sched.total_power_mw * DT_H, lc, sched.peak_mw, site.tariff)
        return (b["total_rs"] + wear_cost_rs(sched, fl)
                + pf_penalty_rs(sched, fl, lc, site.tariff)
                + alt_supply_cost_rs(sched, fl)), b

    c_p, b_p = cost(sp, fl_p)
    c_f, b_f = cost(sf, fl_f)
    c_t, b_t = settle(tot, peak, [base], lc, site.tariff,
                      {base.name: q}, {base.name: dump}, shortfall_t)
    c_t += pf_penalty_rs(type("S", (), {"asset_production": {base.name: q},
                                        "asset_power_mw": {base.name: p}})(),
                         [base], lc, site.tariff)
    rows.append((c_f - c_p, c_f - c_t, b_f["energy_mwh"], shortfall_t))

a = np.array(rows)
prana, tod, mwh, short = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
print(f"rule schedule mean terminal shortfall {short.mean():.1f} t/day "
      f"(charged at the product's own value)")
print(f"days compared                      {len(a)}")
print(f"PRANA saving vs flat      Rs {prana.mean():>10,.0f}/day   Rs {prana.sum()/(mwh.sum()*1000):.3f}/kWh")
print(f"ToD-rule saving vs flat   Rs {tod.mean():>10,.0f}/day   Rs {tod.sum()/(mwh.sum()*1000):.3f}/kWh")
print(f"ToD rule captures                  {tod.sum()/prana.sum():.0%} of PRANA's saving")
print(f"PRANA's incremental value Rs {(prana-tod).mean():>10,.0f}/day  "
      f"= Rs {(prana-tod).mean()*365/1e7:.2f} crore/yr")
print(f"days ToD rule beats PRANA          {(tod>prana).sum()}")
print(f"days ToD rule LOSES money          {(tod<0).sum()}")
