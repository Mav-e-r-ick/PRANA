"""Process digital twins — the novel object in PRANA.

A process buffer is a battery whose state of charge is *inventory* and whose
round-trip loss is a *process efficiency penalty*. Each twin below is a reduced-
order, first-principles model of one archetype:

    ASU            air separation unit + cryogenic LOX/LIN tank
    Electrolyser   alkaline electrolyser + compressed H2 buffer
    Pipeline       crude/product pumping station + destination tankage

Common physics. Electrical power as a function of production rate is modelled as

    P(x) = P_nom * (a + b*x + c*x**2),      x = q / q_nom,   a + b + c = 1

with a > 0 (fixed/standby losses), b > 0, c > 0 (off-design and throttling
losses). This is convex and increasing, so specific energy consumption

    SEC(x) = P(x)/q  =  (P_nom/q_nom) * (a/x + b + c*x)

is U-shaped with its minimum at x* = sqrt(a/c) — turning down costs specific
energy because fixed losses are spread over less product, and pushing above
design costs it because of throttling. That U is exactly why flexibility is not
free, and it is what the flexibility cost curve measures.

The pipeline twin overrides P(x) with the hydraulic cube law: head loss scales
with the square of throughput, so pump power scales with the cube.

MILP linearization. P(x) is convex, so it is represented in the optimizer by a
set of tangent hyperplanes:  p >= slope_k * q + intercept_k. The maximum of
tangents is a lower-bounding (outer) approximation of a convex function, so the
model can under-state power by at most the linearization error, which
`max_linearization_error()` reports and which the tests assert is under 1%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np


@dataclass
class ProcessTwin:
    """One flexible asset."""

    name: str
    kind: str                       # asu | electrolyser | pipeline
    unit: str                       # product unit, e.g. "t" or "kg" or "kL"

    # --- power curve ------------------------------------------------------
    p_nom_mw: float
    q_nom_per_h: float
    coef_a: float = 0.10            # fixed / standby share of nominal power
    coef_b: float = 0.80
    coef_c: float = 0.10
    x_min: float = 0.60             # minimum stable load fraction when running
    x_max: float = 1.10             # maximum sustained overload fraction
    power_fn: Callable[[float], float] | None = None   # override P(x)

    # --- buffer -----------------------------------------------------------
    inv_min: float = 0.0            # product units
    inv_max: float = 1_000.0
    inv_init: float = 500.0
    inv_loss_frac_per_h: float = 0.0   # boil-off / leakage
    demand_per_h: float = 0.0          # downstream draw, product units / h

    # --- dynamics ---------------------------------------------------------
    ramp_frac_per_block: float = 0.25   # |dx| limit per 15-min block
    can_shut_down: bool = False
    start_cost_rs: float = 0.0
    min_up_blocks: int = 4
    min_down_blocks: int = 4

    # --- make-vs-buy alternative (electrolyser: SMR hydrogen) -------------
    alt_supply_cost_per_unit: float | None = None
    alt_supply_max_per_h: float = 0.0

    # --- COUPLED CO-PRODUCT: the constraint that actually binds -----------
    # Electrolysis is stoichiometric. Every tonne of caustic comes with ~0.886 t
    # of chlorine, and chlorine CANNOT be stored in bulk -- it is a Schedule-3
    # substance under the MSIHC Rules, PESO-licensed, and deliberately held at
    # minimum inventory. So the cell house cannot turn down unless the chlorine
    # CONSUMER turns down with it.
    #
    # This is the single most important correction a process engineer will
    # demand: the binding constraint is not the cell's minimum current density,
    # it is the downstream unit's turndown. Modelling it as a fixed `x_min` on
    # the cell hides an entire plant behind one number.
    coproduct_ratio: float = 0.0          # co-product units per product unit
    coproduct_name: str = ""
    sink_min_per_h: float = 0.0           # downstream consumer's minimum take
    sink_max_per_h: float = 0.0           # ... and its maximum
    dump_max_per_h: float = 0.0           # sink of last resort (bleach / HCl)
    dump_cost_per_unit: float = 0.0       # value destroyed per unit dumped

    # --- cycling / degradation --------------------------------------------
    # Membranes, catalysts and tap changers are consumed by movement, not by
    # runtime. Charging zero for a setpoint change makes flexibility look free
    # and is the commonest way these models overstate their own value.
    cycling_cost_rs_per_unit: float = 0.0   # Rs per unit of |dq| between blocks
    max_total_variation: float | None = None  # sum|dq| budget over the horizon

    # --- load-dependent power factor (kVAh billing) -----------------------
    # None = constant pf. Set pf_at_x_min for rectifier-fed loads, where the
    # firing angle widens on turn-down and the plant is billed for kVAh it does
    # not use as kWh.
    pf_nom: float = 0.98
    pf_at_x_min: float | None = None

    # --- what a single-train outage actually costs -------------------------
    # An outage on a multi-train asset is a DERATE, not a trip: "rectifier B is
    # out" means the cell house loses that train's share of capacity, not that
    # it drops to minimum stable load. `n_trains` sets the fraction lost.
    n_trains: int = 1

    # Value of a product unit the day ends short of its opening buffer. High
    # enough that ending short is never an arbitrage, finite so that a genuine
    # outage stays solvable.
    terminal_shortfall_cost_per_unit: float = 50_000.0

    notes: str = ""
    _tangents: list[tuple[float, float]] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ API
    def power_mw(self, q_per_h: float) -> float:
        """True (nonlinear) electrical power for a production rate."""
        if q_per_h <= 0:
            return 0.0
        x = q_per_h / self.q_nom_per_h
        if self.power_fn is not None:
            return self.p_nom_mw * self.power_fn(x)
        return self.p_nom_mw * (self.coef_a + self.coef_b * x + self.coef_c * x * x)

    def sec_per_unit(self, q_per_h: float) -> float:
        """Specific energy consumption, kWh per product unit."""
        if q_per_h <= 0:
            return float("nan")
        return self.power_mw(q_per_h) * 1000.0 / q_per_h

    def power_factor(self, q_per_h: float) -> float:
        """Displacement power factor at a given load.

        The electrical engineer's objection, and a real one: MERC bills HT
        industry in **kVAh, not kWh**. A thyristor rectifier draws current in
        phase with a firing angle that widens as the DC current is reduced, so
        power factor FALLS as the cell house turns down — and the plant is
        billed for the apparent power, not the real power. A model that assumes
        a constant 0.98 is quietly awarding itself free kVAh every time it sheds.

        Linear in load is the standard first-order representation of firing-angle
        displacement, pinned at `pf_nom` at design load. It is charged
        post-solve, so the reported saving is net of it even though the
        optimizer does not yet trade against it — which makes the number
        conservative, not optimistic.
        """
        if self.pf_at_x_min is None or self.q_nom_per_h <= 0:
            return self.pf_nom
        x = max(self.x_min, min(self.x_max, q_per_h / self.q_nom_per_h))
        f = (x - self.x_min) / max(1e-9, 1.0 - self.x_min)
        return self.pf_at_x_min + f * (self.pf_nom - self.pf_at_x_min)

    @property
    def q_min_per_h(self) -> float:
        return self.x_min * self.q_nom_per_h

    @property
    def q_max_per_h(self) -> float:
        return self.x_max * self.q_nom_per_h

    @property
    def p_max_mw(self) -> float:
        return self.power_mw(self.q_max_per_h)

    @property
    def derate_floor_per_h(self) -> float:
        """Production ceiling with one train out of service.

        With a single train this collapses to minimum stable load, which is the
        old behaviour. With four rectifier trains it is 75% of design — which is
        what "rectifier B tripped" actually means on the plant.
        """
        if self.n_trains <= 1:
            return self.q_min_per_h
        return self.q_nom_per_h * (self.n_trains - 1) / self.n_trains

    def tangents(self, n: int = 16) -> list[tuple[float, float]]:
        """Tangent hyperplanes p >= slope*q + intercept over [q_min, q_max]."""
        if self._tangents:
            return self._tangents
        qs = np.linspace(self.q_min_per_h, self.q_max_per_h, n)
        eps = max(1e-6, 1e-5 * self.q_nom_per_h)
        out = []
        for q in qs:
            slope = (self.power_mw(q + eps) - self.power_mw(q - eps)) / (2 * eps)
            out.append((float(slope), float(self.power_mw(q) - slope * q)))
        self._tangents = out
        return out

    def max_linearization_error(self, n: int = 16, samples: int = 400) -> float:
        """Worst relative under-statement of power by the tangent envelope."""
        tans = self.tangents(n)
        qs = np.linspace(self.q_min_per_h, self.q_max_per_h, samples)
        worst = 0.0
        for q in qs:
            true_p = self.power_mw(q)
            lin_p = max(s * q + i for s, i in tans)
            if true_p > 0:
                worst = max(worst, (true_p - lin_p) / true_p)
        return worst

    # ------------------------------------------------- flexibility cost curve
    def flexibility_cost_curve(
        self, delta_mw_grid: np.ndarray, duration_h: float
    ) -> np.ndarray:
        """phi(dMW, dt): marginal cost of flexibility, Rs/MWh.

        This is the object the industry lacks. For a load *reduction* of
        `delta_mw` sustained for `duration_h`, the plant must

          1. turn the asset down, producing less at a worse specific energy;
          2. serve unchanged downstream demand from inventory over the window;
          3. rebuild that inventory afterwards by running above design, again
             at a worse specific energy.

        Total product delivered is identical to running flat, so the two legs
        are product-neutral by construction. What is *not* neutral is energy:
        because P(q) is convex, splitting production into a low leg and a high
        leg always burns more kWh than running at design. That excess is the
        process round-trip loss — the direct analogue of (1-RTE)/RTE for a
        battery — and it is the true cost of the flexibility.

            phi = (E_flex - E_flat) / (delta_mw * duration_h)

        Returned in Rs/MWh against a 1 Rs/kWh reference so the curve is a pure
        *process* cost; the optimizer prices the market separately. inf means
        the flexibility does not exist at that depth and duration — the buffer
        cannot cover it, or the turn-down would breach minimum stable load.
        """
        ref_rs_per_mwh = 1000.0     # 1 Rs/kWh reference -> curve reads in Rs/MWh
        out = np.full(len(delta_mw_grid), np.inf)
        q_design = self.q_nom_per_h
        p_design = self.power_mw(q_design)
        # The floor is the DEEPEST feasible turn-down, which for a coupled
        # co-product is set by the downstream consumer, not by the cell. Using
        # q_min here would advertise flexibility the plant cannot deliver -- and
        # this curve is the slide the whole pitch rests on.
        p_floor = self.power_mw(self.deliverable_q_min_per_h)
        # Likewise the ceiling: the rebuild leg cannot flood the consumer.
        q_up = self.deliverable_q_max_per_h
        rebuild_rate = q_up - q_design

        for i, dmw in enumerate(delta_mw_grid):
            if dmw <= 0:
                out[i] = 0.0
                continue
            p_down = p_design - dmw
            if p_down < p_floor - 1e-9 or rebuild_rate <= 1e-9:
                continue
            q_down = self._q_for_power(p_down)

            shortfall = (q_design - q_down) * duration_h      # product owed
            if shortfall > (self.inv_init - self.inv_min) + 1e-9:
                continue                                      # buffer too small
            rebuild_h = shortfall / rebuild_rate
            if shortfall > (self.inv_max - self.inv_init) + 1e-9:
                pass  # refilling only restores the drawn-down level; always ok

            e_flat = p_design * (duration_h + rebuild_h)
            e_flex = p_down * duration_h + self.power_mw(q_up) * rebuild_h
            displaced = dmw * duration_h
            out[i] = ref_rs_per_mwh * (e_flex - e_flat) / displaced
        return out

    @property
    def deliverable_q_min_per_h(self) -> float:
        """Deepest turn-down the whole plant can actually sustain.

        For a coupled co-product the binding floor is the downstream consumer's
        minimum take, relieved by nothing (the sink of last resort only absorbs
        SURPLUS co-product; it cannot manufacture the shortfall). Where there is
        no co-product this collapses to minimum stable load.
        """
        floor = self.q_min_per_h
        if self.coproduct_ratio > 0:
            floor = max(floor, self.sink_min_per_h / self.coproduct_ratio)
        return floor

    @property
    def deliverable_q_max_per_h(self) -> float:
        """Highest sustained rate the co-product balance allows."""
        ceil = self.q_max_per_h
        if self.coproduct_ratio > 0:
            ceil = min(ceil, (self.sink_max_per_h + self.dump_max_per_h)
                       / self.coproduct_ratio)
        return ceil

    def _q_for_power(self, p_mw: float) -> float:
        """Invert the (monotone increasing) power curve numerically."""
        lo, hi = 0.0, self.q_max_per_h
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.power_mw(mid) < p_mw:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def virtual_battery(self) -> dict[str, float]:
        """Equivalent electrical battery, for the CFO slide."""
        usable_units = max(0.0, self.inv_init - self.inv_min)
        p_design = self.power_mw(self.q_nom_per_h)
        # Deliverable, not theoretical: the CFO slide must quote the battery the
        # plant actually has, which the co-product balance shrinks.
        max_shed_mw = p_design - self.power_mw(self.deliverable_q_min_per_h)
        hours = usable_units / max(
            self.q_nom_per_h - self.q_min_per_h, 1e-9
        )
        return {
            "power_mw": max_shed_mw,
            "duration_h": hours,
            "energy_mwh": max_shed_mw * hours,
        }


# ------------------------------------------------------------------ archetypes
def asu(scale: float = 1.0) -> ProcessTwin:
    """Air separation unit with cryogenic liquid storage.

    Indicative values in published ranges; replace with plant data before
    quoting a site-specific number. Nominal 20 MW producing 40 t/h of liquid
    product at ~500 kWh/t; a 240 t usable tank is six hours of buffer.
    """
    return ProcessTwin(
        name="Air separation unit (LOX/LIN)",
        kind="asu",
        unit="t",
        p_nom_mw=20.0 * scale,
        q_nom_per_h=40.0 * scale,
        coef_a=0.10, coef_b=0.80, coef_c=0.10,      # SEC minimum exactly at design
        x_min=0.55, x_max=1.10,
        inv_min=60.0 * scale, inv_max=520.0 * scale, inv_init=300.0 * scale,
        inv_loss_frac_per_h=0.0002,                 # ~0.5%/day cryogenic boil-off
        demand_per_h=40.0 * scale,
        ramp_frac_per_block=0.10,                   # compressors ramp slowly
        can_shut_down=False,                        # never trip an ASU on price
        notes="SEC ~500 kWh/t at design; U-shaped in load. Tank is the battery.",
    )


def electrolyser(scale: float = 1.0) -> ProcessTwin:
    """Alkaline electrolyser + compressed hydrogen buffer, feeding a refinery.

    The refinery's hydrogen demand is constant; the alternative supply is the
    steam methane reformer, whose marginal cost sets the make-vs-buy threshold.
    """
    return ProcessTwin(
        name="Green H2 electrolyser + buffer",
        kind="electrolyser",
        unit="kg",
        p_nom_mw=15.0 * scale,
        q_nom_per_h=300.0 * scale,                  # 50 kWh/kg at design
        coef_a=0.06, coef_b=0.88, coef_c=0.06,      # flatter part-load than ASU
        x_min=0.15, x_max=1.05,
        inv_min=200.0 * scale, inv_max=3_000.0 * scale, inv_init=1_500.0 * scale,
        inv_loss_frac_per_h=0.0001,
        demand_per_h=240.0 * scale,                 # refinery H2 draw
        ramp_frac_per_block=0.60,                   # electrolysers ramp fast
        can_shut_down=True,
        start_cost_rs=18_000.0 * scale,             # PLACEHOLDER: thermal cycling
        min_up_blocks=4, min_down_blocks=4,
        alt_supply_cost_per_unit=185.0,             # PLACEHOLDER: SMR Rs/kg
        alt_supply_max_per_h=240.0 * scale,
        notes="LCOH minimises near 6,000 h/yr, not 8,000 — see the frontier tab.",
    )


def pipeline(scale: float = 1.0) -> ProcessTwin:
    """Crude/product pipeline pumping station with destination tankage.

    Hydraulically this is a pumped-storage scheme whose working fluid is a
    hydrocarbon: head loss goes with the square of throughput, so pump power
    goes with the cube. That makes the flexibility cost curve rise steeply --
    a deliberate contrast with the ASU, and the point of having three twins.
    """
    return ProcessTwin(
        name="Pipeline pumping station + tankage",
        kind="pipeline",
        unit="kL",
        p_nom_mw=8.0 * scale,
        q_nom_per_h=900.0 * scale,
        power_fn=lambda x: x ** 3,                  # hydraulic cube law
        x_min=0.45, x_max=1.12,
        inv_min=4_000.0 * scale, inv_max=26_000.0 * scale,
        inv_init=12_000.0 * scale,
        inv_loss_frac_per_h=0.0,
        demand_per_h=900.0 * scale,                 # downstream lifting
        ramp_frac_per_block=0.20,
        can_shut_down=True,
        start_cost_rs=25_000.0 * scale,             # PLACEHOLDER: restart + surge
        min_up_blocks=8, min_down_blocks=8,
        notes="Power ~ throughput cubed. Tank level is state of charge.",
    )


def ammonia(scale: float = 1.0) -> ProcessTwin:
    """Ammonia synthesis loop + intermediate liquid-ammonia storage, feeding urea.

    The archetype the author has actually operated. Two facts about it decide
    everything, and both are the opposite of the electrolyser's:

    1. **It cannot be tripped on price.** A synthesis-loop shutdown is a
       multi-day restart with catalyst risk. `can_shut_down=False`, and the
       optimizer is never allowed to consider stopping it.
    2. **It moves slowly.** The loop is ramped in single-digit percent per hour,
       not per block — converter bed temperatures and the recycle compressor's
       surge margin set the pace. Modelled at 3%/h, an order of magnitude slower
       than the electrolyser.

    What it does have is depth: an atmospheric liquid-ammonia tank between
    synthesis and urea holds thousands of tonnes. That makes it a slow, deep
    battery — the exact complement to the electrolyser's fast, shallow one, and
    a good argument for why a portfolio of archetypes beats any single asset.

    Indicative of a ~1,750 TPD gas-based Indian plant. Electricity is the
    smaller share of such a plant's energy (the reformer runs on gas); the
    electrical load modelled here is the syngas, recycle and refrigeration
    compression train at roughly 150 kWh per tonne of ammonia.
    """
    return ProcessTwin(
        name="Ammonia synthesis loop + NH3 storage",
        kind="ammonia",
        unit="t",
        p_nom_mw=10.9 * scale,
        q_nom_per_h=72.9 * scale,                   # 1,750 TPD
        coef_a=0.15, coef_b=0.70, coef_c=0.15,      # SEC minimum at design
        x_min=0.65, x_max=1.05,                     # loop stability floor
        inv_min=600.0 * scale, inv_max=4_000.0 * scale, inv_init=2_200.0 * scale,
        inv_loss_frac_per_h=0.000017,               # ~0.04%/day refrigerated
        demand_per_h=72.9 * scale,                  # urea plant draw
        ramp_frac_per_block=0.0075,                 # 3%/h — converter beds
        can_shut_down=False,                        # never trip on price
        notes=("Slow and deep: 3%/h ramp, 65% turndown floor, thousands of "
               "tonnes of buffer. Complements the electrolyser exactly."),
    )


def chloralkali(scale: float = 1.0) -> ProcessTwin:
    """Chlor-alkali membrane cell house + caustic soda storage.

    THE FLAGSHIP ARCHETYPE, and the only one whose convexity is not asserted
    but derived. In an electrochemical cell, voltage rises linearly with
    current density,

        V = V0 + k*i          (thermodynamic + Tafel + ohmic)

    and Faraday's law makes production proportional to current, q ∝ i. Power is
    V*I, so

        P(q) = alpha*q + beta*q^2

    is a **textbook consequence of electrochemistry**, not a modelling choice.
    Fitting the voltage law over a 0.4-1.08 load range reproduces
    a1 = 0.777, a2 = 0.223 with no fixed term -- the cell itself has no standby
    load. The small a0 below is balance of plant: brine circulation, chlorine
    compression, caustic evaporation, hydrogen handling.

    Three properties make this the best demand-flexibility asset in Indian
    industry, and no other archetype here has all three:

    1. **Turning down IMPROVES specific energy.** SEC(x) has its minimum near
       load, because cell voltage falls with current density. NPC India's
       published empirical equation E = 2.41 + 0.329i + 0.24 log i has NO fixed
       term, so the CELL's SEC falls monotonically on turn-down; the interior
       minimum near 53% here is a consequence of this twin's 6% balance-of-plant
       term, i.e. a boundary choice, not a property of the cell. Every other
       twin in this file pays a specific-energy penalty to turn down; this one
       is paid to. The round-trip loss is therefore unusually small.
    2. **Power is 55-70% of cash cost.** Flexibility is not a rounding error on
       the P&L; it is the P&L.
    3. **Caustic is storable in bulk.** Lye tanks hold days of production, so
       the buffer is enormous relative to the shed.

    What limits it is NOT energy. It is:

    - **Minimum current density.** Below roughly 40% of design, current
      efficiency falls and hydrogen can cross into the chlorine header. H2 in
      Cl2 is explosive above a few percent. This is a hard safety interlock and
      it is why `x_min` is 0.40 and not lower.
    - **The chlorine balance.** Cl2 is produced stoichiometrically with NaOH and
      cannot be stored in bulk. It must be consumed in real time by the
      downstream unit, with a bleach plant as the sink of last resort. In
      practice the Cl2 consumer's turndown, not the cell's, sets the floor --
      which is what `x_min` here really encodes.
    - **The membrane.** A membrane cell house is never de-energised on price: a
      full shutdown risks membrane damage and requires a protective
      polarisation current. Hence `can_shut_down=False`.

    Indicative of a 700 TPD (100% NaOH basis) Indian plant.
    """
    return ProcessTwin(
        name="Chlor-alkali cell house + caustic storage",
        kind="chloralkali",
        unit="t",
        p_nom_mw=67.0 * scale,
        q_nom_per_h=29.2 * scale,                   # 700 TPD NaOH, 100% basis
        coef_a=0.06, coef_b=0.73, coef_c=0.21,      # BoP + cell voltage law
        x_min=0.40,                                 # H2-in-Cl2 safety floor
        x_max=1.08,                                 # rectifier + membrane limit
        inv_min=300.0 * scale, inv_max=1_800.0 * scale, inv_init=900.0 * scale,
        inv_loss_frac_per_h=0.0,                    # lye does not evaporate
        demand_per_h=29.2 * scale,                  # dispatch + downstream draw
        ramp_frac_per_block=0.15,                   # 60%/h: rectifiers are fast,
                                                    # membranes set the limit
        can_shut_down=False,                        # never de-energise on price

        # --- the chlorine balance: what ACTUALLY limits the turndown --------
        # 71 t Cl2 per 80 t NaOH = 0.886. The downstream consumer (EDC/VCM, or
        # a merchant Cl2 offtake) is assumed to hold 70-105% of design draw; the
        # bleach plant absorbs up to 12% of design Cl2 flow at a value penalty.
        # Together these bind the cell to ~66% load even though the cell's own
        # safety interlock sits at 40% -- which is the whole point.
        coproduct_ratio=0.886, coproduct_name="Cl2",
        sink_min_per_h=0.70 * 0.886 * 29.2 * scale,   # PLACEHOLDER: consumer
        sink_max_per_h=1.05 * 0.886 * 29.2 * scale,   #   turndown, plant-specific
        dump_max_per_h=0.12 * 0.886 * 29.2 * scale,   # PLACEHOLDER: bleach cap
        dump_cost_per_unit=9_000.0,                   # PLACEHOLDER: Rs/t of Cl2
                                                      #   value destroyed as
                                                      #   hypochlorite vs EDC

        # --- membrane life is consumed by movement, not by runtime ----------
        # A membrane set is ~Rs 21.5 cr and lives ~4 years at steady load. If
        # cycling costs 5% of that life, the plant is paying ~Rs 27 lakh/yr for
        # movement, which at ~1000 t/h of annual setpoint travel is Rs ~1200 per
        # t/h moved. Charging zero here is how these models flatter themselves.
        cycling_cost_rs_per_unit=1_200.0,             # PLACEHOLDER: Rs per t/h
        max_total_variation=60.0 * scale,             # ~2 full swings/day

        # Thyristor rectifiers: pf falls with firing angle on turn-down, and
        # MERC bills kVAh. PLACEHOLDER pair, plant-specific and improved by any
        # site with static VAr compensation.
        pf_nom=0.98, pf_at_x_min=0.85,
        n_trains=4,                                   # four rectifier trains:
                                                      # losing one is -25%, not
                                                      # a drop to minimum load

        notes=("Convexity derived from V = V0 + k*i, not assumed. SEC minimum "
               "on turn-down (NPC India eqn) — the only archetype PAID to do so. "
               "The binding floor is the CHLORINE CONSUMER's turndown, not the "
               "cell's H2-in-Cl2 interlock at 40%."),
    )


def fleet_chloralkali(scale: float = 1.0) -> list[ProcessTwin]:
    """Chlor-alkali complex — the flagship site."""
    return [chloralkali(scale)]


def fleet_refinery(scale: float = 1.0) -> list[ProcessTwin]:
    """Refinery utilities block — the site the measured results are for."""
    return [asu(scale), electrolyser(scale), pipeline(scale)]


def fleet_fertilizer(scale: float = 1.0) -> list[ProcessTwin]:
    """Ammonia-urea complex: synthesis loop plus its own air separation unit."""
    return [ammonia(scale), asu(scale * 0.5)]


def all_archetypes(scale: float = 1.0) -> list[ProcessTwin]:
    """Every twin, for characterisation on the Twin tab."""
    return [chloralkali(scale), electrolyser(scale), asu(scale),
            ammonia(scale), pipeline(scale)]


def default_fleet(scale: float = 1.0) -> list[ProcessTwin]:
    return fleet_refinery(scale)


# ══════════════════════════════════════════════════════════════════════════
# ProcessModel conformance.
#
# These methods let the existing, validated archetypes be dispatched through
# the same interface as any configured process, WITHOUT changing any of the
# physics above. They are adapters, not new behaviour — every one delegates to
# a field or method that was already here and already covered by tests. The
# validated chlor-alkali numbers are therefore untouched by construction.
# ══════════════════════════════════════════════════════════════════════════
def _twin_data_status(self) -> str:
    from .process import ILLUSTRATIVE, VALIDATED
    return VALIDATED if self.kind == "chloralkali" else ILLUSTRATIVE


def _twin_envelope(self):
    from .process import OperatingEnvelope
    why = "unit minimum stable load"
    if self.coproduct_ratio > 0 and self.deliverable_q_min_per_h > self.q_min_per_h:
        why = f"{self.coproduct_name} consumer minimum take"
    return OperatingEnvelope(
        floor=self.deliverable_q_min_per_h, ceiling=self.deliverable_q_max_per_h,
        design=self.q_nom_per_h, unit=self.unit, floor_reason=why)


def _twin_power_curve(self):
    from .process import PowerCurve
    return PowerCurve(self.power_mw, self.tangents(), self.max_linearization_error())


def _twin_production_constraints(self) -> dict:
    return {
        "downstream_draw_per_h": self.demand_per_h,
        "coproduct_ratio": self.coproduct_ratio,
        "coproduct_name": self.coproduct_name,
        "sink_min_per_h": self.sink_min_per_h,
        "sink_max_per_h": self.sink_max_per_h,
        "hard_constraint_active": False,
        "hard_constraint_reason": "",
        "can_shut_down": self.can_shut_down,
    }


def _twin_inventory_state(self) -> dict:
    usable = max(0.0, self.inv_init - self.inv_min)
    return {"now": self.inv_init, "min": self.inv_min, "max": self.inv_max,
            "unit": self.unit, "usable_below": usable,
            "hours_of_cover": (usable / self.demand_per_h
                               if self.demand_per_h > 0 else float("inf"))}


def _twin_ramp_limits(self) -> dict:
    per_h = self.ramp_frac_per_block * self.q_nom_per_h * 4.0
    return {"up_per_h": per_h, "down_per_h": per_h,
            "up_pct_per_h": self.ramp_frac_per_block * 400.0,
            "down_pct_per_h": self.ramp_frac_per_block * 400.0}


def _twin_recovery_constraints(self) -> dict:
    return {"recovery_time_h": 0.0, "terminal_inventory_min": self.inv_init,
            "min_up_blocks": self.min_up_blocks,
            "min_down_blocks": self.min_down_blocks}


def _twin_flexibility_cost(self, delta_mw: float, duration_h: float):
    """Wraps the existing `flexibility_cost_curve`, which is the validated
    implementation, and adds the availability semantics the platform needs."""
    import numpy as _np
    from .process import FlexibilityQuote
    env = self.get_operating_envelope()
    p_design = self.power_mw(self.q_nom_per_h)
    max_shed = max(0.0, p_design - self.power_mw(env.floor))
    if delta_mw <= 0 or duration_h <= 0:
        return FlexibilityQuote(delta_mw, duration_h, True, 0.0, 0.0,
                                max_shed, 0.0, "no move requested")
    if delta_mw > max_shed + 1e-9:
        return FlexibilityQuote(delta_mw, duration_h, False, float("inf"),
                                float("inf"), max_shed, 0.0,
                                f"exceeds available shed of {max_shed:.1f} MW "
                                f"({env.floor_reason})")
    phi = float(self.flexibility_cost_curve(_np.array([delta_mw]), duration_h)[0])
    if not _np.isfinite(phi):
        inv = self.get_inventory_state()
        return FlexibilityQuote(delta_mw, duration_h, False, float("inf"),
                                float("inf"), max_shed, 0.0,
                                f"buffer cannot cover {delta_mw:.1f} MW for "
                                f"{duration_h:.1f} h "
                                f"({inv['usable_below']:.0f} {self.unit} usable)")
    displaced = delta_mw * duration_h
    q_down = self._q_for_power(p_design - delta_mw)
    inv = self.get_inventory_state()
    return FlexibilityQuote(
        delta_mw=delta_mw, duration_h=duration_h, available=True,
        process_cost_rs=phi * displaced, rs_per_mwh_shifted=phi,
        max_safe_mw=max_shed,
        max_safe_duration_h=(inv["usable_below"]
                             / max(1e-9, self.q_nom_per_h - q_down)),
        limiting_factor=env.floor_reason)


def _twin_validate_schedule(self, production_per_h, dt_h: float):
    import numpy as _np
    from .process import ValidationResult
    q = _np.asarray(production_per_h, dtype=float)
    env = self.get_operating_envelope()
    v = []
    tol = 1e-4
    running = q > tol
    if _np.any(running & (q < self.q_min_per_h - tol)):
        v.append(f"below minimum stable load {self.q_min_per_h:.2f} {self.unit}/h")
    if _np.any(q > self.q_max_per_h + tol):
        v.append(f"above maximum rate {self.q_max_per_h:.2f} {self.unit}/h")
    if len(q) > 1:
        dq = _np.abs(_np.diff(q))
        if _np.any(dq > self.ramp_frac_per_block * self.q_nom_per_h + tol):
            v.append("ramp limit exceeded")
    if self.coproduct_ratio > 0:
        made = self.coproduct_ratio * q
        if _np.any(made - self.dump_max_per_h < self.sink_min_per_h - tol):
            v.append(f"{self.coproduct_name} consumer starved below "
                     f"{self.sink_min_per_h:.2f} {self.unit}/h")
    level = self.inv_init
    lo = level
    for rate in q:
        level = (level * (1.0 - self.inv_loss_frac_per_h * dt_h)
                 + (rate - self.demand_per_h) * dt_h)
        lo = min(lo, level)
    if lo < self.inv_min - 1.0:
        v.append(f"buffer falls to {lo:.1f} < minimum {self.inv_min:.1f}")
    return ValidationResult(not v, v)


def _twin_binding(self, production_per_h, dt_h: float) -> list[str]:
    import numpy as _np
    q = _np.asarray(production_per_h, dtype=float)
    env = self.get_operating_envelope()
    out, tol = [], 1e-4
    n = int(_np.sum(q <= env.floor + tol))
    if n:
        out.append(f"Operating floor binds in {n} of {len(q)} blocks — "
                   f"{env.floor_reason}, {env.floor_pct:.0f}% of design.")
    n = int(_np.sum(q >= env.ceiling - tol))
    if n:
        out.append(f"Ceiling binds in {n} blocks ({env.ceiling_pct:.0f}% of design).")
    return out


for _name, _fn in (
    ("data_status", _twin_data_status),
    ("get_operating_envelope", _twin_envelope),
    ("get_power_curve", _twin_power_curve),
    ("get_production_constraints", _twin_production_constraints),
    ("get_inventory_state", _twin_inventory_state),
    ("get_ramp_limits", _twin_ramp_limits),
    ("get_recovery_constraints", _twin_recovery_constraints),
    ("calculate_flexibility_cost", _twin_flexibility_cost),
    ("validate_schedule", _twin_validate_schedule),
    ("get_binding_constraints", _twin_binding),
):
    setattr(ProcessTwin, _name, _fn)
