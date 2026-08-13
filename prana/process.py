"""The process-model interface — the boundary that makes PRANA a platform.

WHY THIS FILE EXISTS. Until now the optimiser took `ProcessTwin` objects and the
chlor-alkali case was the only thing anyone had run. That is a demonstration,
not a platform. This module defines the contract that *any* industrial process
must satisfy in order to be dispatched, so that the optimiser, the market
engine, the decision logic and the safety architecture are all written once and
reused unchanged.

THE RULE THIS FILE ENFORCES: nothing downstream of here may ask what the process
*is*. It may only ask what the process *can do*. If a module needs to know it is
looking at a cell house rather than a compressor, the abstraction has failed.

A conforming model answers nine questions:

    get_operating_envelope()      where can it run, right now
    get_power_curve()             what does each operating point cost in MW
    get_production_constraints()  what must it deliver regardless of price
    get_inventory_state()         what buffer does it have to play with
    get_ramp_limits()             how fast may it move
    get_recovery_constraints()    what must be true when the horizon ends
    calculate_flexibility_cost()  phi(dMW, dt) — the core product
    validate_schedule()           independent check against true physics
    get_binding_constraints()     why the answer came out the way it did

`ProcessTwin` (chlor-alkali and the other archetypes) conforms. `GenericProcess`
conforms. The optimiser accepts either and cannot tell them apart.

DATA STATUS. Every model declares one, and it travels with every number it
produces:

    VALIDATED       backtested on real prices, physics grounded in a published
                    source, results independently re-verified
    ILLUSTRATIVE    the mechanism is real, the parameters are not a specific
                    plant — requires calibration before any rupee figure means
                    anything
    USER_CONFIGURED entered at runtime by whoever is holding the mouse

A model may not upgrade its own status. That is the point of it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

VALIDATED = "VALIDATED"
ILLUSTRATIVE = "ILLUSTRATIVE"
USER_CONFIGURED = "USER_CONFIGURED"

_STATUSES = (VALIDATED, ILLUSTRATIVE, USER_CONFIGURED)


@dataclass(frozen=True)
class OperatingEnvelope:
    """Where the process may operate, in production units per hour.

    `floor` is the DELIVERABLE minimum — the deepest turn-down the whole plant
    can sustain, which for a coupled process is set by the downstream consumer
    and not by the unit's own minimum stable load. Quoting the unit's own floor
    when a downstream constraint binds first is the commonest way these models
    promise flexibility that does not exist.
    """

    floor: float
    ceiling: float
    design: float
    unit: str
    floor_reason: str = ""

    @property
    def floor_pct(self) -> float:
        return 100.0 * self.floor / self.design if self.design else float("nan")

    @property
    def ceiling_pct(self) -> float:
        return 100.0 * self.ceiling / self.design if self.design else float("nan")


@dataclass(frozen=True)
class FlexibilityQuote:
    """The answer to "what would it cost to move ΔMW for Δt hours?"

    `available=False` with `process_cost_rs=inf` is a first-class answer, not an
    error. A process that cannot move is entitled to say so.
    """

    delta_mw: float
    duration_h: float
    available: bool
    process_cost_rs: float
    rs_per_mwh_shifted: float
    max_safe_mw: float
    max_safe_duration_h: float
    limiting_factor: str = ""

    @property
    def band(self) -> str:
        """Traffic-light band the UI uses. Thresholds are presentation only —
        the optimiser always compares dieselcost against benefit numerically."""
        if not self.available or not np.isfinite(self.rs_per_mwh_shifted):
            return "UNAVAILABLE"
        return "ECONOMIC" if self.rs_per_mwh_shifted <= 250.0 else "EXPENSIVE"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    violations: list[str]

    def __bool__(self) -> bool:      # so `if validate_schedule(...):` reads right
        return self.ok


@runtime_checkable
class ProcessModel(Protocol):
    """What the optimiser is allowed to know about a process. Nothing else."""

    name: str
    unit: str

    def data_status(self) -> str: ...
    def get_operating_envelope(self) -> OperatingEnvelope: ...
    def get_power_curve(self) -> "PowerCurve": ...
    def get_production_constraints(self) -> dict: ...
    def get_inventory_state(self) -> dict: ...
    def get_ramp_limits(self) -> dict: ...
    def get_recovery_constraints(self) -> dict: ...
    def calculate_flexibility_cost(
        self, delta_mw: float, duration_h: float
    ) -> FlexibilityQuote: ...
    def validate_schedule(
        self, production_per_h: np.ndarray, dt_h: float
    ) -> ValidationResult: ...
    def get_binding_constraints(
        self, production_per_h: np.ndarray, dt_h: float
    ) -> list[str]: ...


@dataclass(frozen=True)
class PowerCurve:
    """Electrical power as a function of production rate, plus the linear
    outer approximation the MILP consumes.

    `tangents` must LOWER-bound `true_power` everywhere on the envelope. If it
    ever exceeded the true curve the MILP would forbid feasible operating
    points, which is a silent and very expensive kind of wrong.
    """

    true_power_mw: object                  # callable: q_per_h -> MW
    tangents: list[tuple[float, float]]    # (slope, intercept)
    max_linearization_error: float

    def __call__(self, q_per_h: float) -> float:
        return float(self.true_power_mw(q_per_h))


def check_status(status: str) -> str:
    if status not in _STATUSES:
        raise ValueError(f"data status must be one of {_STATUSES}, got {status!r}")
    return status


def conforms(obj: object) -> bool:
    """True if `obj` can be dispatched. Used by tests to prove the optimiser is
    genuinely process-agnostic rather than accidentally so."""
    required = (
        "get_operating_envelope", "get_power_curve", "get_production_constraints",
        "get_inventory_state", "get_ramp_limits", "get_recovery_constraints",
        "calculate_flexibility_cost", "validate_schedule", "get_binding_constraints",
        "data_status",
    )
    return all(callable(getattr(obj, m, None)) for m in required)
