# SOURCES

Every number in the deck, traced to a primary document, a script in this repo,
or an explicit assumption. Anything not in this file is not in the pitch.

**Classification used throughout:**

| Tier | Meaning |
|---|---|
| **1** | Named custodian, plant- or instrument-specific, retrievable today |
| **2** | Named custodian, sector-aggregate |
| **3** | Real published engineering, technology-class not plant-specific |
| **A** | Assumption — see `ASSUMPTIONS.md`. Never presented as a measurement. |

---

## 1 · MARKET DATA

| Claim | Value | Source | Tier | Reproduce |
|---|---|---|---|---|
| IEX panel size | 152,542 blocks, 1,588 complete days | IEX RTM/DAM/G-DAM, Maharashtra bid area W2, 2022-04-01 → 2026-08-06 | 1 | `data/market_15min.csv`; `python -c "from prana import data; print(len(data.load_market()))"` |
| Evening ÷ solar price ratio | 1.47 (FY22-23) → 2.23 (FY25-26) → 3.53 (FY26-27, **Apr–Aug only**) | same panel | 1 | `python run_demo.py` beat 1 |
| Like-for-like, Apr–Aug both ends | **1.83 → 3.53** | same panel | 1 | quote this if asked whether the windows match |
| Share of year below ₹2/kWh | 4.1% → 21.1% | same panel | 1 | `run_demo.py` beat 1 |
| Price-cap regimes | ₹20,000 → ₹12,000 → ₹10,000/MWh (Apr-22 / May-22 / Apr-23) | derived empirically from the panel; 5,372 RTM blocks cleared >₹10,000 pre-Apr-2023 | 1 | `prana/data.py::CAP_REGIMES` |
| G-DAM series validity | Real for the full panel range | IEX Green Day-Ahead Market launched **27 Oct 2021**, before the panel starts (CERC circular 410) | 2 | checked; not a fill — equals DAM in only 13.7% of blocks |
| DSM rate ≈ max(DAM, RTM) | 133,056 deviation blocks | WRPC published deviation accounts | 2 | **audit lives in the thesis project, not this repo** — see ASSUMPTIONS.md A-11 |

## 2 · TARIFF — the verified core

**Primary document:** MERC Order, Case No. 75 of 2025, **post-remand proceedings, dated 25 March 2026**, 123 pp — [mahadiscom.in](https://www.mahadiscom.in/wp-content/uploads/2026/07/Tariff-Order_Case-No.-75-of-2025-dated-25th-March-2026.pdf)

The 25 June 2025 order was **quashed and set aside** by the Bombay High Court
(WP 19437/2025 & batch, 3 Nov 2025); the Supreme Court remanded on 17 Nov 2025
and extended time on 9 Feb 2026. **Do not cite the June order.** Both were
opened and compared.

| Claim | Value | Where exactly | Tier |
|---|---|---|---|
| Demand charge | **₹650/kVA/month** | p.100, "Summary of HT Tariff for FY 2026-27", HT I (A) HT-Industry, **EHV** | 1 |
| Energy charge | **₹8.44/kVAh** | same row | 1 |
| Wheeling | nil at EHV; **₹0.81/kVAh** at 33 kV (total ₹9.25) | same table, HT sub-total row | 1 |
| FY27-28 trajectory | ₹700 / ₹8.23 | p.101 | 1 |
| ToD peak | **+20%, 17:00–24:00 (7 h)** | Table 8, p.77 | 1 |
| ToD solar rebate | −15% Apr–Sep, −25% Oct–Mar (FY26-27) | Table 8 note ^ | 1 |
| Night rebate | **REMOVED**; 00:00–09:00 flat 0% | §18.13 and Table 8 | 1 |
| Units | ₹/**kVAh**, not ₹/kWh | table header | 1 |
| **Demand charge, daily marginal** | **₹22,109 per MW of peak per day** — derived: ₹650/kVA/month ÷ 0.98 power factor × 1000 kVA/MW ÷ 30 days | `prana/tariff.py::demand_charge_rs_per_mw_day` | 1 |

**Known ambiguity, disclose if asked:** Table 8 prints `+20%#` on the peak row,
but the `#` footnote does not appear anywhere in the 123-page operative order.
In the **quashed** June order that footnote read *"For HT & LT Industrial &
Commercial Categories = +25%"*. We use +20%, matching the operative text as
printed. The peak charge is what PRANA's value derives from, so this is worth
±5 percentage points and we say so rather than hide it.

## 3 · PHYSICS — chlor-alkali

**Primary document:** National Productivity Council (Govt. of India),
*Good Practices Manual — GHG Emission Reduction, Chlor-Alkali Sector*, 78 pp —
[npcindia.gov.in](https://www.npcindia.gov.in/NPC/Uploads/Competencies/Manual%20Chlor-alkali%20Sector.pdf)

| Claim | Value | Where | Tier |
|---|---|---|---|
| Cell voltage law | *"the operating cell voltage varies almost linearly with the current density… **U_cell = U_o + k · i volts**"* | p.28 | 3 |
| Empirical voltage curve | **E = 2.41 + 0.329·i + 0.24·log i** | p.29 | 3 |
| Cell-house SEC by generation | mono-polar 2,550; zero-gap 2,470; bipolar 4th-gen 2,130; 5th 2,070; 6th 2,020–2,035 kWh/t NaOH | p.25, Table 2.7 | 3 |
| Total energy benchmark | 3,040 kWh/t NaOH (0.262 TOE/t), "low end of BEE target" | p.25 | 3 |
| Co-product ratio | *"co-produce chlorine in the ratio of **1:0.89**"* | p.20 | 3 |
| Balance-of-plant load | Cl₂ liquefaction 120–200; brine purification 2.5; water treatment 1.3 kWh/t | p.25 | 3 |
| Power share of production cost | **50–60%** | p.22 | 3 |
| Indian plants >500 TPD SEC | 0.227–0.310 TOE/t (≈2,640–3,605 kWh/t incl. thermal) | p.19, Table 2.2 | 3 |

**What this grounds and what it does not.** It grounds the convexity, the SEC
band, the co-product ratio and the BoP share. **It does not ground turndown,
ramp rate, buffer size, the chlorine consumer's floor, or membrane cycling
cost** — those are in `ASSUMPTIONS.md`.

**Convexity check, and it goes against us in the honest direction.** Fitting
NPC's p.29 equation over 40–108% load implies a quadratic coefficient of
**0.30 (at 3 kA/m²) to 0.45 (at 6 kA/m²)**; the twin uses **0.21**. PRANA
therefore *understates* the round-trip loss. Re-running the headline with
NPC-grounded coefficients moves it **up** 6% (₹10.90 → ₹11.55 cr/yr on a
45-day sample). We keep the conservative number.

## 4 · FERTILISER — why it is not the flexibility play

**Primary document:** Department of Fertilizers, *Urea Policy (Pricing and
Administration)* — New Urea Policy-2015 (notified 25 May 2015) and the
amendment notification of **28 March 2018**.

| Claim | Value | Tier |
|---|---|---|
| Target Energy Norms | **5.5 / 6.2 / 6.5 Gcal/MT** for Groups I / II / III; one named unit at 5.417 | 1 |
| Coverage | 25 gas-based urea units, **named individually** in the notification | 1 |
| Subsidy mechanism | MRP statutorily fixed; subsidy = cost of production − MRP, reimbursed **on a normative basis** — plants in the same group receive the same amount **irrespective of actual energy consumed** | 1 |
| Fixed-cost recovery | *"For production upto 100% re-assessed capacity (RAC), the units are entitled to get total cost of production… which includes fixed cost and variable cost"* | 1 |
| Penalty for exceeding norm | 2% (FY18-19) then 5% (FY19-20) of the energy difference | 1 |
| **Electricity is excluded from the norm** | *"other variable cost e.g. the cost of bag, water charges & **electricity charges** … determined in accordance with NPS-III"* | 1 |

**PAT corroboration is partial, and stated as such.** Fertiliser has been a BEE
PAT sector since Cycle I; Cycle I delivered 0.78 MTOE against a 0.477 MTOE
target, and fertiliser was one of two sectors that missed in PAT II. This
establishes that specific energy is tracked and enforced sector-wide. **It does
not measure capacity utilisation**, so it is corroboration of the incentive
structure, not evidence of flat operation.

**The argument we make, scoped to exactly what the above supports:**

> India's urea subsidy is paid normatively — a government-set energy norm per
> tonne, with fixed costs recovered only through production up to re-assessed
> capacity, and a penalty for exceeding the norm. A plant that runs below
> capacity recovers less fixed cost, and part-load operation raises Gcal/tonne
> against a norm that does not move. **The economics of the sector reward
> continuous operation at design rate.** This is an argument from the
> regulatory and subsidy structure. We have not measured capacity factors
> across the sector and do not claim to.

## 5 · STORAGE COMPARATOR

| Claim | Value | Source | Tier |
|---|---|---|---|
| Oil India crude pipeline | **1,157 km**, Assam to Barauni | Oil India Limited corporate disclosure | 2 |
| National storage requirement | 73.93 GW / **411.4 GWh** by 2031-32 — of which **BESS 47.24 GW / 236.22 GWh**, rest pumped hydro | CEA National Electricity Plan (Vol-I Generation), 2022-32 | 2 |
| BESS capex | **₹0.6–1.1 crore/MWh** — VGF Tranche II ceiling ₹18 lakh/MWh implies the low end; Ember reports long-duration utility-scale project cost ≈ $125/kWh ≈ ₹1.04 cr/MWh | VGF scheme; Ember via Mercom | 2 |

**Say "411 GWh of storage, 236 GWh of it batteries."** Calling the whole 411
"batteries" includes pumped hydro and a policy person will catch it.

## 6 · RESULTS — all reproducible from this repo

| Result | Value | Command |
|---|---|---|
| Headline, forecast error | ₹0.133/kWh · ₹9.17 cr/yr · 13 bad days · **0 violations** | `python -m prana.backtest --days 120 --forecast --site chloralkali` |
| Perfect foresight | ₹0.174/kWh · ₹12.07 cr/yr · 0 bad days | `python -m prana.backtest --days 120 --site chloralkali` |
| Costs netted out | −₹76.8 lakh of ₹378.3 lakh gross (20%) → **net ₹301.5 lakh** over 120 days | same run, "less: wear + Cl2 dumped + kVAh" |
| **vs a production-neutral ToD rule** | rule captures **18%**; PRANA's incremental value **₹8.48 cr/yr**; rule loses money on 15 of 60 days | `python tod_baseline.py` |
| Chlorine-floor sensitivity | 60%→₹10.99cr, 70%→₹10.90cr, 80%→₹10.45cr, 90%→₹7.46cr (45-day) | in-session sweep |
| Forecast skill | MAE 1,072 vs naive 1,189 / DAM 1,271 / 7-day mean 1,538 ₹/MWh | `prana/forecast.py` metrics |
| No leakage | trained through 2026-03-31; tested 2026-04-09 → 2026-08-06 | `QuantileForecaster.load().trained_through` |
| Regression tests | 48 passing | `python -m pytest tests -q` |


## 6A · THE DEMO DAY — every figure on slide 8

All from `python run_demo.py --site chloralkali`, delivery day **2026-07-12**,
perfect foresight, settled at realised landed cost. Reproduces in 22 s from a
clean clone. **This day saves 1.72x the 120-day mean** — it is a demonstration
day, not a typical one, and the slide says so.

| Figure | Steady state | PRANA | Tier |
|---|---|---|---|
| Energy | 1,896.0 MWh | 1,900.5 MWh (+4.5) | model output |
| Peak billing demand | **79.00 MW** | **82.88 MW** (+3.88) | model output |
| Landed cost paid | **₹7.438/kWh** | **₹7.193/kWh** (−0.245) | model output |
| Day's bill | ₹1,41,01,716 | ₹1,36,70,393 | model output |
| Avoided | — | **₹431,324 = ₹4.31 lakh** | model output |
| As % of day's bill | — | **3.06%** | derived |
| Deviation used | — | 0.000000 MW | model output |
| Violations vs true physics | — | 0 | verifier |
| Binding constraint | — | Cl₂ consumer min take, 11 of 96 blocks | solver |

**The peak went UP by 3.88 MW.** That is the demand-charge trade-off being made
explicitly: 3.88 MW × ₹22,109 = **₹85,783/day** of extra demand charge, accepted
because the energy saving exceeded it. An optimiser that could not see the
demand charge would not have known the price of that decision.

## 6B · DERIVED RATES AND REMAINING SLIDE FIGURES

| Figure | Value | Calculation / source | Tier |
|---|---|---|---|
| Net saving per day | **₹2.51 lakh** | 120-day mean, `backtest_chloralkali_forecast.csv` | model output |
| Net saving per hour | **₹10,463** | ₹2.51 lakh ÷ 24 | derived |
| Net saving per month | **₹76.4 lakh** | ₹2.51 lakh × 30.4 | derived |
| Net saving per year | ₹9.17 crore | ₹251,319 × 365 | derived |
| Forecast interval coverage | **76.2%** | after out-of-sample conformal widening (69.7% raw), target 80% | model output |
| Tangent linearisation error | **0.025%** | `ProcessTwin.max_linearization_error()`, chlor-alkali twin | model output |
| Caustic installed capacity | **64.04 lakh MTPA** (Mar 2025) | Alkali Manufacturers Association of India | 2 |
| Capacity utilisation | **78.4%** (FY2024-25) | AMAI — production 50.20 lakh MT | 2 |
| Sector energy base | 2,300 kWh/t assumed membrane-cell SEC | inside NPC's 2,020–2,550 cell-house band | 3 |

## 6C · APPENDIX FIGURES

| Figure | Value | Basis | Tier |
|---|---|---|---|
| Forecast-error haircut | **24%** | ₹0.133 (forecast) vs ₹0.174 (perfect foresight) per kWh, same 120 days | derived |
| Deliverable virtual battery | **21.8 MW / 748 MWh** | at the 70% chlorine-consumer floor | model output |
| Withdrawn battery claim | 41 MW / 1,410 MWh | quoted against the cell's 40% safety interlock — **corrected downward**, roughly halved | withdrawn |
| Infeasible-solve bug | demo reported an outage as a **₹165,121 saving** | fixed; solver status now gated before any figure prints | error log |
| Horizon-scaling bug | spurious **+317%** multi-day value | demand charge is a daily rate; fixed, true value +16.2% | error log |
| ToD-baseline bug | rule appeared to beat PRANA by **382%** | terminal-inventory charge omitted; fixed, rule captures 18% | error log |

## 7 · RELATED WORK — and where PRANA actually sits

Chlor-alkali demand response is an **established, active research area**, not an
open problem. Treating it as novel would be the fastest way to lose credibility
with anyone who follows AIChE or Applied Energy.

**The field.** Otashu & Baldea (UT Austin) built DR-oriented dynamic models and
scheduling frameworks for membrane chlor-alkali plants (*Comput. Chem. Eng.*
2019; *Applied Energy* 2020, frequency regulation). Weigert, Hoffmann, Esche,
Fischer & Repke (TU Berlin) produced the first such dynamic model **validated
against real industrial plant data** (*Comput. Chem. Eng.* 2021). Richstein &
Hosseinioun (DIW Berlin) modelled the chlor-alkali process *with a storable
intermediate good* against network tariffs (*Applied Energy* 278, 2020).
Techno-economic comparisons of flexibility retrofits appear in *I&EC Research*
(2020) and *Applied Energy* (2023).

**Their numbers.** Published electricity-cost savings cluster at **~4%** under
time-dependent tariffs (I&EC 2020) and **5.8%** on 2019 price distributions
(Applied Energy 2023); profit improvement reaches **~10%** when reserve-market
participation is included. **PRANA's 1.53% of the electricity bill sits below
this entire range.** Two structural reasons, both real: India's demand charge on
peak billing kVA penalises the peak that load-shifting creates, and the chlorine
consumer's turndown binds the shed to 70% of design. *Caveat on the comparison:*
PRANA's denominator is the **full landed bill** (energy + demand charge +
surcharges + duty); several of these papers use energy or wholesale cost alone.
A larger denominator mechanically depresses the percentage, so read this as
directional conservatism, not a like-for-like ratio.

**Independent corroboration of our binding constraint.** Weigert et al. (2021)
state that the electrolysis *"cannot be operated flexibly by itself as storing
chlorine is avoided in practice due to safety concerns"*, and locate the
flexibility in downstream 1,2-dichloroethane storage instead. That is the same
structural ceiling PRANA derived independently and encodes as the chlorine
consumer's minimum take. A separate *Applied Energy* (2020) paper is devoted to
the chlorine value chain's limiting effect on DR potential.

**What is actually new here — and only this:**

1. A **real four-year settled Indian price panel** (152,542 blocks, IEX
   Maharashtra W2). The reviewed literature is European/US and largely uses
   exchange or stylised prices.
2. A **primary Indian regulatory tariff order opened to the page** — MERC Case
   75 of 2025, post-remand, p.100 — including establishing that the widely
   circulated June 2025 order was quashed.
3. A **landed-cost engine**: ToD multipliers, open-access surcharges, duty and
   the demand charge on peak kVA, dispatched inside the MILP rather than as a
   post-hoc adjustment. None of the reviewed papers price an Indian regulatory
   stack.

**Not claimed as new:** the buffer-as-battery framing, the convex power curve,
DR scheduling of chlor-alkali, or the observation that demand charges impede
flexibility. All predate this work.

## 8 · COLD START

```bash
git clone <repo> && cd Hackathon_PRANA
pip install -r requirements.txt
python run_demo.py --site chloralkali
```

The market panel and the fitted model ship with the repo. Verified from a clean
copy with `PRANA_IEX_DIR` pointing at a non-existent directory: it runs.
