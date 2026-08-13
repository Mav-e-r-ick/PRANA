"""A configurable industrial process — the platform's proof of generality.

ILLUSTRATIVE / REQUIRES PLANT CALIBRATION.

This model does not represent any real refinery, fertiliser plant or hydrogen
unit. It is a parameterised process that conforms to `ProcessModel`, so that the
optimiser, the market engine, the decision logic and the safety architecture can
be exercised against physics that is *not* chlor-alkali. That is its entire
purpose: to demonstrate that nothing downstream of the process boundary contains
a chlor-alkali assumption.

Every number it produces carries status ILLUSTRATIVE or USER_CONFIGURED. It may
never be quoted as a saving for a real plant, and the UI is responsible for
never showing its output next to a validated figure without a label.

The physics is deliberately the same *shape* as every continuous process with a
buffer: power is convex in production rate, there is a floor and a ceiling, the
rate cannot change instantly, and inventory must end where it started.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .process import (ILLUSTRATIVE, USER_CONFIGURED, FlexibilityQuote,
                      OperatingEnvelope, PowerCurve, ValidationResult,
                      check_status)


@dataclass
class GenericProcess:
    """A continuous process with a buffer, configured rather than derived.

    Parameters are in engineering units a plant engineer would recognise, not in
    the normalised coefficients the optimiser wants — the conversion happens
    here so that the configuration screen never asks anyone for `coef_c`.
    """

    name: str = "Generic continuous process"
    unit: str = "t"

    # --- operating point ---------------------------------------------------
    design_load_mw: float = 100.0
    design_rate_per_h: float = 50.0
    min_stable_pct: float = 60.0          # % of design the UNIT can hold
    max_load_pct: float = 105.0

    # --- how hard it is to move -------------------------------------------
    ramp_up_pct_per_h: float = 30.0
    ramp_down_pct_per_h: float = 30.0
    recovery_time_h: float = 0.0          # forced settle after a move

    # --- the buffer --------------------------------------------------------
    inventory_now: float = 600.0
    inventory_min: float = 200.0
    inventory_max: float = 1_600.0
    downstream_draw_per_h: float = 50.0

    # --- what it costs to move --------------------------------------------
    # Fixed share of power that does NOT scale with rate (standby, auxiliaries).
    # Larger fixed share => turning down saves proportionally less => flexibility
    # is more expensive. This one number carries most of the process penalty.
    fixed_load_share: float = 0.10
    wear_cost_rs_per_unit_moved: float = 0.0
    production_penalty_rs_per_unit: float = 0.0

    # --- hard constraints --------------------------------------------------
    # A downstream consumer that must be fed regardless of electricity price.
    # Set `downstream_min_pct` to 100 to model a unit that simply cannot flex.
    downstream_min_pct: float = 0.0
    hard_constraint_active: bool = False
    hard_constraint_reason: str = ""

    status: str = ILLUSTRATIVE
    notes: str = "ILLUSTRATIVE — requires plant calibration before any rupee figure."

    _tangents: list[tuple[float, float]] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ init
    def __post_init__(self) -> None:
        check_status(self.status)
        self.validate_configuration()

    def validate_configuration(self) -> None:
        """Reject configurations that cannot describe a real plant.

        A UI that silently accepts min > max produces a schedule that looks
        authoritative and is meaningless, which is worse than an error message.
        """
        if self.design_rate_per_h <= 0 or self.design_load_mw <= 0:
            raise ValueError("design load and design rate must be positive")
        if not 0 < self.min_stable_pct <= self.max_load_pct:
            raise ValueError("need 0 < min_stable_pct <= max_load_pct")
        if not 0.0 <= self.fixed_load_share < 1.0:
            raise ValueError("fixed_load_share must be in [0, 1)")
        if self.inventory_min > self.inventory_max:
            raise ValueError("inventory_min exceeds inventory_max")
        if not self.inventory_min <= self.inventory_now <= self.inventory_max:
            raise ValueError("inventory_now is outside [inventory_min, inventory_max]")
        if self.downstream_draw_per_h < 0:
            raise ValueError("downstream draw cannot be negative")
        if not 0.0 <= self.downstream_min_pct <= 200.0:
            raise ValueError("downstream_min_pct must be a sane percentage")

    # -------------------------------------------------------------- interface
    def data_status(self) -> str:
        return self.status

    def get_operating_envelope(self) -> OperatingEnvelope:
        unit_floor = self.min_stable_pct / 100.0 * self.design_rate_per_h
        floor, why = unit_floor, "unit minimum stable load"
        if self.downstream_min_pct > 0:
            ds = self.downstream_min_pct / 100.0 * self.design_rate_per_h
            if ds > floor:
                floor, why = ds, "downstream consumer minimum take"
        if self.hard_constraint_active:
            floor = self.design_rate_per_h
            why = self.hard_constraint_reason or "hard production constraint"
        return OperatingEnvelope(
            floor=floor,
            ceiling=self.max_load_pct / 100.0 * self.design_rate_per_h,
            design=self.design_rate_per_h,
            unit=self.unit,
            floor_reason=why,
        )

    def power_mw(self, rate_per_h: float) -> float:
        """Convex in rate: a fixed share plus a variable share with a quadratic
        term, normalised so that power(design) == design_load_mw."""
        if rate_per_h <= 0:
            return 0.0
        x = rate_per_h / self.design_rate_per_h
        a = self.fixed_load_share
        c = 0.20 * (1.0 - a)               # curvature; keeps a + b + c == 1
        b = 1.0 - a - c
        return self.design_load_mw * (a + b * x + c * x * x)

    def get_power_curve(self) -> PowerCurve:
        env = self.get_operating_envelope()
        if not self._tangents:
            qs = np.linspace(max(env.floor, 1e-9), env.ceiling, 16)
            h = max(1e-6, 1e-4 * self.design_rate_per_h)
            for q in qs:
                slope = (self.power_mw(q + h) - self.power_mw(q - h)) / (2 * h)
                self._tangents.append((float(slope),
                                       float(self.power_mw(q) - slope * q)))
        qs = np.linspace(max(env.floor, 1e-9), env.ceiling, 200)
        err = max(
            (self.power_mw(q) - max(s * q + i for s, i in self._tangents))
            / max(self.power_mw(q), 1e-9) for q in qs
        )
        return PowerCurve(self.power_mw, list(self._tangents), float(err))

    def get_production_constraints(self) -> dict:
        return {
            "downstream_draw_per_h": self.downstream_draw_per_h,
            "downstream_min_pct": self.downstream_min_pct,
            "hard_constraint_active": self.hard_constraint_active,
            "hard_constraint_reason": self.hard_constraint_reason,
            "production_penalty_rs_per_unit": self.production_penalty_rs_per_unit,
        }

    def get_inventory_state(self) -> dict:
        return {
            "now": self.inventory_now, "min": self.inventory_min,
            "max": self.inventory_max, "unit": self.unit,
            "usable_below": max(0.0, self.inventory_now - self.inventory_min),
            "hours_of_cover": (max(0.0, self.inventory_now - self.inventory_min)
                               / self.downstream_draw_per_h
                               if self.downstream_draw_per_h > 0 else float("inf")),
        }

    def get_ramp_limits(self) -> dict:
        return {
            "up_per_h": self.ramp_up_pct_per_h / 100.0 * self.design_rate_per_h,
            "down_per_h": self.ramp_down_pct_per_h / 100.0 * self.design_rate_per_h,
            "up_pct_per_h": self.ramp_up_pct_per_h,
            "down_pct_per_h": self.ramp_down_pct_per_h,
        }

    def get_recovery_constraints(self) -> dict:
        return {
            "recovery_time_h": self.recovery_time_h,
            "terminal_inventory_min": self.inventory_now,
        }

    # ------------------------------------------------------- the core product
    def calculate_flexibility_cost(
        self, delta_mw: float, duration_h: float
    ) -> FlexibilityQuote:
        """phi(dMW, dt) — what it costs this process to give up `delta_mw` for
        `duration_h`, then put the inventory back.

        Returns UNAVAILABLE rather than a large number when the move is
        physically impossible. A process that cannot move must be able to say so
        — that is what makes DO NOTHING a real answer instead of a fallback.
        """
        env = self.get_operating_envelope()
        p_design = self.power_mw(self.design_rate_per_h)
        p_floor = self.power_mw(env.floor)
        max_shed = max(0.0, p_design - p_floor)

        ramps = self.get_ramp_limits()
        inv = self.get_inventory_state()

        def unavailable(why: str) -> FlexibilityQuote:
            return FlexibilityQuote(delta_mw, duration_h, False, float("inf"),
                                    float("inf"), max_shed, 0.0, why)

        if self.hard_constraint_active:
            return unavailable(self.hard_constraint_reason
                               or "hard production constraint active")
        if delta_mw <= 0 or duration_h <= 0:
            return FlexibilityQuote(delta_mw, duration_h, True, 0.0, 0.0,
                                    max_shed, 0.0, "no move requested")
        if delta_mw > max_shed + 1e-9:
            return unavailable(f"exceeds available shed of {max_shed:.1f} MW "
                               f"({env.floor_reason})")

        # Rate that delivers the requested power reduction.
        lo, hi = env.floor, self.design_rate_per_h
        target = p_design - delta_mw
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.power_mw(mid) < target:
                lo = mid
            else:
                hi = mid
        rate_down = 0.5 * (lo + hi)

        shortfall = (self.design_rate_per_h - rate_down) * duration_h
        if shortfall > inv["usable_below"] + 1e-9:
            hrs = (inv["usable_below"] / max(1e-9, self.design_rate_per_h - rate_down))
            return unavailable(
                f"buffer covers only {hrs:.1f} h at this depth "
                f"({inv['usable_below']:.0f} {self.unit} usable)")

        # Rebuild leg: run above design to replace the shortfall.
        rebuild_rate = env.ceiling - self.design_rate_per_h
        if rebuild_rate <= 1e-9:
            return unavailable("no headroom above design to rebuild inventory")
        rebuild_h = shortfall / rebuild_rate

        # Ramp feasibility: can it get there and back inside the window?
        ramp_h = ((self.design_rate_per_h - rate_down) / max(1e-9, ramps["down_per_h"])
                  + (self.design_rate_per_h - rate_down) / max(1e-9, ramps["up_per_h"]))
        if ramp_h + self.recovery_time_h >= duration_h:
            return unavailable(
                f"ramp + recovery needs {ramp_h + self.recovery_time_h:.1f} h, "
                f"longer than the {duration_h:.1f} h window")

        # Energy penalty: convexity means the two legs burn more than running flat.
        e_flat = p_design * (duration_h + rebuild_h)
        e_flex = (self.power_mw(rate_down) * duration_h
                  + self.power_mw(env.ceiling) * rebuild_h)
        extra_mwh = max(0.0, e_flex - e_flat)

        # Priced at the plant's own average cost of energy is circular, so the
        # process cost is returned in MWh-equivalent and the DECISION layer
        # prices it. Here we only add the non-energy penalties.
        moved = (self.design_rate_per_h - rate_down) * 2.0     # down and back
        wear = moved * self.wear_cost_rs_per_unit_moved
        penalty = shortfall * self.production_penalty_rs_per_unit

        displaced_mwh = delta_mw * duration_h
        return FlexibilityQuote(
            delta_mw=delta_mw,
            duration_h=duration_h,
            available=True,
            process_cost_rs=extra_mwh * 1000.0 + wear + penalty,
            rs_per_mwh_shifted=((extra_mwh * 1000.0 + wear + penalty)
                                / max(displaced_mwh, 1e-9)),
            max_safe_mw=max_shed,
            max_safe_duration_h=(inv["usable_below"]
                                 / max(1e-9, self.design_rate_per_h - rate_down)),
            limiting_factor=env.floor_reason,
        )

    # ------------------------------------------------------------ validation
    def validate_schedule(
        self, production_per_h: np.ndarray, dt_h: float
    ) -> ValidationResult:
        q = np.asarray(production_per_h, dtype=float)
        env = self.get_operating_envelope()
        ramps = self.get_ramp_limits()
        v: list[str] = []
        tol = 1e-6

        if np.any(q < env.floor - tol):
            v.append(f"below operating floor {env.floor:.2f} {self.unit}/h "
                     f"({env.floor_reason})")
        if np.any(q > env.ceiling + tol):
            v.append(f"above ceiling {env.ceiling:.2f} {self.unit}/h")
        if len(q) > 1:
            d = np.diff(q)
            if np.any(d > ramps["up_per_h"] * dt_h + tol):
                v.append("ramp-up limit exceeded")
            if np.any(-d > ramps["down_per_h"] * dt_h + tol):
                v.append("ramp-down limit exceeded")

        level = self.inventory_now
        lo = hi = level
        for rate in q:
            level += (rate - self.downstream_draw_per_h) * dt_h
            lo, hi = min(lo, level), max(hi, level)
        if lo < self.inventory_min - 1e-6:
            v.append(f"inventory falls to {lo:.1f} < minimum {self.inventory_min:.1f}")
        if hi > self.inventory_max + 1e-6:
            v.append(f"inventory rises to {hi:.1f} > maximum {self.inventory_max:.1f}")
        if level < self.inventory_now - 1e-6:
            v.append(f"ends at {level:.1f}, below opening {self.inventory_now:.1f}")
        return ValidationResult(not v, v)

    def get_binding_constraints(
        self, production_per_h: np.ndarray, dt_h: float
    ) -> list[str]:
        q = np.asarray(production_per_h, dtype=float)
        env = self.get_operating_envelope()
        out: list[str] = []
        tol = 1e-4
        n = int(np.sum(q <= env.floor + tol))
        if n:
            out.append(f"Operating floor binds in {n} of {len(q)} blocks — "
                       f"{env.floor_reason}, {env.floor_pct:.0f}% of design.")
        n = int(np.sum(q >= env.ceiling - tol))
        if n:
            out.append(f"Ceiling binds in {n} blocks ({env.ceiling_pct:.0f}% of design).")
        if self.hard_constraint_active:
            out.append(f"HARD CONSTRAINT: {self.hard_constraint_reason}")
        return out


def demo_generic(**kw) -> GenericProcess:
    """The configuration the UI opens with. USER_CONFIGURED the moment anyone
    touches a slider."""
    g = GenericProcess(**kw)
    if kw:
        g.status = USER_CONFIGURED
    return g
