"""PRANA configuration: paths, market constants, tariff placeholders.

EVERY number here is either (a) a market/physical constant with a stated source,
or (b) a PLACEHOLDER that must be replaced with a verified figure before the
number is quoted anywhere. Placeholders are tagged. Do not remove the tags.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"

# The cached IEX panel SHIPS with the repo (data/market_15min.csv) so a fresh
# clone runs with no external dependency. Only if that cache is missing does
# PRANA try to rebuild it from raw segment files, whose location comes from the
# PRANA_IEX_DIR environment variable. A hardcoded absolute path into one
# person's home directory is not a data source — it is an unreproducible
# result, and it is the difference between evidence and an assertion.
RAW_IEX_DIR = Path(os.environ.get("PRANA_IEX_DIR", str(DATA_DIR / "raw_iex")))
MARKET_CACHE = DATA_DIR / "market_15min.csv"

# ---------------------------------------------------------------- market
BLOCKS_PER_DAY = 96
DT_H = 0.25                       # hours per settlement block
PRICE_CAP_RS_MWH = 10_000.0       # CERC cap on DAM/RTM
PRICE_FLOOR_RS_MWH = 0.0

SOLAR_WINDOW = (9, 17)            # hours [start, end)
EVENING_WINDOW = (18, 24)

DEMO_DATE = "2026-07-12"          # RTM Rs 1/MWh @13:00 -> Rs 10,000/MWh @00:00


@dataclass
class TariffConfig:
    """Landed cost of electricity at the meter, Rs/kWh unless noted.

    Two supply modes:
      EXCHANGE  open access / exchange-exposed: energy at MCP + OA charge stack
      DISCOM    utility retail HT tariff with a ToD multiplier
    """

    mode: str = "EXCHANGE"                 # EXCHANGE | DISCOM

    # --- exchange / open-access route -------------------------------------
    transmission_loss_frac: float = 0.0357   # PLACEHOLDER: MSLDC/InSTS loss %
    wheeling_rs_kwh: float = 1.08            # PLACEHOLDER: MERC wheeling charge
    cross_subsidy_rs_kwh: float = 1.31       # PLACEHOLDER: MERC CSS, HT-Ind
    additional_surcharge_rs_kwh: float = 0.0  # PLACEHOLDER: MERC MYT para 11.1.3
    # ^ THE PARAGRAPH THAT FLIPS THE SIGN. 0.0 = waiver applied. Set to ~1.39
    #   to test the no-waiver case. This parse is NOT yet verified; see the
    #   thesis PROBLEM_STATEMENT_V2.md. Never quote a headline without saying
    #   which value was used.
    sldc_other_rs_kwh: float = 0.06          # PLACEHOLDER: SLDC + misc

    # --- discom retail route ----------------------------------------------
    # VERIFIED against MERC Order, Case No. 75 of 2025 (post-remand, the
    # operative order -- the 25-Jun-2025 order was QUASHED by the Bombay High
    # Court). "Summary of HT Tariff for FY 2026-27, effective 1 April 2026",
    # category HT I (A) HT - Industry, EHV.
    #
    #   FY26-27  Rs 650/kVA/month   Rs 8.44/kVAh      <- the backtest period
    #   FY27-28  Rs 700             Rs 8.23
    #   FY28-29  Rs 730             Rs 7.52
    #   FY29-30  Rs 750             Rs 7.45
    #   (FY25-26 was Rs 600 / Rs 8.68; prior year Rs 549 / Rs 8.98)
    #
    # A 33 kV connection adds ~Rs 0.81/kVAh wheeling (sub-total Rs 9.25/kVAh).
    retail_energy_rs_kvah: float = 8.44      # VERIFIED FY2026-27, EHV
    retail_wheeling_rs_kvah: float = 0.0     # 0.81 if 33 kV instead of EHV

    # ToD, Table 8 of the same order, "as % of Energy Charge" for HT categories.
    # THREE THINGS HERE ARE NOT WHAT A TRADE-PRESS SUMMARY WOULD TELL YOU:
    #   1. The peak window is 17:00-24:00 (7 h), not 17:00-22:00.
    #   2. The solar rebate is SEASONAL: -15% Apr-Sep, -25% Oct-Mar in FY26-27.
    #   3. The night rebate WAS REMOVED. Para 18.13: the Commission "decided to
    #      remove the ToD tariff rebate applicable for night hours", because
    #      rebating at night is "inconsistent with the objective of encouraging
    #      load shifting to solar hours". 00:00-09:00 is now flat 0%.
    # Rebate escalates: -15%/-25% (FY26, FY27) then -20%/-30% thereafter.
    tod_solar_mult_apr_sep: float = 0.85     # VERIFIED: -15%
    tod_solar_mult_oct_mar: float = 0.75     # VERIFIED: -25%
    tod_peak_mult: float = 1.20              # VERIFIED: +20%, 17:00-24:00
    tod_offpeak_mult: float = 1.00           # VERIFIED: 00:00-09:00 is 0%

    # --- deviation settlement --------------------------------------------
    # Our DSM reference is max(DAM, RTM) computed on IEX alone; IEX is one of
    # three exchanges, so the published rate is >= our estimate. 2% is a
    # conservative allowance, and it is what stops the optimizer treating
    # deviation as free in the blocks where RTM itself sets the maximum.
    dsm_uplift_frac: float = 0.02

    # --- both routes ------------------------------------------------------
    electricity_duty_frac: float = 0.093     # PLACEHOLDER: MH electricity duty

    # --- demand charge: THE TERM EVERYONE FORGETS -------------------------
    # VERIFIED: MERC Case 75/2025 post-remand, HT I (A) HT-Industry, FY2026-27.
    demand_charge_rs_kva_month: float = 650.0  # VERIFIED FY2026-27
    power_factor: float = 0.98
    contract_demand_mw: float = 110.0
    md_ratchet_frac: float = 0.75            # billing demand >= 75% of contract

    def days_in_month(self) -> int:
        return 30


@dataclass
class SiteConfig:
    """The plant as a whole."""

    name: str = "Refinery utilities block (illustrative 100 MW site)"
    base_load_mw: float = 62.0     # non-flexible: crude unit, reformer, lighting
    tariff: TariffConfig = field(default_factory=TariffConfig)

    # Risk aversion on the CVaR term. 0 = expected cost only.
    cvar_weight: float = 0.35
    cvar_alpha: float = 0.95

    # Grid emission factor for the CO2 tile. APPROXIMATE — cite CEA CO2
    # Baseline Database and label it as an estimate on any slide.
    grid_ef_tco2_mwh_peak: float = 0.90
    grid_ef_tco2_mwh_solar: float = 0.55
