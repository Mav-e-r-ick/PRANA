"""Regression tests. Each one pins a claim made in the submission pack.

    python -m pytest tests -q          (or: python tests/test_prana.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prana import agent, data, tariff, twins                      # noqa: E402
from prana.backtest import (alt_supply_cost_rs, mcp_only_penalty,  # noqa: E402
                            wear_cost_rs,  # noqa: E402
                            verify_schedule)
from prana.config import DEMO_DATE, DT_H, SiteConfig              # noqa: E402
from prana.optimizer import Constraint, optimize_day              # noqa: E402


# --------------------------------------------------------------- twin physics
def test_power_curve_is_convex_and_increasing():
    for t in twins.default_fleet():
        qs = np.linspace(t.q_min_per_h, t.q_max_per_h, 200)
        p = np.array([t.power_mw(q) for q in qs])
        assert np.all(np.diff(p) > -1e-9), f"{t.kind}: power not increasing"
        assert np.all(np.diff(p, 2) > -1e-6), f"{t.kind}: power not convex"


def test_sec_is_u_shaped_for_quadratic_twins():
    """SEC minimum at design point is what makes flexibility genuinely costly
    in BOTH directions. If SEC fell monotonically, turn-down would be free."""
    for t in twins.default_fleet():
        if t.power_fn is not None:
            continue                                  # pipeline is monotone
        sec = [t.sec_per_unit(q)
               for q in np.linspace(t.q_min_per_h, t.q_max_per_h, 200)]
        assert np.argmin(sec) not in (0, len(sec) - 1), f"{t.kind}: SEC not U-shaped"


def test_tangent_envelope_never_overstates_power():
    """max-of-tangents must LOWER-bound a convex function. If it ever exceeded
    the true curve the MILP would forbid feasible operating points."""
    for t in twins.default_fleet():
        tans = t.tangents()
        for q in np.linspace(t.q_min_per_h, t.q_max_per_h, 300):
            assert max(s * q + i for s, i in tans) <= t.power_mw(q) + 1e-9


def test_linearization_error_under_one_percent():
    for t in twins.default_fleet():
        assert t.max_linearization_error() < 0.01, t.kind


def test_flexibility_cost_is_positive_and_rises_with_depth():
    grid = np.array([1.0, 2.0, 3.0, 4.0])
    for t in twins.default_fleet():
        phi = t.flexibility_cost_curve(grid, 4.0)
        finite = phi[np.isfinite(phi)]
        assert np.all(finite > 0), f"{t.kind}: free flexibility"
        assert np.all(np.diff(finite) > 0), f"{t.kind}: phi not increasing"


def test_chloralkali_convexity_matches_the_cell_voltage_law():
    """The quadratic coefficient must match what V = V0 + k*i predicts. If the
    twin drifts away from the electrochemistry, the central claim is dead."""
    import numpy as _np
    V0, k, i_des = 2.35, 0.135, 5.0
    xs = _np.linspace(0.40, 1.08, 200)
    rel = _np.array([((V0 + k*x*i_des) * x*i_des) / ((V0 + k*i_des) * i_des)
                     for x in xs])
    A = _np.vstack([_np.ones_like(xs), xs, xs**2]).T
    a0, a1, a2 = _np.linalg.lstsq(A, rel, rcond=None)[0]
    c = twins.chloralkali()
    assert abs(c.coef_c - a2) < 0.05, f"twin a2={c.coef_c} vs theory {a2:.3f}"
    assert abs(a0) < 0.02, "a pure cell must have no fixed term"


def test_chloralkali_sec_minimum_is_below_design():
    """The property that makes it the best flexibility asset in India: turning
    down IMPROVES specific energy. Every other twin here pays to turn down."""
    import numpy as _np
    c = twins.chloralkali()
    xs = _np.linspace(c.x_min, c.x_max, 300)
    sec = _np.array([c.sec_per_unit(x * c.q_nom_per_h) for x in xs])
    x_star = xs[int(_np.argmin(sec))]
    assert 0.45 < x_star < 0.65, f"SEC minimum at {x_star:.2f}, expected ~0.53"
    assert abs(x_star - (c.coef_a / c.coef_c) ** 0.5) < 0.05  # theory sqrt(a0/a2)
    assert c.sec_per_unit(c.q_nom_per_h) > sec.min()


def test_chloralkali_never_shuts_down_and_respects_safety_floor():
    """H2-in-Cl2 is an explosion hazard, not a cost. It must be a hard bound."""
    c = twins.chloralkali()
    assert c.can_shut_down is False, "a membrane cell house is never de-energised"
    assert c.x_min >= 0.35, "below ~40% current density H2 crosses into Cl2"


def test_chloralkali_site_solves_and_verifies():
    market = data.load_market()
    d = data.day(market, DEMO_DATE)
    site = SiteConfig(name="Chlor-alkali complex", base_load_mw=12.0)
    site.tariff.contract_demand_mw = 85.0
    fl = twins.fleet_chloralkali()
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fl, q, d["hour"].to_numpy(), site,
                     dam_price=d["dam"].to_numpy(float), time_limit_s=90)
    assert s.status == "Optimal"
    assert s.max_deviation_mw < 1e-6
    assert verify_schedule(s, fl, site, DEMO_DATE) == []
    # the cell house must never be driven below the safety floor
    qq = s.asset_production[fl[0].name]
    assert qq.min() >= fl[0].q_min_per_h - 1e-4


def _ca_day():
    """Solved chlor-alkali demo day, shared by the constraint tests below."""
    d = data.day(data.load_market(), DEMO_DATE)
    site = SiteConfig(name="CA", base_load_mw=12.0)
    site.tariff.contract_demand_mw = 92.0
    fl = twins.fleet_chloralkali()
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fl, q, d["hour"].to_numpy(), site,
                     dam_price=d["dam"].to_numpy(float), time_limit_s=90)
    return s, fl[0], site, d


def test_chlorine_consumer_not_the_cell_sets_the_floor():
    """The correction the engineering panel called non-negotiable.

    Chlorine is stoichiometric and unstorable, so the downstream consumer's
    turndown -- not the cell's H2-in-Cl2 interlock -- is what limits the shed.
    If this ever regresses, the model is optimizing a plant that cannot exist.
    """
    s, c, _, _ = _ca_day()
    assert c.coproduct_ratio > 0, "chlorine balance has been removed"
    q = s.asset_production[c.name]
    sink_floor_q = c.sink_min_per_h / c.coproduct_ratio
    assert sink_floor_q > c.q_min_per_h, "test is vacuous: sink floor below cell floor"
    assert q.min() >= sink_floor_q - 1e-4, (
        f"cell ran at {q.min():.2f} t/h, starving the Cl2 consumer which needs "
        f"{sink_floor_q:.2f} t/h of production")


def test_chlorine_dump_is_capped_and_charged():
    s, c, _, _ = _ca_day()
    dmp = s.coproduct_dump[c.name]
    assert dmp.max() <= c.dump_max_per_h + 1e-6, "bleach plant over capacity"
    # whatever is dumped must be paid for, at the stated rate
    expected = c.dump_cost_per_unit * float(dmp.sum()) * DT_H
    assert abs(s.dump_cost_rs - expected) < 1.0


def test_setpoint_movement_is_charged_and_budgeted():
    """Membranes are consumed by movement. Free cycling is how these models
    flatter themselves, so both the price and the cap are asserted here."""
    s, c, _, _ = _ca_day()
    assert c.cycling_cost_rs_per_unit > 0, "cycling has been made free again"
    q = s.asset_production[c.name]
    travel = float(np.sum(np.abs(np.diff(q))))
    assert travel <= c.max_total_variation + 1e-3, "movement budget breached"
    assert abs(s.cycling_cost_rs - c.cycling_cost_rs_per_unit * travel) < 1.0


def test_wear_costs_fall_on_prana_not_the_baseline():
    """A flat schedule pays no wear. If the comparison ever credits PRANA with
    a saving it did not net these out of, it is rigged."""
    s, c, _, _ = _ca_day()
    fl = [c]
    assert wear_cost_rs(s, fl) > 0, "flexible schedule should incur wear"
    flat = replace(s, asset_production={c.name: np.full(96, c.q_nom_per_h)},
                   coproduct_dump={c.name: np.zeros(96)})
    assert wear_cost_rs(flat, fl) == 0.0


def test_ending_the_day_short_is_never_an_arbitrage():
    """Terminal inventory is soft so a real outage stays solvable. Softening it
    must NOT open a hole: on a normal day the buffer must come back whole."""
    s, c, _, _ = _ca_day()
    assert s.terminal_shortfall[c.name] < 1e-3, (
        "the optimizer ended the day short with no outage to force it — the "
        "shortfall penalty is too cheap")


def test_a_train_outage_is_a_derate_not_a_trip():
    """'Rectifier B tripped' removes a train's capacity; it does not command
    minimum stable load. Pinning at q_min starves the Cl2 consumer and turns a
    routine outage into a spurious infeasibility."""
    from prana.optimizer import Constraint
    d = data.day(data.load_market(), DEMO_DATE)
    site = SiteConfig(name="CA", base_load_mw=12.0)
    site.tariff.contract_demand_mw = 85.0
    c0 = twins.chloralkali()
    assert c0.n_trains > 1
    assert c0.derate_floor_per_h > c0.sink_min_per_h / c0.coproduct_ratio, (
        "one train out must still feed the chlorine consumer")
    fl = twins.fleet_chloralkali()
    cons = [Constraint(kind="outage", asset=fl[0].name, start_block=56,
                       end_block=84, source="rules")]
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fl, q, d["hour"].to_numpy(), site,
                     dam_price=d["dam"].to_numpy(float), constraints=cons,
                     time_limit_s=90)
    assert s.status == "Optimal", "a single-train outage must remain solvable"
    qq = s.asset_production[fl[0].name]
    assert qq[56:84].max() <= fl[0].derate_floor_per_h + 1e-4
    assert verify_schedule(s, fl, site, DEMO_DATE) == []


def test_optimizing_on_mcp_costs_real_money():
    """The central claim, tested the only valid way: build both schedules, settle
    BOTH at the true landed bill, and measure the gap in rupees. Comparing peak
    MW with the demand charge zeroed is NOT valid -- the peak variable is
    unpriced there, so any difference is solver degeneracy."""
    from prana.forecast import perfect_foresight
    market = data.load_market()
    d = data.day(market, DEMO_DATE)
    site = SiteConfig(name="CA", base_load_mw=12.0)
    site.tariff.contract_demand_mw = 92.0
    r = mcp_only_penalty(twins.fleet_chloralkali, perfect_foresight(d),
                         d["hour"].to_numpy(), d["rtm"].to_numpy(float),
                         d["dam"].to_numpy(float), site)
    assert r["penalty_rs"] > 0, "landed-cost optimization must beat MCP-only"
    assert r["landed_rs"] < r["mcp_only_rs"]


def test_ammonia_cannot_be_tripped_and_is_slow():
    """The two facts that define the archetype. If either ever flips, the twin
    no longer describes a synthesis loop."""
    a = twins.ammonia()
    assert a.can_shut_down is False, "a synthesis loop is never tripped on price"
    assert a.ramp_frac_per_block * 400 <= 5.0, "loop ramp must stay single-digit %/h"
    assert a.x_min >= 0.6, "loop stability floor"


def test_ammonia_is_the_deepest_and_slowest_battery():
    """Portfolio argument: ammonia is long-duration, the electrolyser is fast.
    If they ever converge, there is no case for a portfolio of archetypes."""
    a, e = twins.ammonia(), twins.electrolyser()
    assert a.virtual_battery()["duration_h"] > 5 * e.virtual_battery()["duration_h"]
    assert a.ramp_frac_per_block < e.ramp_frac_per_block / 10


def test_every_archetype_is_convex_and_well_linearized():
    for t in twins.all_archetypes():
        assert t.max_linearization_error() < 0.01, t.kind
        qs = np.linspace(t.q_min_per_h, t.q_max_per_h, 150)
        p = np.array([t.power_mw(q) for q in qs])
        assert np.all(np.diff(p, 2) > -1e-6), f"{t.kind} not convex"


def test_fertilizer_site_solves_and_verifies():
    market = data.load_market()
    d = data.day(market, DEMO_DATE)
    site = SiteConfig(name="Ammonia-urea complex", base_load_mw=25.0)
    site.tariff.contract_demand_mw = 52.0
    fl = twins.fleet_fertilizer()
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fl, q, d["hour"].to_numpy(), site,
                     dam_price=d["dam"].to_numpy(float), time_limit_s=90)
    assert s.status == "Optimal"
    assert s.max_deviation_mw < 1e-6
    assert verify_schedule(s, fl, site, DEMO_DATE) == []


def test_pipeline_flexibility_is_costlier_than_electrolyser():
    """The cube law must show up as a materially steeper curve. This is the
    claim the Twin tab makes visually."""
    grid = np.array([3.0])
    fleet = {t.kind: t for t in twins.default_fleet()}
    e = fleet["electrolyser"].flexibility_cost_curve(grid, 4.0)[0]
    p = fleet["pipeline"].flexibility_cost_curve(grid, 4.0)[0]
    assert p > 5 * e, f"pipeline {p:.0f} vs electrolyser {e:.0f} Rs/MWh"


def test_deep_long_shed_is_infeasible_somewhere():
    """phi must return inf where the buffer cannot cover the window; a curve
    that is finite everywhere would be promising flexibility that doesn't exist."""
    t = [x for x in twins.default_fleet() if x.kind == "electrolyser"][0]
    grid = np.linspace(0.5, t.power_mw(t.q_nom_per_h), 40)
    assert np.any(~np.isfinite(t.flexibility_cost_curve(grid, 12.0)))


# -------------------------------------------------------------------- tariff
def test_verified_merc_figures_have_not_drifted():
    """Pinned to MERC Case 75 of 2025 (post-remand), HT I(A) HT-Industry, EHV,
    FY2026-27. The 25-Jun-2025 order was QUASHED by the Bombay HC; these come
    from the operative post-remand order. If someone edits config.py, this fails."""
    cfg = SiteConfig().tariff
    assert cfg.demand_charge_rs_kva_month == 650.0
    assert cfg.retail_energy_rs_kvah == 8.44
    assert cfg.tod_peak_mult == 1.20                 # +20%, 17:00-24:00
    assert cfg.tod_solar_mult_apr_sep == 0.85        # -15%
    assert cfg.tod_solar_mult_oct_mar == 0.75        # -25%
    assert cfg.tod_offpeak_mult == 1.00, "the night rebate was removed, para 18.13"


def test_tod_peak_window_runs_to_midnight_and_night_is_flat():
    """Two things a trade-press summary would get wrong: the peak window is 7
    hours (17:00-24:00), and there is no longer a night rebate."""
    cfg = SiteConfig().tariff
    h = np.arange(96) // 4
    m = tariff.tod_multiplier(h, cfg, month=7)
    assert m[80] == cfg.tod_peak_mult, "20:00 must be peak"
    assert m[92] == cfg.tod_peak_mult, "23:00 must STILL be peak"
    assert m[12] == 1.00, "03:00 must be flat — night rebate removed"
    assert m[52] == cfg.tod_solar_mult_apr_sep, "13:00 July must be solar rebate"


def test_tod_solar_rebate_is_seasonal():
    cfg = SiteConfig().tariff
    h = np.arange(96) // 4
    jul = tariff.tod_multiplier(h, cfg, month=7)
    dec = tariff.tod_multiplier(h, cfg, month=12)
    assert dec[52] < jul[52], "Oct-Mar rebate (-25%) must exceed Apr-Sep (-15%)"



def test_non_energy_is_a_large_share_of_landed_cost():
    cfg = SiteConfig().tariff
    lc = tariff.landed_cost(np.full(96, 3000.0), np.arange(96) // 4, cfg)
    assert 0.30 < lc.non_energy_share < 0.75


def test_demand_charge_is_material_per_mw():
    cfg = SiteConfig().tariff
    assert tariff.demand_charge_rs_per_mw_day(cfg) > 10_000


def test_ratchet_floor_applies():
    cfg = SiteConfig().tariff
    e = np.full(96, 1.0)
    lc = tariff.landed_cost(np.full(96, 3000.0), np.arange(96) // 4, cfg)
    low = tariff.bill_summary(e, lc, 10.0, cfg)
    assert low["billing_peak_mw"] == tariff.ratchet_floor_mw(cfg)


# ----------------------------------------------------------------------- DSM
def test_dsm_rate_is_never_below_rtm():
    df = data.load_market()
    r = df["rtm"].to_numpy(float)
    a = df["dam"].to_numpy(float)
    assert np.all(data.dsm_rate(a, r) >= r - 1e-9)


def test_dsm_binds_in_almost_all_blocks():
    """The claim: >= RTM in 99.9% of blocks. Assert it on the real panel."""
    df = data.load_market()
    r, a = df["rtm"].to_numpy(float), df["dam"].to_numpy(float)
    assert float(np.mean(data.dsm_rate(a, r) >= r)) > 0.999


# ----------------------------------------------------------------- optimizer
def _solve(date=DEMO_DATE, cons=None, **site_kw):
    market = data.load_market()
    d = data.day(market, date)
    hours = d["hour"].to_numpy()
    rtm = d["rtm"].to_numpy(float)
    site = SiteConfig(**site_kw)
    fleet = twins.default_fleet()
    q = {x: rtm.copy() for x in (0.10, 0.50, 0.90)}
    s = optimize_day(fleet, q, hours, site, dam_price=d["dam"].to_numpy(float),
                     constraints=cons, time_limit_s=90)
    return d, s, fleet, site


def test_solver_reaches_optimal_and_never_deviates():
    _, s, _, _ = _solve()
    assert s.status == "Optimal"
    assert s.max_deviation_mw < 1e-6, "deviation must never be profitable"


def test_schedule_survives_true_physics_verification():
    _, s, fleet, site = _solve()
    assert verify_schedule(s, fleet, site, DEMO_DATE) == []


def test_prana_beats_steady_state_net_of_bought_in_product():
    market = data.load_market()
    d = data.day(market, DEMO_DATE)
    hours, rtm = d["hour"].to_numpy(), d["rtm"].to_numpy(float)
    site = SiteConfig()
    q = {x: rtm.copy() for x in (0.10, 0.50, 0.90)}
    lc = tariff.landed_cost(rtm, hours, site.tariff)
    out = {}
    for flat in (True, False):
        fl = twins.default_fleet()
        s = optimize_day(fl, q, hours, site, dam_price=d["dam"].to_numpy(float),
                         flat_baseline=flat, time_limit_s=90)
        b = tariff.bill_summary(s.total_power_mw * DT_H, lc, s.peak_mw, site.tariff)
        out[flat] = b["total_rs"] + alt_supply_cost_rs(s, fl)
    assert out[False] < out[True], "optimized must beat steady state"


def test_agent_outage_constraint_actually_binds():
    """An extracted constraint must change the schedule, or sign-off is theatre."""
    _, base, fleet, _ = _solve()
    asu = [t for t in fleet if t.kind == "asu"][0]
    c = Constraint(kind="outage", asset=asu.name, start_block=56, end_block=72)
    _, s, _, _ = _solve(cons=[c])
    q = s.asset_production[asu.name][56:72]
    assert np.allclose(q, asu.q_min_per_h, atol=1e-3), \
        "ASU should be held at minimum stable load through the outage window"


def test_demand_charge_changes_the_answer():
    """The headline claim of Problem 3: modelling the demand charge changes the
    dispatch. If this ever passes trivially, the claim is dead."""
    _, s_real, fleet_r, _ = _solve()
    market = data.load_market()
    d = data.day(market, DEMO_DATE)
    site0 = SiteConfig()
    site0.tariff.demand_charge_rs_kva_month = 0.0
    fl0 = twins.default_fleet()
    q = {x: d["rtm"].to_numpy(float) for x in (0.10, 0.50, 0.90)}
    s0 = optimize_day(fl0, q, d["hour"].to_numpy(), site0,
                      dam_price=d["dam"].to_numpy(float), time_limit_s=90)
    assert s0.peak_mw > s_real.peak_mw + 1.0, \
        "zeroing the demand charge must raise the peak"


# --------------------------------------------------------------------- agent
def test_agent_extracts_windowed_outage_from_wrapped_text():
    fleet = twins.default_fleet()
    ex = agent.elicit(
        "Compressor B on the air separation unit is down for bearing\n"
        "replacement from 14:00 to 18:00 today.", fleet)
    outs = [c for c in ex.constraints if c.kind == "outage"]
    assert outs and outs[0].start_block == 56 and outs[0].end_block == 72


def test_agent_extracts_inventory_floor_with_units():
    fleet = twins.default_fleet()
    ex = agent.elicit("LOX tank level must be maintained above 120 t.", fleet)
    f = [c for c in ex.constraints if c.kind == "inventory_floor"]
    assert f and abs(f[0].value - 120.0) < 1e-6


def test_agent_flags_ambiguity_instead_of_guessing():
    fleet = twins.default_fleet()
    ex = agent.elicit("Ensure the reformer feed is never interrupted.", fleet)
    assert ex.unresolved and not ex.constraints


def test_trip_utterance_is_anchored_to_now_not_midnight():
    """'Compressor B tripped, back by 21:00' at 14:00 is a 7-hour outage, not a
    21-hour one. Anchoring it at midnight triples the modelled outage and badly
    misprices the schedule."""
    fleet = twins.default_fleet()
    ex = agent.perturb("Compressor B tripped, back by 21:00.", fleet,
                       now_block=56)                      # 14:00
    c = [x for x in ex.constraints if x.kind == "outage"][0]
    assert (c.start_block, c.end_block) == (56, 84)


def test_explicit_range_ignores_the_clock():
    fleet = twins.default_fleet()
    ex = agent.perturb("Electrolyser isolated 02:00 until 05:00.", fleet,
                       now_block=56)
    c = [x for x in ex.constraints if x.kind == "outage"][0]
    assert (c.start_block, c.end_block) == (8, 20)


def test_source_has_no_control_characters():
    """A shell heredoc once turned a regex '\\b' into a literal backspace byte,
    silently disabling a word boundary. Cheap to catch, expensive to miss."""
    root = Path(__file__).resolve().parents[1]
    for p in root.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        raw = p.read_bytes()
        for ctrl in (0x07, 0x08, 0x0B, 0x0C):
            assert bytes([ctrl]) not in raw, f"{p.name} contains {hex(ctrl)}"


def test_agent_requires_signoff():
    ex = agent.elicit("Pipeline pumps offline 19:00 to 22:00.",
                      twins.default_fleet())
    assert ex.requires_signoff is True


# ---------------------------------------------------------------------- data
def test_market_panel_is_complete_and_respects_the_cap_in_force():
    """Not a flat 10,000 ceiling: the cap stepped 20,000 -> 12,000 -> 10,000
    inside this window. Every block must respect the cap on ITS OWN date."""
    df = data.load_market()
    assert len(df) > 150_000
    assert df["rtm"].min() >= 0.0
    assert len(data.available_days(df)) > 1_500
    assert data.check_caps(df).empty, "price above the cap in force on that date"


def test_current_regime_is_capped_at_ten_thousand():
    df = data.load_market()
    cur = df[df["ts"] >= "2023-04-01"]
    assert cur["rtm"].max() <= 10_000.0 and cur["dam"].max() <= 10_000.0


def test_demo_day_has_the_spread_the_pitch_claims():
    d = data.day(data.load_market(), DEMO_DATE)
    r = d["rtm"].to_numpy(float)
    assert r.min() <= 5 and r.max() >= 9_990


# ------------------------------------------------------- plant data loader
def test_plant_loader_is_column_map_driven_not_hardcoded():
    """The loader must work from a caller-supplied mapping, never from any
    particular site's column names. A loader that only reads the sheet it was
    written against is a transcription, and it is how a model gets overfitted
    to its first site.

    This is asserted structurally rather than by listing real column names,
    because naming a real site's columns in a test would put them in the repo
    -- which is the very thing the test exists to prevent.
    """
    from dataclasses import fields
    from prana.plantdata import ColumnMap
    cm = ColumnMap(date="D", site_total="T", grid_import="G",
                   units={"x": "X"}, captive=("A", "B"))
    assert set(cm.energy_columns()) == {"T", "G", "X", "A", "B"}

    # No field may default to a real column name: every optional field must
    # default to None or empty, so nothing site-specific can be baked in.
    import dataclasses
    for f in fields(ColumnMap):
        if f.name == "date":
            continue
        if f.default_factory is not dataclasses.MISSING:   # dict/list defaults
            assert not f.default_factory(), f"{f.name} carries a baked-in default"
        else:
            assert f.default in (None, ()), f"{f.name} carries a baked-in default"

    # And the module source must contain no meter-column-shaped literals.
    src = (Path(__file__).resolve().parents[1] / "prana" / "plantdata.py").read_text(
        encoding="utf-8")
    for shape in ("(MWH)", "(MWh)", "Consumption (", "Import(", "kVAh)"):
        assert shape not in src, f"{shape!r} looks like a site's column name"


def test_plant_loader_rejects_a_bad_map_loudly():
    """Silent failure on a mis-mapped column is how a wrong number reaches a
    slide. It must raise, and it must say what the sheet actually contains."""
    import pandas as pd, tempfile, os
    from prana.plantdata import ColumnMap, load_plant_sheet
    fd, path = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"],
                  "kWh": [10.0, 11.0]}).to_csv(path, index=False)
    try:
        try:
            load_plant_sheet(path, ColumnMap(date="Date", site_total="NOPE"))
            raise AssertionError("should have raised on a missing column")
        except KeyError as exc:
            assert "kWh" in str(exc), "error must list the columns actually present"
    finally:
        os.unlink(path)


def test_plant_profile_always_declares_what_it_cannot_ground():
    """A meter sheet has no production column, so it can never ground the power
    curve. That limitation must travel with the numbers at runtime."""
    import pandas as pd, tempfile, os
    from prana.plantdata import ColumnMap, load_plant_sheet
    fd, path = tempfile.mkstemp(suffix=".csv"); os.close(fd)
    pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=40, freq="D"),
                  "total": [240.0] * 40, "grid": [24.0] * 40}).to_csv(path, index=False)
    try:
        p = load_plant_sheet(path, ColumnMap(date="Date", site_total="total",
                                             grid_import="grid"), name="t")
        blob = " ".join(p.cannot_ground()).lower()
        assert "power curve" in blob and "turndown" in blob
        assert "intraday" in blob, "daily data must disclaim intraday claims"
        assert abs(p.period_hours - 24.0) < 1e-6      # inferred, not assumed
        assert abs(p.load_mw["site_total"] - 10.0) < 1e-9  # 240 MWh/24h = 10 MW
        assert abs(p.grid_share - 0.10) < 1e-9
    finally:
        os.unlink(path)


if __name__ == "__main__":
    import traceback

    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    passed = failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {name}: {exc}")
            traceback.print_exc(limit=1)
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(fns)} total")
    sys.exit(1 if failed else 0)
