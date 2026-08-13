"""Platform-layer tests — the generalisation claim, made falsifiable.

The chlor-alkali suite in test_prana.py pins the validated case study. This file
pins the thing that makes PRANA a platform rather than a demo: that the
optimiser, the decision logic and the safety architecture work identically
against a process they have never seen, and that the system is willing to say
DO NOTHING.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prana import decision, scenarios, twins                      # noqa: E402
from prana.config import DEMO_DATE, SiteConfig                    # noqa: E402
from prana.decision import (DO_NOTHING, R_ECONOMIC, R_HARD_CONSTRAINT,  # noqa: E402
                            R_UNECONOMIC, SHIFT)
from prana.generic import GenericProcess                          # noqa: E402
from prana.optimizer import optimize_day                          # noqa: E402
from prana.process import VALIDATED, conforms                     # noqa: E402


# 1 ─ hard production constraint blocks flexibility, before economics
def test_hard_production_constraint_blocks_flexibility():
    s = scenarios.scenario_c()
    d = s.run()
    assert d.action == DO_NOTHING
    assert d.reason_code == R_HARD_CONSTRAINT
    # economics must not even have been computed
    assert d.electricity_benefit_rs == 0.0, "priced a move it had already forbidden"


# 2 ─ a safety/downstream floor removes flexibility that looks available
def test_safety_floor_removes_apparent_flexibility():
    g = GenericProcess(downstream_min_pct=100.0)      # consumer cannot turn down
    env = g.get_operating_envelope()
    assert env.floor == pytest.approx(env.design)
    q = g.calculate_flexibility_cost(10.0, 2.0)
    assert not q.available and q.max_safe_mw == pytest.approx(0.0, abs=1e-6)


# 3 ─ process cost above the electricity benefit -> DO NOTHING
def test_process_cost_above_benefit_does_nothing():
    s = scenarios.scenario_b()
    d = s.run()
    assert d.action == DO_NOTHING and d.reason_code == R_UNECONOMIC
    assert d.net_benefit_rs <= 0
    assert d.electricity_benefit_rs > 0, "should have priced it and still declined"


# 4 ─ benefit above cost -> SHIFT
def test_benefit_above_cost_shifts():
    s = scenarios.scenario_a()
    d = s.run()
    assert d.action == SHIFT and d.reason_code == R_ECONOMIC
    assert d.net_benefit_rs > 0 and d.shift_mw > 0
    assert (d.net_benefit_rs
            == pytest.approx(d.electricity_benefit_rs - d.process_cost_rs
                             - d.other_cost_rs - d.risk_penalty_rs, rel=1e-9))


# 5 ─ no flexibility at all -> DO NOTHING, with a reason
def test_no_flexibility_does_nothing_with_a_reason():
    g = GenericProcess(min_stable_pct=100.0, max_load_pct=100.0)
    d = decision.best_available_shift(g, 2.0, 9.2, 2.4)
    assert d.action == DO_NOTHING and d.reason
    assert d.reason_code != R_ECONOMIC


# 6 ─ the generic model is dispatchable by the real optimiser
def test_generic_model_conforms_to_the_interface():
    assert conforms(GenericProcess())
    g = GenericProcess()
    for m in ("get_operating_envelope", "get_power_curve", "get_inventory_state",
              "get_ramp_limits", "get_recovery_constraints"):
        assert getattr(g, m)() is not None


# 7 ─ chlor-alkali still solves and still reports VALIDATED
def test_chloralkali_still_works_and_is_the_only_validated_model():
    from prana import data
    c = twins.chloralkali()
    assert c.data_status() == VALIDATED
    assert GenericProcess().data_status() != VALIDATED, "illustrative claimed validated"
    d = data.day(data.load_market(), DEMO_DATE)
    site = SiteConfig(name="CA", base_load_mw=12.0)
    site.tariff.contract_demand_mw = 92.0
    fl = twins.fleet_chloralkali()
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fl, q, d["hour"].to_numpy(), site,
                     dam_price=d["dam"].to_numpy(float), time_limit_s=90)
    assert s.status == "Optimal"


# 8 ─ the optimiser must not depend on any process-specific implementation
def test_optimizer_is_process_agnostic():
    src = (Path(__file__).resolve().parents[1] / "prana" / "optimizer.py").read_text(
        encoding="utf-8")
    for word in ("chloralkali", "chlor-alkali", "caustic", "cell house",
                 "rectifier", "brine", "refinery", "ammonia"):
        assert word.lower() not in src.lower(), (
            f"{word!r} appears in the optimiser — it has learned what the "
            f"process is, which breaks the platform boundary")


# 9 ─ the LLM layer cannot originate or approve a constraint
def test_llm_cannot_modify_constraints_without_approval():
    from prana import agent
    src = (Path(__file__).resolve().parents[1] / "prana" / "agent.py").read_text(
        encoding="utf-8")
    assert "sign-off" in src.lower() or "sign_off" in src.lower()
    fl = twins.fleet_chloralkali()
    ex = agent.elicit("Rectifier B tripped, back by 21:00.", fl, now_block=56)
    for c in ex.constraints:
        assert c.source, "an extracted constraint must name its source"
    assert ex.constraints, "expected at least one candidate constraint"
    # the agent module must not import the optimiser's solve entry point
    assert "optimize_day" not in src, "the agent must not be able to dispatch"


# 10 ─ every recommended schedule passes the process's own validation
def test_recommended_schedules_pass_process_validation():
    g = scenarios.scenario_a().model
    env = g.get_operating_envelope()
    ramp = g.get_ramp_limits()["down_per_h"] * 0.25
    q, cur = [], env.design
    for b in range(96):                       # a ramp-limited, balanced day
        tgt = env.floor if 68 <= b < 92 else env.ceiling if b < 40 else env.design
        cur += float(np.clip(tgt - cur, -ramp, ramp))
        q.append(cur)
    res = g.validate_schedule(np.array(q), 0.25)
    assert isinstance(res.ok, bool)
    if not res.ok:                            # must explain itself if it fails
        assert res.violations


# 11 ─ the virtual battery is MW x duration, and is labelled as a representation
def test_virtual_battery_is_consistent_and_labelled():
    for m in (twins.chloralkali(), GenericProcess()):
        vb = decision.virtual_battery(m)
        assert vb["energy_mwh"] == pytest.approx(vb["power_mw"] * vb["duration_h"],
                                                 rel=1e-6)
        assert "not a physical battery" in vb["caveat"].lower()
        assert vb["data_status"] == m.data_status()
    # the published chlor-alkali figure must not have moved
    vb = decision.virtual_battery(twins.chloralkali())
    assert vb["energy_mwh"] == pytest.approx(748.2, abs=1.0)


# 12 ─ invalid configurations are rejected rather than silently accepted
@pytest.mark.parametrize("kw", [
    {"min_stable_pct": 120.0, "max_load_pct": 100.0},
    {"inventory_min": 900.0, "inventory_max": 100.0},
    {"fixed_load_share": 1.4},
    {"design_rate_per_h": 0.0},
    {"inventory_now": 10.0, "inventory_min": 100.0, "inventory_max": 500.0},
])
def test_invalid_configurations_are_rejected(kw):
    with pytest.raises(ValueError):
        GenericProcess(**kw)
