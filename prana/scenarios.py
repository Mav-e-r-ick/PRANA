"""Three demo scenarios — two of which end in DO NOTHING.

The point of this file is that the same engine, given the same high electricity
price, returns three different answers depending on what the *process* says. If
a demo only ever shows the system agreeing to act, it has demonstrated nothing.

    A · ECONOMIC FLEXIBILITY   price high, process can move cheaply  -> SHIFT
    B · PROCESS COST TOO HIGH  price high, moving costs more         -> DO NOTHING
    C · HARD CONSTRAINT        price high, downstream unit is fixed  -> DO NOTHING

Only the process configuration changes between them. The market inputs, the
decision logic and the safety architecture are identical.
"""
from __future__ import annotations

from dataclasses import dataclass

from .decision import FlexibilityDecision, best_available_shift, decide
from .generic import GenericProcess

# Market conditions shared by all three, so the only variable is the process.
# Evening peak against a midday trough — the shape from the real IEX panel.
PEAK_RS_KWH = 9.20
OFFPEAK_RS_KWH = 2.40
WINDOW_H = 2.0


@dataclass
class Scenario:
    key: str
    title: str
    subtitle: str
    expected_action: str
    model: GenericProcess

    def run(self) -> FlexibilityDecision:
        return best_available_shift(
            self.model, WINDOW_H, PEAK_RS_KWH, OFFPEAK_RS_KWH)


def scenario_a() -> Scenario:
    """Healthy buffer, modest fixed load, downstream unit can turn down."""
    return Scenario(
        key="A", title="Economic flexibility",
        subtitle="High price · process can move · penalty below the benefit",
        expected_action="SHIFT",
        model=GenericProcess(
            name="Illustrative continuous process — flexible",
            design_load_mw=100.0, design_rate_per_h=50.0,
            min_stable_pct=60.0, max_load_pct=108.0,
            ramp_up_pct_per_h=40.0, ramp_down_pct_per_h=40.0,
            inventory_now=900.0, inventory_min=200.0, inventory_max=1800.0,
            downstream_draw_per_h=50.0,
            fixed_load_share=0.06,           # little standby load => cheap to shed
            downstream_min_pct=55.0,
        ),
    )


def scenario_b() -> Scenario:
    """Same price. Large fixed load and a wear charge make moving uneconomic.

    This is the scenario that proves the system is not a price-chaser.
    """
    return Scenario(
        key="B", title="Process cost exceeds benefit",
        subtitle="High price · flexibility exists · but the process charges more",
        expected_action="DO NOTHING",
        model=GenericProcess(
            name="Illustrative continuous process — costly to move",
            design_load_mw=100.0, design_rate_per_h=50.0,
            min_stable_pct=80.0, max_load_pct=106.0,
            ramp_up_pct_per_h=40.0, ramp_down_pct_per_h=40.0,
            inventory_now=900.0, inventory_min=200.0, inventory_max=1800.0,
            downstream_draw_per_h=50.0,
            # Mostly standby load, so turning down saves little power, and a
            # heavy wear charge on every unit of setpoint travel. The move is
            # entirely FEASIBLE here — it is simply not worth doing, which is
            # the distinction this scenario exists to demonstrate.
            fixed_load_share=0.55,
            wear_cost_rs_per_unit_moved=45_000.0,
            production_penalty_rs_per_unit=8_000.0,
        ),
    )


def scenario_c() -> Scenario:
    """Same price, real flexibility on paper — but a downstream unit is fixed.

    The hard gate fires before any economics are computed.
    """
    return Scenario(
        key="C", title="Hard production constraint",
        subtitle="High price · flexibility on paper · downstream unit cannot follow",
        expected_action="DO NOTHING",
        model=GenericProcess(
            name="Illustrative continuous process — downstream locked",
            design_load_mw=100.0, design_rate_per_h=50.0,
            min_stable_pct=60.0, max_load_pct=108.0,
            ramp_up_pct_per_h=40.0, ramp_down_pct_per_h=40.0,
            inventory_now=900.0, inventory_min=200.0, inventory_max=1800.0,
            downstream_draw_per_h=50.0, fixed_load_share=0.06,
            hard_constraint_active=True,
            hard_constraint_reason=("downstream unit on fixed take — "
                                    "co-product cannot be stored"),
        ),
    )


ALL = {"A": scenario_a, "B": scenario_b, "C": scenario_c}


def run_all() -> list[tuple[Scenario, FlexibilityDecision]]:
    return [(s, s.run()) for s in (f() for f in ALL.values())]


if __name__ == "__main__":                                  # pragma: no cover
    import sys
    try:                                    # a Windows console defaults to cp1252
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"Market: peak ₹{PEAK_RS_KWH}/kWh vs off-peak ₹{OFFPEAK_RS_KWH}/kWh, "
          f"{WINDOW_H:.0f} h window — identical in all three.\n")
    for s, d in run_all():
        ok = "OK " if d.action == s.expected_action else "!! "
        print(f"{ok}{s.key} · {s.title}")
        print(f"    expected {s.expected_action:<11} got {d.action}")
        print(f"    {d.reason}")
        if d.acts:
            print(f"    benefit ₹{d.electricity_benefit_rs:,.0f}  "
                  f"process cost ₹{d.process_cost_rs:,.0f}  "
                  f"net ₹{d.net_benefit_rs:,.0f}")
        print()
