"""Landed-cost engine.

The differentiator. Every competing tool optimizes against the exchange market
clearing price; the MCP is roughly 60% of what an Indian industrial consumer
actually pays. This module turns a market price series into the cost the plant
sees at its own meter, and exposes the demand-charge term separately because it
is levied on peak billing kVA rather than on energy — which means a schedule
that piles shifted load into cheap midday hours can raise the monthly maximum
demand and wipe out the energy saving.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import TariffConfig


@dataclass
class LandedCost:
    """Per-block landed marginal energy cost, Rs/kWh, plus its decomposition."""

    total: np.ndarray          # Rs/kWh, per block — what the optimizer prices
    energy: np.ndarray         # Rs/kWh, the market/retail energy component
    non_energy: np.ndarray     # Rs/kWh, the regulatory stack
    duty: np.ndarray           # Rs/kWh, electricity duty
    label: str

    @property
    def non_energy_share(self) -> float:
        num = float(np.mean(self.non_energy + self.duty))
        den = float(np.mean(self.total))
        return num / den if den else 0.0

    def as_rs_per_mwh(self) -> np.ndarray:
        return self.total * 1000.0


def tod_multiplier(
    hours: np.ndarray, cfg: TariffConfig, month: int | None = None
) -> np.ndarray:
    """Time-of-day multiplier on the retail energy charge.

    VERIFIED against MERC Case 75 of 2025 (post-remand), Table 8, HT categories:

        00:00-09:00   0%     (the night rebate was REMOVED — para 18.13)
        09:00-17:00   -15% Apr-Sep, -25% Oct-Mar   (seasonal, FY2026-27)
        17:00-24:00   +20%   (a 7-hour peak window, not 5)

    `month` selects the season. Passing None assumes the Apr-Sep rebate, which
    is the *smaller* of the two — the conservative choice.
    """
    m = np.ones_like(hours, dtype=float) * cfg.tod_offpeak_mult
    solar = (cfg.tod_solar_mult_apr_sep
             if month is None or 4 <= month <= 9
             else cfg.tod_solar_mult_oct_mar)
    m[(hours >= 9) & (hours < 17)] = solar
    m[hours >= 17] = cfg.tod_peak_mult
    return m


def landed_cost(
    mcp_rs_mwh: np.ndarray,
    hours: np.ndarray,
    cfg: TariffConfig,
    month: int | None = None,
) -> LandedCost:
    """Market price (or retail tariff) -> Rs/kWh at the meter."""
    if cfg.mode == "EXCHANGE":
        # Losses are applied by grossing up drawal: to consume 1 kWh you must
        # buy 1/(1-loss) kWh at the exchange.
        energy = (mcp_rs_mwh / 1000.0) / (1.0 - cfg.transmission_loss_frac)
        non_energy = np.full_like(
            energy,
            cfg.wheeling_rs_kwh
            + cfg.cross_subsidy_rs_kwh
            + cfg.additional_surcharge_rs_kwh
            + cfg.sldc_other_rs_kwh,
        )
        label = "Open access (exchange-exposed)"
    elif cfg.mode == "DISCOM":
        # MERC prices energy for >=20 kW loads in Rs/kVAh, NOT Rs/kWh. At a
        # power factor of 0.98 that is ~2% more per kWh consumed, and getting
        # the unit wrong is exactly the kind of silent error the order's own
        # footnote warns about.
        per_kwh = cfg.retail_energy_rs_kvah / cfg.power_factor
        wheel = cfg.retail_wheeling_rs_kvah / cfg.power_factor
        energy = per_kwh * tod_multiplier(hours, cfg, month)
        non_energy = np.full_like(energy, wheel)
        label = "DISCOM retail HT tariff (MERC Case 75/2025, FY2026-27)"
    else:
        raise ValueError(f"unknown tariff mode {cfg.mode!r}")

    duty = (energy + non_energy) * cfg.electricity_duty_frac
    return LandedCost(
        total=energy + non_energy + duty,
        energy=energy,
        non_energy=non_energy,
        duty=duty,
        label=label,
    )


def demand_charge_rs_per_mw_day(cfg: TariffConfig) -> float:
    """Marginal cost of one extra MW of billing demand, for one day.

    Billing demand is in kVA; a daily horizon carries 1/days_in_month of the
    monthly charge, so the optimizer trades a real peak against a real energy
    saving rather than ignoring the peak entirely.
    """
    kva_per_mw = 1000.0 / cfg.power_factor
    return cfg.demand_charge_rs_kva_month * kva_per_mw / cfg.days_in_month()


def ratchet_floor_mw(cfg: TariffConfig) -> float:
    """Billing demand can never fall below the ratchet, so shaving below it
    earns nothing. Without this the optimizer over-values peak shaving."""
    return cfg.md_ratchet_frac * cfg.contract_demand_mw


def bill_summary(
    energy_mwh_by_block: np.ndarray,
    lc: LandedCost,
    peak_mw: float,
    cfg: TariffConfig,
) -> dict[str, float]:
    """Decompose the bill for a horizon of any length.

    The demand charge is a DAILY rate here, so it must scale with the number of
    days in the horizon. Charging it once over a multi-day window under-counts
    it by (days - 1) and makes a longer horizon look spuriously profitable --
    which is exactly what it did before this was fixed.
    """
    e_kwh = energy_mwh_by_block * 1000.0
    n_days = max(1.0, len(energy_mwh_by_block) / 96.0)
    dc = (max(peak_mw, ratchet_floor_mw(cfg))
          * demand_charge_rs_per_mw_day(cfg) * n_days)
    return {
        "energy_rs": float(np.sum(e_kwh * lc.energy)),
        "non_energy_rs": float(np.sum(e_kwh * lc.non_energy)),
        "duty_rs": float(np.sum(e_kwh * lc.duty)),
        "demand_charge_rs": float(dc),
        "total_rs": float(np.sum(e_kwh * lc.total) + dc),
        "energy_mwh": float(np.sum(energy_mwh_by_block)),
        "horizon_days": float(n_days),
        "peak_mw": float(peak_mw),
        "billing_peak_mw": float(max(peak_mw, ratchet_floor_mw(cfg))),
    }
