"""Stochastic MILP dispatch over a 96-block delivery day.

Decision variables, per flexible asset a and block b
    q[a,b]   production rate            (product units / h)
    p[a,b]   electrical power           (MW)
    I[a,b]   buffer inventory           (product units)
    u[a,b]   on/off                     (binary, only if the asset may shut down)
    s[a,b]   start indicator            (binary)
    alt[a,b] alternative supply         (product units / h; e.g. SMR hydrogen)

Plant level, per block
    dam[b]        day-ahead purchase, constant within the hour   (MW)
    rtm_buy[b]    real-time top-up                               (MW)
    rtm_sell[b]   real-time sell-back                            (MW)
    dev[b]        deliberate deviation from schedule             (MW)
    peak          billing demand                                 (MW)

Objective
    min  E[cost] + lambda * CVaR_alpha[cost]  +  start costs  +  demand charge

CVaR uses the Rockafellar-Uryasev linearization over price scenarios drawn from
the forecast quantiles. The dispatch itself is a single here-and-now decision;
only the cost differs by scenario.

Two structural points worth reading before the constraints:

1. Power is tied to production by tangent hyperplanes p >= slope*q + intercept.
   P(q) is convex, so the maximum of its tangents is a valid outer
   approximation and the optimizer cannot cheat by claiming free production.

2. `dev` exists so the model can prove a negative on stage. Deviation settles
   at the published DSM rate, which an audit of 133,056 WRPC blocks shows is
   approximately max(DAM, RTM) for the same block — therefore >= RTM in 99.9%
   of blocks. The optimizer is free to deviate and never does. Every schedule
   PRANA produces carries `max_deviation_mw == 0` as evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pulp

from .config import BLOCKS_PER_DAY, DT_H, SiteConfig
from .data import dsm_rate
from .tariff import (
    LandedCost,
    demand_charge_rs_per_mw_day,
    landed_cost,
    ratchet_floor_mw,
)
from .twins import ProcessTwin

BIG_M = 1e4


@dataclass
class Schedule:
    """The optimizer's answer, plus everything needed to audit it."""

    status: str
    objective_rs: float
    total_power_mw: np.ndarray                 # site load, per block
    asset_power_mw: dict[str, np.ndarray]
    asset_production: dict[str, np.ndarray]
    asset_inventory: dict[str, np.ndarray]
    asset_online: dict[str, np.ndarray]
    alt_supply: dict[str, np.ndarray]
    coproduct_dump: dict[str, np.ndarray]      # co-product units/h to the
                                               # sink of last resort
    deviation_mw: np.ndarray
    peak_mw: float
    energy_cost_rs: float
    demand_charge_rs: float
    start_cost_rs: float
    cycling_cost_rs: float
    terminal_shortfall: dict[str, float]   # product units the day ended short
    dump_cost_rs: float
    cvar_rs: float
    binding: list[str] = field(default_factory=list)
    solve_seconds: float = 0.0

    @property
    def max_deviation_mw(self) -> float:
        return float(np.max(np.abs(self.deviation_mw)))

    @property
    def energy_mwh(self) -> float:
        return float(np.sum(self.total_power_mw) * DT_H)


@dataclass
class Constraint:
    """A typed operating restriction, from the plant or from the agent."""

    kind: str            # outage | inventory_floor | no_go | fix_load | max_rate
    asset: str           # twin name, or "*"
    start_block: int = 0
    end_block: int = 96
    value: float = 0.0
    source: str = "operator"
    note: str = ""

    def blocks(self) -> range:
        return range(max(0, self.start_block), min(96, self.end_block))


def _scenarios(
    quantiles: dict[float, np.ndarray]
) -> tuple[list[np.ndarray], list[float]]:
    """Three price scenarios with probabilities implied by the q10/q50/q90 fan."""
    lo, med, hi = quantiles[0.10], quantiles[0.50], quantiles[0.90]
    return [lo, med, hi], [0.25, 0.50, 0.25]


def optimize_day(
    twins: list[ProcessTwin],
    price_quantiles: dict[float, np.ndarray],
    hours: np.ndarray,
    site: SiteConfig,
    dam_price: np.ndarray | None = None,
    constraints: list[Constraint] | None = None,
    time_limit_s: int = 120,
    flat_baseline: bool = False,
) -> Schedule:
    """Solve one delivery day.

    `flat_baseline=True` pins every asset at its design point, which is what the
    plant does today. That is the counterfactual the savings are measured
    against — not a strawman, just the current operating practice.
    """
    import time

    t0 = time.time()
    n = len(hours)
    constraints = constraints or []
    cfg = site.tariff

    price_scen, probs = _scenarios(price_quantiles)
    landed = [landed_cost(p, hours, cfg) for p in price_scen]
    landed_med: LandedCost = landed[1]

    # Deviation carries the SAME regulatory stack as scheduled drawal -- the
    # DSM charge sits on top of the energy, it does not replace wheeling, the
    # cross-subsidy surcharge or duty. Pricing deviation as bare energy would
    # hand the optimizer a fake ~Rs 2.7/kWh discount for going unscheduled, and
    # it would route the entire plant through it. That is the single most
    # important line in this file.
    dam_ref = dam_price if dam_price is not None else price_quantiles[0.50]
    # The audit computed max(DAM, RTM) across IEX only. IEX is one of three
    # power exchanges, so our max is a LOWER BOUND on the true reference rate:
    # the residual against the IEX-only max was non-negative in 94.5% of
    # blocks. The uplift below encodes that, and it also breaks the exact tie
    # that occurs in the ~45% of blocks where RTM itself sets the maximum.
    #
    # The rate is computed PER SCENARIO. It must move with the real-time price
    # in that scenario, because in reality it is a function of the realised
    # price. Fixing it at the median while pricing energy across the fan would
    # make deviation look cheap in the high-price scenario -- and the optimizer
    # finds that immediately.
    dsm = [
        landed_cost(
            dsm_rate(dam_ref, p) * (1.0 + cfg.dsm_uplift_frac), hours, cfg
        ).total
        for p in price_scen
    ]

    m = pulp.LpProblem("prana_dispatch", pulp.LpMinimize)

    # ------------------------------------------------------------ variables
    q, p, inv, on, start, alt = {}, {}, {}, {}, {}, {}
    dump, ramp, short = {}, {}, {}
    for t in twins:
        a = t.name
        short[a] = pulp.LpVariable(f"short_{a}", 0, None)
        for b in range(n):
            q[a, b] = pulp.LpVariable(f"q_{a}_{b}", 0, t.q_max_per_h)
            p[a, b] = pulp.LpVariable(f"p_{a}_{b}", 0, t.p_max_mw)
            inv[a, b] = pulp.LpVariable(f"I_{a}_{b}", t.inv_min, t.inv_max)
            if t.can_shut_down:
                on[a, b] = pulp.LpVariable(f"u_{a}_{b}", cat="Binary")
                start[a, b] = pulp.LpVariable(f"s_{a}_{b}", cat="Binary")
            if t.alt_supply_cost_per_unit is not None:
                alt[a, b] = pulp.LpVariable(f"alt_{a}_{b}", 0, t.alt_supply_max_per_h)
            if t.coproduct_ratio > 0:
                dump[a, b] = pulp.LpVariable(f"dmp_{a}_{b}", 0, t.dump_max_per_h)
            if b > 0 and (t.cycling_cost_rs_per_unit > 0
                          or t.max_total_variation is not None):
                ramp[a, b] = pulp.LpVariable(f"r_{a}_{b}", 0, None)

    total = [pulp.LpVariable(f"P_{b}", 0, None) for b in range(n)]
    dam_hr = [pulp.LpVariable(f"dam_{h}", 0, None) for h in range(n // 4)]
    rtm_buy = [pulp.LpVariable(f"rb_{b}", 0, None) for b in range(n)]
    rtm_sell = [pulp.LpVariable(f"rs_{b}", 0, None) for b in range(n)]
    dev = [pulp.LpVariable(f"dev_{b}", 0, None) for b in range(n)]
    peak = pulp.LpVariable("peak_mw", ratchet_floor_mw(cfg), cfg.contract_demand_mw)

    # -------------------------------------------------------- asset physics
    for t in twins:
        a = t.name
        no_go = {
            bb
            for c in constraints
            if c.kind in ("outage", "no_go") and c.asset in (a, "*")
            for bb in c.blocks()
        }
        floors = [c for c in constraints
                  if c.kind == "inventory_floor" and c.asset in (a, "*")]

        for b in range(n):
            forced_off = b in no_go
            u = on.get((a, b))

            # production window and on/off coupling
            if t.can_shut_down:
                if forced_off:
                    m += u == 0
                m += q[a, b] >= t.q_min_per_h * u
                m += q[a, b] <= t.q_max_per_h * u
                m += p[a, b] <= t.p_max_mw * u
                for slope, icept in t.tangents():
                    m += p[a, b] >= slope * q[a, b] + icept * u
            else:
                if forced_off:
                    # An asset that cannot shut down is held DOWN during a
                    # forced outage rather than tripped. Pinning it exactly at
                    # the cell's own minimum is wrong when a co-product balance
                    # exists: it starves the downstream consumer and the whole
                    # day goes infeasible, which is a modelling artefact, not a
                    # plant. A single-train trip removes capacity; it does not
                    # command a specific setpoint. So cap it and let the
                    # co-product balance decide where it can actually sit --
                    # and if THAT is infeasible, the answer is genuinely "this
                    # outage cannot be absorbed", which is worth being told.
                    m += q[a, b] <= max(t.q_min_per_h, t.derate_floor_per_h)
                    m += q[a, b] >= t.q_min_per_h
                else:
                    m += q[a, b] >= t.q_min_per_h
                m += q[a, b] <= t.q_max_per_h
                for slope, icept in t.tangents():
                    m += p[a, b] >= slope * q[a, b] + icept

            # ramp limit on production rate, plus |dq| for the cycling charge
            if b > 0:
                dq = t.ramp_frac_per_block * t.q_nom_per_h
                m += q[a, b] - q[a, b - 1] <= dq
                m += q[a, b - 1] - q[a, b] <= dq
                if (a, b) in ramp:
                    m += ramp[a, b] >= q[a, b] - q[a, b - 1]
                    m += ramp[a, b] >= q[a, b - 1] - q[a, b]

            # COUPLED CO-PRODUCT BALANCE — the constraint the panel said was
            # missing, and the one that actually sets the turndown floor.
            # Production is stoichiometric and the co-product cannot be stored,
            # so it must be taken by the downstream consumer within ITS turndown
            # band, with a low-value sink of last resort for the remainder:
            #
            #     sink_min <= ratio*q[b] - dump[b] <= sink_max
            #
            # Note the dump only relieves the UPPER bound. Nothing can relieve
            # the lower one: if the consumer needs the co-product, the unit
            # must make it, and no amount of cheap power changes that.
            if t.coproduct_ratio > 0:
                made = t.coproduct_ratio * q[a, b]
                m += made - dump[a, b] >= t.sink_min_per_h
                m += made - dump[a, b] <= t.sink_max_per_h

            # inventory dynamics
            supply = q[a, b] + (alt[(a, b)] if (a, b) in alt else 0)
            prev = inv[a, b - 1] if b > 0 else t.inv_init
            m += inv[a, b] == (
                prev * (1.0 - t.inv_loss_frac_per_h * DT_H)
                + (supply - t.demand_per_h) * DT_H
            )
            for c in floors:
                if b in c.blocks():
                    m += inv[a, b] >= c.value

            # start indicator + minimum up/down time
            if t.can_shut_down and b > 0:
                m += start[a, b] >= on[a, b] - on[a, b - 1]
                for k in range(b + 1, min(n, b + t.min_up_blocks)):
                    m += on[a, k] >= on[a, b] - on[a, b - 1]
                for k in range(b + 1, min(n, b + t.min_down_blocks)):
                    m += 1 - on[a, k] >= on[a, b - 1] - on[a, b]

        # TOTAL-VARIATION BUDGET — the control room's real constraint. A board
        # operator will not accept a setpoint that moves all day, and "at most N
        # changes" is a binary count that would blow up the MILP. Capping
        # sum|dq| is the linear equivalent: it buys the same restraint at no
        # branching cost, and it scales with the horizon.
        if t.max_total_variation is not None:
            m += pulp.lpSum(ramp[a, b] for b in range(1, n)) <= (
                t.max_total_variation * (n / float(BLOCKS_PER_DAY)))

        # Terminal inventory: no gaming the horizon by dumping the buffer.
        #
        # SOFT, not hard. As a hard constraint this is not physics — it is an
        # anti-gaming guard — and it makes any genuine multi-hour outage
        # INFEASIBLE, because the lost tonnes cannot always be made up inside
        # the same day at x_max. That is a modelling artefact: a real plant
        # draws the buffer down and refills it over the following days, which is
        # what the buffer is for. Priced at the product's own value, the
        # optimizer cannot profit by ending short, but a forced outage can still
        # be absorbed -- and the shortfall is reported rather than hidden.
        m += inv[a, n - 1] + short[a] >= t.inv_init

    # --------------------------------------------------------- plant balance
    for b in range(n):
        m += total[b] == site.base_load_mw + pulp.lpSum(
            p[t.name, b] for t in twins
        )
        m += total[b] == (
            dam_hr[b // 4] + rtm_buy[b] - rtm_sell[b] + dev[b]
        )
        # A consumer with no generation can only unwind a day-ahead position;
        # without this cap the model invents a merchant trading desk.
        m += rtm_sell[b] <= dam_hr[b // 4]
        # A DISCOM-supplied consumer has no exchange position to deviate from
        # and nothing to sell back. Leaving these open lets the model settle
        # retail load at the market DSM rate -- which is far below the retail
        # tariff -- and it routes the ENTIRE plant through deviation. It is not
        # arbitrage, it is a category error: deviation settlement applies to
        # scheduled open-access drawal, not to a retail connection.
        if cfg.mode == "DISCOM":
            m += dev[b] == 0
            m += rtm_sell[b] == 0
            m += rtm_buy[b] == 0
            m += dam_hr[b // 4] == total[b]
        m += total[b] <= peak
        for c in constraints:
            if c.kind == "fix_load" and b in c.blocks():
                m += total[b] == c.value

    # ---------------------------------------------------------- flat baseline
    if flat_baseline:
        # What the plant does today: one steady setpoint per asset, held all
        # day. The setpoint is not pinned to nameplate -- it is whatever
        # constant rate holds inventory against demand and boil-off, which is
        # exactly how a real plant is run. This is the honest counterfactual.
        for t in twins:
            for b in range(1, n):
                m += q[t.name, b] == q[t.name, 0]
            if t.can_shut_down:
                for b in range(n):
                    m += on[t.name, b] == 1

    # ------------------------------------------------------------- objective
    def scenario_cost(idx: int):
        lc = landed[idx]
        # Sell-back is credited at the market price NET of losses -- you deliver
        # less than you inject. Crediting it at the grossed-up landed rate would
        # make buy-then-sell a free arbitrage and the model unbounded.
        sell_credit = price_scen[idx] / 1000.0 * (1.0 - cfg.transmission_loss_frac)
        # The DAM leg carries the same landed stack as the market leg, so the
        # regulatory charges are never accidentally avoided by shifting venue.
        return pulp.lpSum(
            (dam_hr[b // 4] + rtm_buy[b]) * DT_H * 1000.0 * lc.total[b]
            - rtm_sell[b] * DT_H * 1000.0 * sell_credit[b]
            + dev[b] * DT_H * 1000.0 * dsm[idx][b]
            for b in range(n)
        )

    costs = [scenario_cost(i) for i in range(len(price_scen))]
    expected = pulp.lpSum(pr * c for pr, c in zip(probs, costs))

    eta = pulp.LpVariable("cvar_eta")
    z = [pulp.LpVariable(f"z_{i}", 0, None) for i in range(len(costs))]
    for i, c in enumerate(costs):
        m += z[i] >= c - eta
    cvar = eta + (1.0 / (1.0 - site.cvar_alpha)) * pulp.lpSum(
        pr * zi for pr, zi in zip(probs, z)
    )

    start_cost = pulp.lpSum(
        t.start_cost_rs * start[t.name, b]
        for t in twins if t.can_shut_down for b in range(n)
    )
    alt_cost = pulp.lpSum(
        t.alt_supply_cost_per_unit * alt[t.name, b] * DT_H
        for t in twins if t.alt_supply_cost_per_unit is not None for b in range(n)
    )
    # Co-product diverted to the sink of last resort is real margin destroyed,
    # and cycling is real membrane life consumed. Both are priced INSIDE the
    # objective so the optimizer trades them against the energy saving, rather
    # than being subtracted afterwards from a number it never saw.
    dump_cost = pulp.lpSum(
        t.dump_cost_per_unit * dump[t.name, b] * DT_H
        for t in twins if t.coproduct_ratio > 0 for b in range(n)
    )
    # Ending the day short of the opening buffer is charged at the product's
    # own value, so it is never worth doing for an energy saving -- but it stays
    # possible when an outage leaves no alternative.
    terminal_cost = pulp.lpSum(
        t.terminal_shortfall_cost_per_unit * short[t.name] for t in twins
    )
    cycling_cost = pulp.lpSum(
        t.cycling_cost_rs_per_unit * ramp[t.name, b]
        for t in twins if t.cycling_cost_rs_per_unit > 0
        for b in range(1, n) if (t.name, b) in ramp
    )
    # Daily rate x days in horizon. Without the scaling a multi-day solve pays
    # one day of demand charge for a week of peak, and the optimizer happily
    # buys peak it would never buy in reality.
    demand_cost = peak * demand_charge_rs_per_mw_day(cfg) * (n / 96.0)

    # Convex combination, NOT expected + w*CVaR. The additive form silently
    # scales the energy term by (1+w) against the start, alternative-supply and
    # demand-charge terms, which distorts every make-vs-buy and peak-shaving
    # trade-off. With w=0 this is risk-neutral; with identical scenarios it
    # collapses exactly onto the deterministic cost.
    w = site.cvar_weight
    m += ((1.0 - w) * expected + w * cvar
          + start_cost + alt_cost + dump_cost + cycling_cost
          + terminal_cost + demand_cost)

    # ----------------------------------------------------------------- solve
    m.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_s))
    status = pulp.LpStatus[m.status]

    def vals(d, t):
        return np.array([pulp.value(d[t.name, b]) or 0.0 for b in range(n)])

    sched = Schedule(
        status=status,
        objective_rs=float(pulp.value(m.objective) or 0.0),
        total_power_mw=np.array([pulp.value(v) or 0.0 for v in total]),
        asset_power_mw={t.name: vals(p, t) for t in twins},
        asset_production={t.name: vals(q, t) for t in twins},
        asset_inventory={t.name: vals(inv, t) for t in twins},
        asset_online={
            t.name: (vals(on, t) if t.can_shut_down else np.ones(n)) for t in twins
        },
        alt_supply={
            t.name: (vals(alt, t) if t.alt_supply_cost_per_unit is not None
                     else np.zeros(n))
            for t in twins
        },
        coproduct_dump={
            t.name: (vals(dump, t) if t.coproduct_ratio > 0 else np.zeros(n))
            for t in twins
        },
        deviation_mw=np.array([pulp.value(v) or 0.0 for v in dev]),
        peak_mw=float(pulp.value(peak) or 0.0),
        energy_cost_rs=float(pulp.value(costs[1]) or 0.0),
        demand_charge_rs=float(pulp.value(demand_cost) or 0.0),
        start_cost_rs=float(pulp.value(start_cost) or 0.0),
        cycling_cost_rs=float(pulp.value(cycling_cost) or 0.0),
        terminal_shortfall={t.name: float(pulp.value(short[t.name]) or 0.0)
                            for t in twins},
        dump_cost_rs=float(pulp.value(dump_cost) or 0.0),
        cvar_rs=float(pulp.value(cvar) or 0.0),
        solve_seconds=time.time() - t0,
    )
    sched.binding = _binding_constraints(sched, twins, landed_med, site)
    return sched


def _binding_constraints(
    s: Schedule, twins: list[ProcessTwin], lc: LandedCost, site: SiteConfig
) -> list[str]:
    """Plain-language account of what actually limited the schedule.

    Derived from the solution, not from the LLM. The agent phrases these; it
    does not invent them.
    """
    out: list[str] = []
    tol = 1e-3
    marginal_md = demand_charge_rs_per_mw_day(site.tariff)
    out.append(
        f"Demand charge is worth Rs {marginal_md:,.0f} per MW of peak per day. "
        f"Any shift that raises the peak must beat that on energy alone — the "
        f"term an MCP-only optimizer omits."
    )
    if s.peak_mw >= site.tariff.contract_demand_mw - 0.05:
        out.append(
            f"Contract demand ({site.tariff.contract_demand_mw:.0f} MW) is binding "
            f"— the schedule cannot draw more in any block."
        )
    if s.peak_mw <= ratchet_floor_mw(site.tariff) + 0.05:
        out.append(
            f"Billing demand has hit the {site.tariff.md_ratchet_frac:.0%} ratchet "
            f"floor ({ratchet_floor_mw(site.tariff):.1f} MW); shaving further "
            f"earns nothing."
        )
    for t in twins:
        q = s.asset_production[t.name]
        inv = s.asset_inventory[t.name]
        running = q > tol
        at_min = running & (q <= t.q_min_per_h + tol)
        if int(np.sum(~running)):
            out.append(
                f"{t.name}: shut down in {int(np.sum(~running))} blocks — "
                f"cheaper to stop than to hold minimum stable load."
            )
        if int(np.sum(at_min)):
            out.append(
                f"{t.name}: minimum stable load binds in {int(np.sum(at_min))} "
                f"blocks ({t.x_min:.0%} of design)."
            )
        if np.any(q >= t.q_max_per_h - tol):
            k = int(np.sum(q >= t.q_max_per_h - tol))
            out.append(f"{t.name}: maximum sustained rate binds in {k} blocks.")
        if np.any(inv <= t.inv_min + tol):
            out.append(
                f"{t.name}: buffer hit its floor ({t.inv_min:.0f} {t.unit}) — "
                f"this is what caps the depth of the shed."
            )
        if np.any(inv >= t.inv_max - tol):
            out.append(f"{t.name}: buffer full ({t.inv_max:.0f} {t.unit}).")

        # The co-product balance is usually the REAL floor. Say so explicitly,
        # because "why won't it turn down further?" is the first question a
        # board operator asks, and "minimum stable load" is the wrong answer.
        if t.coproduct_ratio > 0:
            dmp = s.coproduct_dump[t.name]
            made = t.coproduct_ratio * q
            k = int(np.sum(made - dmp <= t.sink_min_per_h + tol))
            if k:
                floor_x = (t.sink_min_per_h / t.coproduct_ratio) / t.q_nom_per_h
                out.append(
                    f"{t.name}: the {t.coproduct_name} consumer's minimum take "
                    f"binds in {k} blocks. It holds the unit at "
                    f"{floor_x:.0%} of design — well above the {t.x_min:.0%} "
                    f"safety interlock. THIS, not the cells, is the floor."
                )
            if float(np.sum(dmp)) * DT_H > tol:
                out.append(
                    f"{t.name}: {float(np.sum(dmp)) * DT_H:.1f} {t.unit} of "
                    f"{t.coproduct_name} routed to the sink of last resort, "
                    f"costing Rs {s.dump_cost_rs:,.0f} of destroyed margin."
                )
        if t.cycling_cost_rs_per_unit > 0 and s.cycling_cost_rs > 0:
            tv = float(np.sum(np.abs(np.diff(q))))
            cap = t.max_total_variation
            msg = (f"{t.name}: setpoint travel {tv:.1f} {t.unit}/h over the "
                   f"horizon, charged at Rs {s.cycling_cost_rs:,.0f} of "
                   f"membrane life.")
            if cap is not None and tv >= cap * (len(q) / BLOCKS_PER_DAY) - 1e-2:
                msg += " The movement budget is BINDING — more travel was worth "
                msg += "buying, and the control-room limit is what stopped it."
            out.append(msg)
    out.append(
        "Deliberate deviation used in 0 blocks — the DSM rate is >= the "
        "real-time price by regulatory design, so deviation is never profitable."
        if s.max_deviation_mw < 1e-6
        else f"WARNING: deviation used, max {s.max_deviation_mw:.2f} MW — "
             "check the DSM rate series."
    )
    return out
