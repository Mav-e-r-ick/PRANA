"""The decision engine — and the reason PRANA is allowed to say NO.

PRODUCTION FIRST. SAFETY FIRST. CONSTRAINTS FIRST. ECONOMICS SECOND.

This module answers one question: *given what the market is paying and what the
process would charge to move, should the plant do anything at all?*

The answer is very often **DO NOTHING**, and that is a feature. A system that
always finds a reason to act is not an optimiser, it is a salesman. An operator
who is told to shed load on a day when it is not worth it will stop trusting the
system on the day when it is.

DECISION ORDER — hard gates before economics, always:

    1. hard constraint active            -> DO NOTHING
    2. flexibility physically unavailable-> DO NOTHING
    3. net benefit <= 0                  -> DO NOTHING
    4. otherwise                         -> SHIFT

A high electricity price is never on its own sufficient. It appears only in
step 3, after both physical gates have been cleared.

EVERY REASON RETURNED BY THIS MODULE COMES FROM THE MODEL. The LLM layer may
phrase a reason for a human, and may propose candidate constraints for an
engineer to approve, but it may not originate one and it may not decide the
setpoint. See `agent.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .process import ILLUSTRATIVE, FlexibilityQuote

# Reason codes. Stable identifiers so the UI, the tests and the explanation
# layer all refer to the same thing.
R_HARD_CONSTRAINT = "HARD_CONSTRAINT"
R_NO_FLEXIBILITY = "NO_USABLE_FLEXIBILITY"
R_UNECONOMIC = "PROCESS_COST_EXCEEDS_BENEFIT"
R_INVENTORY = "INVENTORY_CONSTRAINT"
R_RECOVERY = "RECOVERY_CONSTRAINT"
R_ECONOMIC = "ECONOMIC_FLEXIBILITY"

SHIFT, HOLD, DO_NOTHING = "SHIFT", "HOLD", "DO NOTHING"


@dataclass
class FlexibilityDecision:
    """What to do, why, and what it is worth. Serialisable for the UI."""

    action: str
    reason_code: str
    reason: str

    shift_mw: float = 0.0
    duration_h: float = 0.0

    electricity_benefit_rs: float = 0.0
    process_cost_rs: float = 0.0
    other_cost_rs: float = 0.0
    risk_penalty_rs: float = 0.0
    net_benefit_rs: float = 0.0

    binding_constraint: str = ""
    constraint_margin_pct: float = float("nan")
    data_status: str = ILLUSTRATIVE
    detail: list[str] = field(default_factory=list)

    @property
    def acts(self) -> bool:
        return self.action == SHIFT

    def as_dict(self) -> dict:
        return {
            "action": self.action, "reason_code": self.reason_code,
            "reason": self.reason, "shift_mw": round(self.shift_mw, 2),
            "duration_h": round(self.duration_h, 2),
            "electricity_benefit_rs": round(self.electricity_benefit_rs),
            "process_cost_rs": round(self.process_cost_rs),
            "net_benefit_rs": round(self.net_benefit_rs),
            "binding_constraint": self.binding_constraint,
            "constraint_margin_pct": (None if np.isnan(self.constraint_margin_pct)
                                      else round(self.constraint_margin_pct, 1)),
            "data_status": self.data_status,
        }


def electricity_benefit_rs(
    delta_mw: float, duration_h: float,
    landed_now_rs_kwh: float, landed_later_rs_kwh: float,
) -> float:
    """What the market pays for moving `delta_mw` out of the expensive window
    and into the cheap one.

    Note both legs are priced. Counting only the avoided expensive energy and
    forgetting that the same energy is bought back later is the commonest way a
    demand-response business case is overstated.
    """
    mwh = max(0.0, delta_mw) * max(0.0, duration_h)
    return mwh * 1000.0 * (landed_now_rs_kwh - landed_later_rs_kwh)


def decide(
    model,
    delta_mw: float,
    duration_h: float,
    landed_now_rs_kwh: float,
    landed_later_rs_kwh: float,
    *,
    risk_penalty_rs: float = 0.0,
    demand_charge_rs_per_mw_day: float = 0.0,
    peak_increase_mw: float = 0.0,
) -> FlexibilityDecision:
    """Gate a proposed move through physics, then economics.

    `model` is anything satisfying `ProcessModel`. This function contains no
    knowledge of what the process makes.
    """
    status = model.data_status()
    env = model.get_operating_envelope()
    quote: FlexibilityQuote = model.calculate_flexibility_cost(delta_mw, duration_h)
    prod = model.get_production_constraints()

    # ---- GATE 1: hard constraints. Nothing economic is even computed. ------
    if prod.get("hard_constraint_active"):
        return FlexibilityDecision(
            action=DO_NOTHING, reason_code=R_HARD_CONSTRAINT,
            reason=("Production constraint prevents flexibility: "
                    + (prod.get("hard_constraint_reason")
                       or "a hard production constraint is active")),
            binding_constraint=prod.get("hard_constraint_reason", "hard constraint"),
            constraint_margin_pct=0.0, data_status=status,
            detail=["Hard constraints are evaluated before economics. "
                    "The electricity price was not considered."],
        )

    # ---- GATE 2: is the move physically available at all? ------------------
    if not quote.available:
        code = R_NO_FLEXIBILITY
        low = quote.limiting_factor.lower()
        if "buffer" in low or "inventory" in low:
            code = R_INVENTORY
        elif "ramp" in low or "recovery" in low:
            code = R_RECOVERY
        return FlexibilityDecision(
            action=DO_NOTHING, reason_code=code,
            reason=f"No usable flexibility: {quote.limiting_factor}.",
            binding_constraint=quote.limiting_factor or env.floor_reason,
            constraint_margin_pct=0.0, data_status=status,
            detail=[f"Maximum safe shed at this operating point: "
                    f"{quote.max_safe_mw:.1f} MW."],
        )

    # ---- ECONOMICS, only now ----------------------------------------------
    benefit = electricity_benefit_rs(delta_mw, duration_h,
                                     landed_now_rs_kwh, landed_later_rs_kwh)
    # A shed that raises the monthly peak elsewhere is charged for it.
    other = max(0.0, peak_increase_mw) * demand_charge_rs_per_mw_day
    net = benefit - quote.process_cost_rs - other - risk_penalty_rs

    margin = float("nan")
    p_design = model.get_power_curve()(env.design)
    if quote.max_safe_mw > 0:
        margin = 100.0 * (1.0 - delta_mw / quote.max_safe_mw)

    if net <= 0:
        return FlexibilityDecision(
            action=DO_NOTHING, reason_code=R_UNECONOMIC,
            reason=("Process flexibility cost exceeds electricity benefit — "
                    f"₹{quote.process_cost_rs + other + risk_penalty_rs:,.0f} to save "
                    f"₹{benefit:,.0f}."),
            shift_mw=0.0, duration_h=duration_h,
            electricity_benefit_rs=benefit, process_cost_rs=quote.process_cost_rs,
            other_cost_rs=other, risk_penalty_rs=risk_penalty_rs, net_benefit_rs=net,
            binding_constraint="economics", constraint_margin_pct=margin,
            data_status=status,
            detail=[f"Flexibility is available ({quote.max_safe_mw:.1f} MW) but "
                    f"costs ₹{quote.rs_per_mwh_shifted:,.0f}/MWh shifted.",
                    "The plant is better off doing nothing."],
        )

    return FlexibilityDecision(
        action=SHIFT, reason_code=R_ECONOMIC,
        reason=(f"Shift {delta_mw:.1f} MW for {duration_h:.1f} h — "
                f"net benefit ₹{net:,.0f}."),
        shift_mw=delta_mw, duration_h=duration_h,
        electricity_benefit_rs=benefit, process_cost_rs=quote.process_cost_rs,
        other_cost_rs=other, risk_penalty_rs=risk_penalty_rs, net_benefit_rs=net,
        binding_constraint=quote.limiting_factor or env.floor_reason,
        constraint_margin_pct=margin, data_status=status,
        detail=[f"Process cost ₹{quote.rs_per_mwh_shifted:,.0f}/MWh shifted.",
                f"Operating floor {env.floor_pct:.0f}% of design "
                f"({env.floor_reason}).",
                f"Maximum safe duration {quote.max_safe_duration_h:.1f} h."],
    )


def best_available_shift(
    model, duration_h: float, landed_now_rs_kwh: float, landed_later_rs_kwh: float,
    *, steps: int = 24, **kw
) -> FlexibilityDecision:
    """Search the depth axis for the most valuable *safe* move.

    Returns the best SHIFT if one exists, otherwise the DO NOTHING decision that
    explains why nothing was worth doing — never an empty result.
    """
    quote = model.calculate_flexibility_cost(1e-9, duration_h)
    ceiling = quote.max_safe_mw
    if ceiling <= 0 or not np.isfinite(ceiling):
        return decide(model, 0.0, duration_h, landed_now_rs_kwh,
                      landed_later_rs_kwh, **kw)
    best = None
    for d in np.linspace(ceiling / steps, ceiling, steps):
        dec = decide(model, float(d), duration_h, landed_now_rs_kwh,
                     landed_later_rs_kwh, **kw)
        if dec.acts and (best is None or dec.net_benefit_rs > best.net_benefit_rs):
            best = dec
    if best is not None:
        return best
    return decide(model, float(ceiling), duration_h, landed_now_rs_kwh,
                  landed_later_rs_kwh, **kw)


def virtual_battery(model) -> dict:
    """Market representation of safe process flexibility.

    NOT a physical battery. It cannot export to the grid, it cannot serve any
    load but its own, and its 'capacity' is inventory that exists to buffer
    production. The label matters: quoting this as battery capacity is the
    single easiest way to lose a room full of power engineers.
    """
    # A model that already has a validated figure keeps it. Recomputing here
    # with a different convention would silently contradict published numbers —
    # which is exactly the class of error this codebase keeps catching.
    own = getattr(model, "virtual_battery", None)
    if callable(own):
        vb = own()
        return {
            "power_mw": vb["power_mw"], "duration_h": vb["duration_h"],
            "energy_mwh": vb["energy_mwh"],
            "label": "Virtual-battery representation of process flexibility",
            "caveat": ("This is a market representation of safe process "
                       "flexibility, not a change in the plant's primary "
                       "function, and not a physical battery. It cannot export "
                       "to the grid."),
            "data_status": model.data_status(),
        }
    env = model.get_operating_envelope()
    curve = model.get_power_curve()
    inv = model.get_inventory_state()
    power = max(0.0, curve(env.design) - curve(env.floor))
    rate_gap = max(1e-9, env.design - env.floor)
    hours = inv["usable_below"] / rate_gap if rate_gap > 0 else 0.0
    return {
        "power_mw": power,
        "duration_h": hours,
        "energy_mwh": power * hours,
        "label": "Virtual-battery representation of process flexibility",
        "caveat": ("This is a market representation of safe process "
                   "flexibility, not a change in the plant's primary function, "
                   "and not a physical battery. It cannot export to the grid."),
        "data_status": model.data_status(),
    }
