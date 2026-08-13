# PRANA — Master Brief
### Everything about this project, start to end, in one document

> ## ⚠ THE NUMBERS IN THIS FILE ARE SUPERSEDED — READ `SUBMIT_THIS.md` FOR ANY FIGURE
>
> This brief was written for the **refinery utilities** site, before two things
> happened: the project was re-aimed at **chlor-alkali**, and an engineering
> review forced four corrections into the model (the chlorine balance, membrane
> cycling cost, power-factor droop on kVAh billing, and single-train derates).
>
> | | This file says | Current, verified |
> |---|---|---|
> | Site | Refinery utilities block | **Chlor-alkali cell house** |
> | Saving, forecast error | ₹0.260/kWh · ₹21.2 cr/yr | **₹0.133/kWh · ₹9.17 cr/yr** |
> | Virtual battery | 28 MW / 294 MWh | **21.8 MW / 748 MWh** |
> | Days worse than steady state | 0 of 120 | **13 of 120** |
> | Tariff | ₹590/kVA placeholder | **₹650/kVA, MERC Case 75/2025 verified** |
>
> **Do not quote a rupee figure from this file.** What remains valid and worth
> studying here: the physics derivation, the model choices and why each one, the
> architecture, and the presentation guidance. `SUBMIT_THIS.md` §8 and §13 carry
> every current number and the record of what changed.

**Purpose of this file.** You should be able to read this once and then defend the
entire project to a hostile panel without opening anything else. It covers what
the problem is, why the idea works physically, every model and why that model
and not another, every number and where it came from, what the impact is at
three different scales, what is *not* true yet, and how to present it.

**Reading order if you are short on time:** §1 (the idea in one page) → §4 (the
physics) → §8 (results) → §12 (how to present). Everything else is depth for
Q&A.

**Companion files.** `SUBMIT_THIS.md` is the operative submission and the only
source for numbers. `README.md` is the repo guide.

---

# TABLE OF CONTENTS

| § | Section |
|---|---|
| 1 | The whole project in one page |
| 2 | Where this came from |
| 3 | The problem, with the data behind it |
| 4 | The core insight and its physics |
| 5 | Every model: what, why, and what it rejects |
| 6 | The data layer |
| 7 | Architecture and code map |
| 8 | Results — every number and its provenance |
| 9 | Impact — how much changes, at three scales |
| 10 | Bugs found during the build (and why they matter) |
| 11 | Limitations and what is not yet true |
| 12 | How to present it |
| 13 | Q&A bank |
| 14 | Glossary |

---

# §1 · THE WHOLE PROJECT IN ONE PAGE

**The observation.** India's power problem stopped being *how much* and became
*when*. On four years of real 15-minute settlement data, the ratio of evening
price to midday price went from 1.47 to 3.53. Midday is nearly free; the evening
hits the ₹10/kWh regulatory cap.

**The consensus answer** is to build batteries — 73.9 GW / 411 GWh by 2031-32.
That has to happen. But it frames storage as something to *construct*.

**The insight.** Every process plant already owns storage. An air separation
unit's cryogenic tank, a refinery's hydrogen buffer, a pipeline's tankage, an
ammonia plant's liquid-NH₃ tank — each is a battery whose **state of charge is
inventory** and whose **round-trip loss is a process-efficiency penalty**. None
of it is dispatched.

**Why not?** Not because the optimization is hard — that is a solved problem.
Because **no plant can write down its own constraints.** Ask how many MW it can
move, for how long, at what cost, without touching product spec: no document
answers. The answer is in the interlock list, the HAZOP minutes, and a board
operator's head.

**What PRANA is.** Three layers:

1. A **physics digital twin** per asset that outputs a *flexibility cost curve*
   φ(ΔMW, Δt) — the ₹/MWh cost of shedding ΔMW for Δt hours. This object does
   not currently exist in Indian industry.
2. A **stochastic MILP** that dispatches 96 blocks/day against the **landed**
   cost of power — the price at the meter, not the exchange — under a CVaR risk
   term.
3. An **LLM agent** that extracts constraints from SOPs and operator speech into
   a typed, sign-off-gated form, and explains each schedule *from the solver's
   own binding constraints*.

**What it delivers, measured.** On a 105 MW refinery utilities block, 120
consecutive real days, with real forecast error, net of bought-in hydrogen:
**₹0.260 per kWh of total plant load** — ₹21.2 crore/year — with **zero days
worse than doing nothing** and **zero constraint violations** under independent
verification. The same three assets are a **28 MW / 294 MWh virtual battery at
zero capex**, roughly ₹323 crore of battery investment displaced.

**The single most important result.** Same plant, same day, same optimizer;
change only whether the demand charge is modelled:

| Demand charge | Peak | Electrolyser dispatch |
|---|---|---|
| ₹590/kVA/month (reality) | 94.6 MW | **1 of 96 blocks** |
| ₹0 (what MCP-only tools assume) | 110.0 MW | **20 of 96 blocks** |

Every tool that optimizes on the exchange clearing price is giving Indian
industry a materially wrong answer, and the error is ~40% of the bill.

---

# §2 · WHERE THIS CAME FROM

Three prior threads converge here. Knowing this matters, because a judge asking
"how did you get here so fast?" deserves the real answer.

**Thread 1 — the earlier course project** ("Can Renewable Energy Solve India's
Peak Demand?"). Five models on CEA/POSOCO data. Its conclusion: renewables solve
the *energy* problem but not the *peak timing* problem; storage is required. Its
BESS NPV sensitivity came out negative in all 63 cells — **which is where PRANA
started.** If building storage does not pencil, look for storage that is already
built. (That sensitivity has an axis error; see §11.)

**Thread 2 — the MBA thesis.** Four years of IEX settlement data already
collected, cleaned and verified: 152,542 blocks across DAM, RTM and G-DAM for the
Maharashtra bid area. Plus a regulatory cost-stack model built by reading primary
MERC orders, and an audit of 133,056 WRPC deviation-settlement blocks. **PRANA
reuses all of it.** That is why a hackathon MVP has a four-year validated panel
behind it.

**Thread 3 — the plant.** Chemical engineering at NIT Rourkela, then energy
efficiency and DCS work on an ammonia–urea plant. This supplies the thing neither
dataset can: knowing what a synthesis loop will and will not tolerate. The
ammonia twin in `prana/twins.py` is the direct expression of it.

**Why the intersection is the point.** The energy-software industry hires power
engineers. The process industry hires chemical engineers. Someone who can read a
P&ID *and* formulate a MILP is rare — and §3's Problem 2 exists precisely because
that intersection is empty.

---

# §3 · THE PROBLEM, WITH THE DATA BEHIND IT

Three problems, all evidenced from the panel.

## 3.1 India's grid problem is no longer *how much*. It is *when*.

Computed on RTM prices, Maharashtra W2:

| FY | Blocks | share < ₹2/kWh | solar 09–17 | evening 18–23 | **ratio** | median intraday spread |
|---|---|---|---|---|---|---|
| 2022-23 | 35,040 | 4.1% | ₹4.82 | ₹7.08 | **1.47** | ₹8,999/MWh |
| 2023-24 | 35,136 | 4.9% | ₹4.32 | ₹6.32 | **1.46** | ₹7,200 |
| 2024-25 | 35,038 | 8.8% | ₹3.11 | ₹5.82 | **1.87** | ₹7,943 |
| 2025-26 | 35,040 | 17.0% | ₹2.35 | ₹5.22 | **2.23** | ₹8,128 |
| 2026-27\* | 12,288 | 21.1% | ₹2.00 | ₹7.06 | **3.53** | ₹9,424 |

\* **April–August 2026 only.** India's peak-demand *and* peak-solar months.
Seasonally biased upward. Say this out loud every time the row appears — a judge
who catches an unlabelled seasonal figure will discount everything else you said.

**What it means.** A flat industrial load profile is now paying a large and
growing penalty for being flat. The shape of the price curve, not its level, is
where the money is.

## 3.2 The binding constraint on industrial flexibility is *epistemic*

India has run demand-response pilots for over a decade with no regulator-approved
flexibility market. The usual diagnosis — "no market mechanism" — is incomplete.
Even where a mechanism exists (exchange exposure, ToD tariffs, demand-charge
management all exist *today*), plants do not participate, because they cannot
quantify their own production risk. An unquantified risk always beats a
quantified saving.

**Why it stays unsolved:** it needs a P&ID reader who can also formulate a MILP.

## 3.3 Everyone optimizes on exchange price. The exchange price is not the bill.

The market clearing price is roughly 60% of what an Indian industrial consumer
pays. The rest: wheeling, cross-subsidy surcharge, additional surcharge,
electricity duty, and a **demand charge on peak billing kVA with a ratchet.**

Measured in this model: **non-energy charges are 46% of landed cost** at typical
prices, and the demand charge is worth **₹20,068 per MW of peak per day**.

The consequence is not academic. It **changes the answer** — see §8.4.

---

# §4 · THE CORE INSIGHT AND ITS PHYSICS

This is the section to understand properly. Everything else follows from it.

## 4.1 The reframe

A battery stores **electrons**; its state variable is state-of-charge and its
loss is round-trip efficiency. A process buffer stores **molecules**; its state
variable is **inventory** and its loss is a **process-efficiency penalty**.

| | Electrochemical battery | Process buffer |
|---|---|---|
| State of charge | kWh in cells | tonnes / kg / kL in a tank |
| Charge | rectifier draws power | run the process *above* demand |
| Discharge | inverter exports | run *below* demand, serve from tank |
| Round-trip loss | ~10–15% electrical | extra kWh per unit of product |
| Capex | ₹1.0–1.2 crore/MWh | **already spent** |
| Limits | C-rate, DoD, cycles | ramp rate, min stable load, product spec |

## 4.2 Why flexibility is not free — the convexity argument

Model electrical power as a function of production rate:

> **P(x) = P_nom · (a + b·x + c·x²)**,  where x = q / q_nom and a + b + c = 1

with a > 0 (fixed/standby losses), b > 0, c > 0 (off-design and throttling
losses). Then specific energy consumption is

> **SEC(x) = P(x)/q = (P_nom/q_nom) · (a/x + b + c·x)**

which is **U-shaped**, with its minimum at **x\* = √(a/c)**. The coefficients are
chosen so x\* = 1, i.e. the plant is most efficient at its design point — which is
what "design point" means.

**The consequence, and it is the whole argument:** because P(x) is **convex**,
splitting production into a low leg and a high leg always burns more kWh than
running steady, *even though total product is identical*. That excess is real,
physical, and unavoidable. It is the exact analogue of (1−RTE)/RTE for a battery.

## 4.3 The flexibility cost curve φ(ΔMW, Δt)

For a load reduction of ΔMW held for Δt hours, the plant must:

1. turn down to q_down, producing less at worse specific energy;
2. serve unchanged downstream demand from inventory for Δt hours;
3. rebuild that inventory afterwards at q_up, again at worse specific energy.

Product delivered is identical to running flat, by construction. Energy is not:

> **φ = (E_flex − E_flat) / (ΔMW · Δt)**   [₹ per MWh actually shifted]

Returned against a ₹1/kWh reference so the curve is a pure *process* cost; the
optimizer prices the market separately. **φ = ∞** means the flexibility does not
exist at that depth and duration — the buffer cannot cover it, or the turn-down
would breach minimum stable load. A curve that were finite everywhere would be
promising flexibility that isn't there.

**This is the novel object.** Not the optimizer, not the forecast. Nobody in
Indian industry has this number for their own plant.

## 4.4 The four archetypes, and why four

| Archetype | P_nom | SEC @ design | Turndown | Ramp | Shed | Buffer | Virtual MWh | Trippable? |
|---|---|---|---|---|---|---|---|---|
| Air separation unit | 20.0 MW | 500 kWh/t | 55% | 40%/h | 8.6 MW | 13.3 h | 115 | no |
| Green H₂ electrolyser | 15.0 MW | 50 kWh/kg | 15% | 240%/h | 12.1 MW | 5.1 h | 62 | yes |
| Pipeline pumping | 8.0 MW | 8.9 kWh/kL | 45% | 80%/h | 7.3 MW | 16.2 h | 118 | yes |
| **Ammonia synthesis loop** | 10.9 MW | 149.5 kWh/t | 65% | **3%/h** | 3.6 MW | **62.7 h** | **227** | **NO** |

**φ(ΔMW, 4h), ₹ per MWh shifted:**

| Archetype | 1 MW | 2 MW | 3 MW | 4 MW | 6 MW |
|---|---|---|---|---|---|
| Electrolyser | 7 | 11 | 15 | 20 | 28 |
| ASU | 15 | 20 | 26 | 31 | 42 |
| Ammonia | 22 | 37 | 53 | — | — |
| **Pipeline** | **175** | **234** | **305** | **392** | **665** |

**Read the table out loud on stage — it is the technical high point.**

- The **pipeline sits ~10× above the electrolyser.** That is not a parameter
  choice; it is the hydraulic cube law. Head loss scales with the square of
  throughput, so pump power scales with the **cube**. Convexity that steep makes
  flexibility genuinely expensive.
- The **electrolyser is the cheapest** because its part-load curve is flattest.
- The **ammonia loop is the deepest and slowest**: 3%/h ramp, 62.7 hours of
  buffer, 227 MWh from a single asset, and it can never be tripped — a restart is
  a multi-day event with catalyst risk.

**Why four archetypes and not one:** they are complementary in *duration*, not
redundant. The electrolyser is fast and shallow; ammonia is slow and deep. A
portfolio covers a price curve that a single asset cannot. That is the argument
for a platform rather than a point solution.

## 4.5 Making it MILP-safe

P(q) is convex, so it is represented by **16 tangent hyperplanes**:

> p ≥ slopeₖ · q + interceptₖ,  for k = 1…16

The maximum of tangents to a convex function is a valid **outer (lower-bounding)**
approximation — the optimizer can never claim production is cheaper than physics
allows. Worst-case understatement, measured:

| Archetype | Linearization error |
|---|---|
| Ammonia | 0.004% |
| ASU | 0.005% |
| Electrolyser | 0.023% |
| Pipeline (cube law) | 0.622% |

All under 1%, and asserted by a test.

---

# §5 · EVERY MODEL: WHAT, WHY, AND WHAT IT REJECTS

Five modelling components. For each: what it does, why this method, and what was
deliberately *not* used. The rejections matter more than the choices in Q&A.

## 5.1 The process digital twin — first-principles reduced-order model

**Does:** maps production rate → power, inventory dynamics, ramp, min stable
load, min up/down time, start cost; emits φ(ΔMW, Δt) and the operating envelope.

**Method:** convex quadratic power curve (cube law for the pipeline), fitted to
plant historian data at commissioning.

**Why not a neural network / pure ML twin?** Because it must extrapolate to
operating points the plant has **never visited** — and that is exactly where
flexibility lives. A plant run flat for ten years has no data at 60% load. An ML
twin trained on that history would confidently interpolate nonsense. First
principles extrapolate; curve-fits do not. **This is the strongest technical
answer in the whole project — memorise it.**

**Why not a full rigorous simulation (Aspen Plus / gPROMS)?** Too slow to sit
inside a 96-block optimization solved every 15 minutes, and it needs a level of
plant detail no one will hand a startup on day one. A reduced-order model is the
right fidelity for a *scheduling* decision.

## 5.2 The landed-cost engine

**Does:** converts market price → ₹/kWh at the meter, and exposes the demand
charge separately because it is levied on **peak kVA**, not energy.

```
EXCHANGE route:  energy = MCP/1000 / (1 − loss)
                 + wheeling + cross-subsidy + additional surcharge + SLDC
                 + electricity duty on the sum
DISCOM route:    retail energy charge × ToD multiplier + duty
BOTH:            + demand charge on max(peak, ratchet floor) × ₹/kVA/month/days
```

**Why it matters more than the optimizer:** it is 46% of the cost and it changes
the *answer*, not just the number (§8.4).

**Why not just use MCP?** Because that is what everyone else does and it is
wrong. See §8.4.

## 5.3 The price forecaster — LightGBM quantile regression

**Does:** predicts the q10 / q50 / q90 distribution of RTM price for each of 96
blocks, so the optimizer can take a *risk-aware* decision.

**Method:** three gradient-boosted models (500 trees each), objective
`quantile` at α = 0.10 / 0.50 / 0.90. 15 features, all causal.

**The lead feature is the day-ahead price for the same delivery block** — known
12–36 hours before delivery, correlating 0.811 with real-time price, beating
same-block previous-day persistence at 0.765.

**Conformal calibration.** Quantile GBMs systematically under-cover on
heavy-tailed price data. Raw 80% interval covered only 69.7%. A single
multiplicative widening factor, fitted **out-of-sample** on a held-out 90-day
calibration slice, lifts it to **76.2%** (factor ×1.20). Still short of 80% — the
test period is more volatile than the calibration window. **Reported, not tuned
away**; it means the CVaR term is mildly optimistic.

**Why quantiles and not a point forecast?** Because the buffer decision is
inherently a risk decision. A point forecast makes the MILP overconfident, and
CVaR needs a distribution.

**Why not LSTM / transformer?** Gradient boosting is the strong baseline on
tabular electricity-price data, trains in minutes, and — crucially — the value
here is small anyway (§5.6). Spending the build on a deep model would optimize
the least important lever.

**Why not ARIMA/SARIMAX?** Cannot use the day-ahead price as an exogenous
lead feature nearly as effectively, and it is beaten by the naive baselines this
model already beats.

## 5.4 The dispatch optimizer — stochastic MILP with CVaR

**Does:** chooses production, power, inventory, on/off, procurement leg and peak
demand for all 96 blocks.

**Size (measured):** **1,757 variables** (1,373 continuous + **384 binary**),
**8,646 constraints**. Solved by **CBC** in 0.3–13 s.

**Objective:**

```
min  (1−λ)·E[cost] + λ·CVaR₉₅[cost]
     + start costs + bought-in product cost + demand charge
```

CVaR uses the Rockafellar–Uryasev linearization over three price scenarios drawn
from the forecast fan (q10/q50/q90, probabilities 0.25/0.50/0.25). The dispatch
is a single here-and-now decision; only the cost differs by scenario.

**Note the convex combination.** Writing `E + λ·CVaR` instead silently scales the
energy term by (1+λ) against the demand-charge and make-vs-buy terms, distorting
every trade-off. This was a real bug — see §10.2.

**Procurement legs:** hourly day-ahead, 15-minute real-time buy, real-time
sell-back (capped at the day-ahead position — a consumer with no generation
cannot run a trading desk), and **deliberate deviation**.

**Why the deviation lever exists at all:** to prove a negative *on stage*. The
optimizer is free to use it and never does. See §8.3.

**Why MILP and not reinforcement learning?** Three reasons, and give all three:
(1) no simulator of sufficient fidelity exists to train against; (2) no safety
guarantee — an RL policy can propose anything, and a PSU will not accept an
unexplainable setpoint; (3) MILP gives **duals** — the shadow price of every
plant constraint. That number is itself a product: it tells the plant what its
own operating rules cost.

**Why not a simple heuristic (charge cheap / discharge dear)?** Because it
cannot respect min-up/min-down, ramp, terminal inventory, contract demand and the
peak-demand trade-off simultaneously — and the peak-demand trade-off is exactly
where naive approaches lose money.

## 5.5 The constraint agent — LLM with structured outputs

**Does three jobs:**

| Function | Input | Output |
|---|---|---|
| `elicit()` | SOP extract, interlock list, handover note | typed `Constraint[]` + `unresolved[]` |
| `perturb()` | one operator sentence, mid-shift | typed `Constraint[]` |
| `explain()` | a solved `Schedule` | plain-language reasoning |

**Model:** a provider-configurable LLM, **structured outputs** via a JSON
schema so the model cannot return prose where constraints are expected.

**The architectural decision that makes it trustworthy:** `explain()` does **not**
ask the model to produce a reason. Reasons come from `Schedule.binding`, which
the optimizer derives from active bounds in the solution. The LLM only *phrases*
facts the solver produced. **It cannot hallucinate a reason, because it is never
asked for one.** Say this exact sentence if anyone raises hallucination.

**Sign-off is mandatory.** Every `Extraction` carries `requires_signoff=True`.
The agent proposes; a human accepts.

**It surfaces ambiguity rather than resolving it.** Given "Ensure the reformer
feed is never interrupted," it returns *nothing* and flags the sentence for the
operator. Guessing there would be worse than useless.

**Graceful degradation, never silent.** With no API key it falls back to a
deterministic parser and `backend_status()` says which one ran. The fallback
handles all demo phrasings, including the `now_block` anchoring that makes
"tripped, back by 21:00" a 7-hour outage rather than a 21-hour one.

**Why an LLM here and nowhere else?** Because this is the one place where the
bottleneck is unstructured natural language. Using it to pick setpoints would be
worse than a MILP at the job and unexplainable. Using it to read an SOP is the
job it is actually best at.

## 5.6 What the models are *worth* — the honest hierarchy

State this before anyone asks "isn't this just a forecasting project?":

| Component | Worth |
|---|---|
| Constraint model + twin | the product |
| Landed-cost engine | changes the *answer* (§8.4) |
| Optimizer | necessary, but a solved problem |
| **Forecast** | **8% of the value** (§8.2) |

In a five-lever ranking on this same data, exchange timing came **last** at
₹0.13/kWh realistic against ₹0.31 with perfect foresight, while load shifting
came first by roughly an order of magnitude. **A better forecast is worth paise;
a better constraint model is worth rupees.**

---

# §6 · THE DATA LAYER

## 6.1 What is used

| Dataset | Source | Size | Role |
|---|---|---|---|
| IEX RTM / DAM / G-DAM, Maharashtra W2 | IEX, 15-min settlement | **152,542 blocks**, 1,588 complete days, 2022-04-01 → 2026-08-06 | prices, forecast target, DSM reference |
| WRPC deviation settlement | WRPC | 133,056 blocks (thesis) | established DSM rate = max(DAM, RTM) |
| MERC tariff orders | primary PDFs | — | landed-cost stack (**placeholders pending verification**) |
| Plant historian | OPC-UA / PI / IP.21 | per site | twin fitting (not yet done for a real plant) |

## 6.2 Two data traps that would have silently corrupted everything

**Trap 1 — the price cap is not constant.** Derived empirically from the panel,
not assumed:

| Period | Cap |
|---|---|
| 2022-04-01 → 2022-04-30 | ₹20,000/MWh |
| 2022-05-01 → 2023-03-31 | ₹12,000/MWh |
| 2023-04-01 → present | ₹10,000/MWh |

Clipping the whole panel at the current ₹10,000 cap would silently rewrite
**5,372 real RTM blocks**, and a model trained straight across the boundary is
learning across a regime break rather than a market. The forecaster trains on the
current regime for exactly this reason.

**Trap 2 — inherited from the thesis, worth repeating.** In the WRPC deviation
files the **sign convention flips between files** (not along schema or date
lines), and the rate column is **₹/MWh in one schema but paise/kWh in two
others** — a factor-of-ten step. Both corrupt silently. The general lesson, and
it is the one to say: *check a file's own arithmetic before trusting it.*

## 6.3 Real-data-only discipline

Nothing in this project is synthetic except the twin parameters, which are
indicative values in published ranges and are labelled as such everywhere. No
prices are simulated. No savings are projected from assumption — every rupee
figure is a replay of a real settled day.

---

# §7 · ARCHITECTURE AND CODE MAP

```
┌─ 1 · INGESTION ──────────────────────────────────────────────────────┐
│ IEX DAM/RTM/G-DAM 15-min · deviation settlement · SERC orders        │
│ plant historian (OPC-UA) · weather · production plan                 │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 2 · TWIN ───────────────────▼───────────────────────────────────────┐
│ P(x) convex · SEC U-shaped · inventory ODE · ramp · min up/down       │
│ ⇒ φ(ΔMW, Δt) — the flexibility cost curve                             │
│ 16 tangent hyperplanes, linearization error < 0.7%                    │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 3 · FORECAST ───────────────▼───────────────────────────────────────┐
│ LightGBM quantile q10/q50/q90 + out-of-sample conformal widening      │
│ lead feature: same-block day-ahead price (known 12–36 h ahead)        │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 4 · DECISION ───────────────▼───────────────────────────────────────┐
│ min (1−λ)E[cost] + λCVaR₉₅ + starts + bought-in + demand charge       │
│ 1,757 vars (384 binary) · 8,646 constraints · CBC · 0.3–13 s          │
│ deviation offered and provably never used                             │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 5 · AGENT & OUTPUT ─────────▼───────────────────────────────────────┐
│ elicit / explain / perturb · structured outputs · sign-off gated      │
│ Streamlit console · REST API · OPC-UA setpoint write (L2+)            │
└──────────────────────────────────────────────────────────────────────┘
```

## Code map

| File | Lines | What it owns |
|---|---|---|
| `prana/config.py` | 98 | Paths, market constants, tariff params — **every placeholder tagged** |
| `prana/data.py` | ~200 | Panel cache, DSM rate, price-cap regimes |
| `prana/tariff.py` | 121 | Landed cost, demand charge, ratchet, bill decomposition |
| `prana/twins.py` | ~360 | 4 archetypes, φ, tangents, virtual-battery equivalence |
| `prana/forecast.py` | 266 | Quantile GBM, conformal calibration, 3 baselines |
| `prana/optimizer.py` | ~425 | The MILP, `Schedule`, `Constraint`, binding-constraint derivation |
| `prana/agent.py` | ~400 | Elicitation, explanation, perturbation, rule fallback |
| `prana/backtest.py` | ~300 | Replay, alt-supply charge-back, **independent physics verification** |
| `app.py` | ~380 | 5-tab console |
| `run_demo.py` | ~195 | Terminal demo — venue insurance |
| `tests/test_prana.py` | ~300 | **31 tests**, each pinning a claim |

~3,000 lines of Python. Dependencies: pandas, numpy, pulp (CBC), lightgbm,
scikit-learn, streamlit, plotly. Optional: an LLM provider SDK.

## The trust ladder — say this before a PSU judge asks

**L1 Advisory** — read-only, shadow mode, 4–8 weeks, prove savings against
actuals. **L2 Supervised** — one-click accept, OPC-UA write, every DCS interlock
retains absolute veto. **L3 Bounded closed loop** — autonomous only inside a
pre-approved envelope, automatic reversion on twin/actual divergence.

PRANA's feasible set is always a **strict subset** of the plant's licensed
operating envelope. No interlock is ever bypassed.

---

# §8 · RESULTS — EVERY NUMBER AND ITS PROVENANCE

## 8.1 The headline replay

120 consecutive delivery days (2026-04-09 → 2026-08-06), settled at **realised**
prices, savings **net of bought-in hydrogen**, every schedule independently
verified against true nonlinear physics.

| Site | Mode | Mean/day | Per kWh of load | % of bill | Annualised | Days worse | Violations |
|---|---|---|---|---|---|---|---|
| **Refinery** | **forecast (realistic)** | **₹5.80 L** | **₹0.260** | 2.90% | ₹21.2 cr | **0** | **0** |
| Refinery | perfect foresight | ₹6.29 L | ₹0.282 | 3.14% | ₹23.0 cr | 0 | 0 |
| **Fertilizer** | **forecast (realistic)** | **₹0.93 L** | **₹0.085** | 0.98% | ₹3.4 cr | 5 | **0** |

Distribution, refinery/forecast: median ₹6.64 L, p10 ₹2.51 L, p90 ₹7.89 L, worst
day ₹1.16 L, best ₹8.27 L. **Correlation of daily saving with intraday spread:
0.651** — the value tracks the price shape, exactly as the thesis predicts.

**Quote the realistic refinery row.** Perfect foresight is the upper bound.

**Be honest about the fertilizer row.** It is smaller (₹0.085 vs ₹0.260/kWh) and
it has **5 days worse than steady state**. That is real: with a 3%/h ramp you
must commit early, and with forecast error you are sometimes wrong. A slow asset
is a worse flexibility asset — which is itself a finding, and is why the pitch
leads with the refinery.

## 8.2 The forecast-error haircut

₹0.282 → ₹0.260 per kWh. **The haircut is 8%.**

This is the single best answer to "isn't this just a forecasting project?" —
perfect knowledge of tomorrow's prices is worth only 8% more than a decent
forecast, because the value lives in the constraint model.

## 8.3 Deviation: a negative, proved

The optimizer is *given* a deliberate-deviation decision variable in every solve.
Result: **`max_deviation_mw = 0.000000` in every solve**, across 6 dates, both
forecast modes, and all 363 site-days replayed.

Why: the published DSM rate ≈ max(DAM, RTM) for the same block — audited on
133,056 WRPC blocks, correlation 0.955–0.971, slope ≈ 1.0, peaking at zero lag —
so it is ≥ the real-time price in 99.9% of blocks. Deviation arbitrage is
impossible **by regulatory design**.

**Presentation value:** most teams will not know this. You do not just assert it —
your optimizer demonstrates it live.

## 8.4 The demand-charge result — the most important finding

Same plant, same day, same optimizer. Only the demand charge changes:

| Demand charge | Peak | Electrolyser | Interpretation |
|---|---|---|---|
| ₹590/kVA/month | 94.6 MW | 1 of 96 blocks | reality |
| **₹0** | **110.0 MW** | **20 of 96 blocks** | what MCP-only tools assume |
| ₹590, contract demand 125 MW | 94.6 MW | 1 of 96 blocks | **raising the cap changes nothing** |

The demand charge is worth **₹20,068 per MW of peak per day.** Marginal green
hydrogen looks profitable in 21 of 96 blocks on energy price alone — and is not,
once the peak it creates is priced.

**Third row matters:** it proves the mechanism is the *charge*, not the *cap*. It
kills the obvious objection before it is made.

## 8.5 A subtlety worth knowing before someone finds it

Across the backtest, PRANA's **demand-charge cost is ₹25,195/day *higher*** than
steady state. It deliberately buys peak to capture energy spread, and the trade
nets strongly positive. If asked "doesn't your optimizer raise the peak?" — yes,
sometimes, knowingly, and it prices the trade. That is the point of modelling the
term rather than assuming it away.

## 8.6 Forecast performance

Held-out: 12,287 blocks from 2026-04-01. Trained through 2026-03-31.

| Model | MAE ₹/MWh | Pinball q50 |
|---|---|---|
| **PRANA LightGBM** | **1,072** | **536** |
| Naive persistence (same block yesterday) | 1,189 | 595 |
| DAM as forecast | 1,271 | 635 |
| 7-day block mean | 1,538 | 769 |

Pinball q10/q50/q90 = 286.6 / 536.2 / 195.4. RMSE 1,688. Coverage 76.2% after
×1.20 conformal widening.

## 8.7 Verification

`verify_schedule()` is **independent of the optimizer**. It recomputes power from
the exact convex curve (not the tangent envelope), re-integrates inventory block
by block, and checks min/max load, ramp, buffer floor and ceiling, terminal
inventory, contract demand and deviation.

**Across all 363 site-days replayed: 0 violations.** That is why the claim means something.

## 8.8 Test suite

**31 tests, 0 failures.** Each pins a claim: power curves convex and increasing;
SEC U-shaped; tangents never overstate power; linearization < 1%; φ positive and
monotone; ammonia un-trippable and slow; pipeline ≥ 5× electrolyser; DSM ≥ RTM in
>99.9% of real blocks; deviation never used; schedule survives true physics;
PRANA beats steady state net of bought-in product; **zeroing the demand charge
must raise the peak**; agent extracts wrapped SOP text, anchors "tripped" to now,
flags ambiguity, requires sign-off; source contains no control characters.

---

# §9 · IMPACT — HOW MUCH CHANGES, AT THREE SCALES

## Scale 1 — one site

| Metric | Refinery (105 MW nameplate) | Fertilizer (46 MW nameplate) |
|---|---|---|
| Saving per kWh of total load | ₹0.260 | ₹0.085 |
| Annualised | ₹21.2 crore | ₹3.4 crore |
| Virtual battery | 28 MW / 294 MWh | 7.9 MW / 284 MWh |
| Equivalent BESS capex displaced | ₹323 crore | ₹312 crore |
| Capex required | **zero** | **zero** |
| Character | 28 MW shallow-and-fast | 7.9 MW **deep-and-slow** (ammonia alone is 62.7 h) |
| Production impact | **none** — product output unchanged by construction | same |

**On the demo day (12 July 2026, a real day):** RTM ₹1/MWh at 13:00 → ₹10,000/MWh
at midnight. Avoided **₹5.98 lakh in a single day**, 3.46% of that day's bill,
with zero violations.

## Scale 2 — Oil India

Three deployment paths, in increasing order of difficulty:

1. **Pipeline pumping stations** — the cleanest archetype in the country. Tankage
   at both ends, a schedulable pump, no product-quality risk beyond batch
   interfaces. Start here.
2. **NRL utilities block** — ASU, hydrogen and cooling through the 3→9 MMTPA
   expansion. Highest ₹ value.
3. **Green hydrogen programme (Jorhat / NRL)** — where the price-duration
   analysis says the LCOH minimum sits near 6,000 operating hours, not 8,000. If
   DPRs are being written at ~90% CUF, they are mis-sizing the plant. This is an
   actionable correction to a live decision, not a research finding.

## Scale 3 — national (clearly labelled as an estimate)

**Do not present this as measured.** State the assumptions out loud.

- Indian industrial + commercial consumption: order of **700 billion units/year**
- Assume 15% sits in buffer-bearing processes → ~105 BU
- Assume 20% of that is genuinely shiftable → ~21 BU moved per year
- At an observed intraday spread of ~₹5/kWh → **gross value pool in the low
  tens of thousands of crores per year**
- A platform take of 10–20% → **revenue pool in the low thousands of crores**

**System-level, non-financial:** this is dispatchable demand appearing exactly
where the grid is breaking — absorbing curtailed midday solar and vacating the
evening ramp. The plant is paid to provide a public good.

## Business model

| Line | Detail |
|---|---|
| SaaS | ₹25–60 lakh per site per year, tiered by connected MW |
| Gainshare | 15–20% of verified savings on an IPMVP Option C regression baseline — opex-neutral, which PSUs prefer |
| Aggregation | 10–15% take rate once a flexibility market opens; we already hold the constraint models, which is the hard part of being a VPP |
| Data product | The capture-rate / flexibility index — the Modo Energy / Pexapark model, unbuilt for India |

**Moat — three things, none of them the optimizer:**
1. The **process constraint library**: every archetype commissioned makes the
   next deployment in that industry faster. Onboarding cost is the entire barrier.
2. The **regulatory cost engine**: months of primary SERC-order work, where
   trade-press summaries are demonstrably wrong.
3. **Negative knowledge**: the deviation finding, the sign-convention trap, the
   unit-scale trap, the price-cap regime break. A lab rebuilds the MILP in a
   fortnight. It cannot rebuild two years of being wrong.

---

# §10 · BUGS FOUND DURING THE BUILD

Include these if a technical judge goes deep. They demonstrate the model was
actually interrogated, not just run.

**10.1 Deviation priced as bare energy.** The DSM charge was applied without the
regulatory stack, handing deviation a fake ~₹2.7/kWh discount. The optimizer
immediately routed 100% of plant load through it. *Fix:* deviation carries the
same landed stack as scheduled drawal.

**10.2 CVaR added instead of blended.** `E + λ·CVaR` silently scaled the energy
term by 1.35× against the demand-charge, start-cost and make-vs-buy terms,
distorting every trade-off. *Fix:* the convex combination `(1−λ)E + λ·CVaR`,
which collapses exactly onto the deterministic cost when scenarios are identical.

**10.3 DSM rate fixed at the median across a price fan.** Costs were evaluated
across three scenarios but the deviation rate used only the median, so deviating
looked cheap in the high-price scenario. *Fix:* compute the rate **per scenario**.
This is why "deviation is never used" now holds under forecast error too.

**10.4 Bought-in hydrogen not charged back.** PRANA could idle the electrolyser,
book a large electricity saving, and never pay for the SMR gas that replaced the
hydrogen. **This inflated the headline by ~28%.** *Fix:* the saving is net of
alternative supply, on both sides of the comparison.

**10.5 Sell-back arbitrage loop.** Sell-back was credited at the grossed-up
landed rate, making buy-then-sell free money and the model unbounded. *Fix:*
credit at the market price **net** of losses, and cap sell-back at the day-ahead
position.

**10.6 Flat baseline infeasible.** Pinning assets at nameplate could not hold
inventory against boil-off. *Fix:* the baseline is a *constant* setpoint chosen
to hold inventory — which is also a more honest counterfactual.

**10.7 A regex `\b` became a literal backspace byte** through a shell heredoc,
silently disabling a word boundary and mis-parsing operator utterances. *Fix:*
repaired, plus a test that scans all source for control characters.

**The meta-point, and it is worth saying:** every one of these made the numbers
*better* before it was found. A model that is not adversarially tested reports
whatever its bugs allow.

---

# §11 · LIMITATIONS AND WHAT IS NOT YET TRUE

State these before a judge finds them. It converts a weakness into evidence of
rigour.

1. **Every regulatory figure is a placeholder** pending verification against the
   MERC MYT order. All are tagged in `prana/config.py`. The *architecture* of the
   landed-cost engine is the contribution; the specific rupees are not audited.
   The additional-surcharge parse in particular flips the sign of the open-access
   case and is explicitly unverified.
2. **The twins are archetypes.** Parameters are in published ranges but not
   fitted to any specific plant's historian. Commissioning means fitting them to
   real data.
3. **FY2026-27 is April–August only** and seasonally biased upward. Label it
   everywhere.
4. **The 80% forecast interval covers 76.2%.** The CVaR term is therefore mildly
   optimistic. Reported, not tuned away.
5. **Single-site.** The aggregation/VPP layer is designed, not built.
6. **CO₂ figures are estimates** from a peak-vs-solar grid emission-factor
   difference. Cite the CEA CO₂ Baseline Database and label them.
7. **The fertilizer site has 5 loss-making days out of 120** under forecast
   error. Slow assets are worse flexibility assets.
8. **No real plant data has been used.** Everything is market-side real and
   plant-side indicative.

## A correction to carry forward from the earlier project

The prior submission's BESS NPV sensitivity swept capex at **₹2.5–5.5 crore per
MWh** and concluded negative NPV in all 63 cells. Indian utility-scale BESS is
currently around **₹1.0–1.2 crore per MWh installed** — the sweep is 3–4× high.
Re-running at ₹1.0 crore/MWh with the same ₹42,000 crore annual benefit and
15-year life moves NPV from about **−₹8.8 lakh crore to roughly +₹19,000 crore.
The sign flips.**

**Do not reuse that heatmap unfixed.** Fixing it strengthens PRANA: storage
economics are better than that chart implies, *and* the free storage inside the
fence should still be dispatched first.

---

# §12 · HOW TO PRESENT IT

## The narrative arc — five moves

1. **A number they cannot argue with.** The price ratio going 1.47 → 3.53 on real
   settlement data. Not a projection.
2. **The consensus, and what it misses.** Everyone says build batteries. This
   refinery already owns 294 MWh — it is just full of liquid oxygen.
3. **Why nobody has used it.** Not because optimization is hard. Because nobody
   can write down the constraints. *"I spent two years in an ammonia–urea plant.
   I know exactly where those constraints live."*
4. **The thing you built.** The flexibility cost curve, the landed-cost engine,
   the agent. Show the demand-charge slider.
5. **Proof and safety.** 120 days, zero bad days, zero violations, and the trust
   ladder.

## Slide-by-slide (10 slides)

| # | Slide | The one thing it must land |
|---|---|---|
| 1 | Title + one line | "India's biggest battery is already built. It's made of molecules." |
| 2 | The price shape breaking | 1.47 → 3.53, real settled data |
| 3 | The consensus vs the insight | 411 GWh to build vs 294 MWh already there |
| 4 | Why nobody dispatches it | The constraint problem — your plant credentials |
| 5 | **The flexibility cost curve** | The novel object. Pipeline 10× electrolyser = cube law |
| 6 | Architecture | Twin → forecast → MILP → agent, one diagram |
| 7 | **The demand-charge kill shot** | 1 block vs 20 blocks. Everyone else is wrong |
| 8 | 120-day replay | ₹0.260/kWh, 0 bad days, 0 violations |
| 9 | Oil India deployment | Pipelines → NRL utilities → Jorhat H₂ |
| 10 | Ask | One site, 90 days, advisory mode |

## Live demo — 5 minutes, rehearsed six times

| Time | Beat |
|---|---|
| 0:00 | Price-shape chart. *"Settled money, not a forecast."* |
| 0:40 | The LOX tank photo. *"294 MWh, already built."* |
| 1:20 | **Tab 2** — the flexibility cost curve. Point at the pipeline line 10× above. |
| 2:00 | **Tab 1** — live solve on 12 July 2026. ₹1/MWh at 13:00 → ₹10,000 at midnight. |
| 2:50 | **The kill shot.** Drag the demand-charge slider to zero. Electrolyser jumps 1 → 20 blocks. |
| 3:30 | **Tab 3** — hand a judge the keyboard: *"Compressor B tripped, back by 21:00."* Then show the two sentences it **refused** to encode. |
| 4:20 | **Tab 4** — 120 days, violations: 0. Then the DSM slide: *"the strategy we deliberately did NOT build."* |
| 4:50 | **Tab 5** — board view, Oil India deployment map. |

**Highest-variance moment:** handing a judge the keyboard. Rehearse it. It is
also the highest-payoff — the moment a judge participates, you have the room.

**If Streamlit will not start:** `python run_demo.py` prints every number in
pitch order. Test it on the venue laptop before you present.

## Five sentences to memorise verbatim

1. *"The state of charge is inventory, not electrons."*
2. *"The optimizer was never the hard part. Getting the constraints out of the
   plant is."*
3. *"You cannot machine-learn your way to operating points the plant has never
   visited — and that is exactly where flexibility lives."*
4. *"We gave the optimizer the deviation lever and it declines to use it, every
   single solve."*
5. *"A better forecast is worth paise. A better constraint model is worth
   rupees."*

---

# §13 · Q&A BANK

**"Isn't this just demand response? That failed in India for a decade."**
Agreed, and the usual diagnosis is wrong. DR is blamed on the absence of a market
mechanism. The real blocker is that plants cannot quantify their own flexibility,
so they cannot price the production risk, so they refuse. We attack that with the
twin and the agent. And we do not wait for a DR market — we monetise through
exchange exposure, ToD tariff and demand-charge management, all live today.

**"Why not just install a battery?"** A 28 MW / 294 MWh system is roughly ₹320
crore. On this panel a 4-hour merchant battery earns ₹61–85 lakh/MW-yr against an
annualised capital cost in the same range — merchant arbitrage alone barely
covers it. The virtual battery has zero capex. They are complements: use the free
storage first, then size the lithium for what is left.

**"What about DSM arbitrage?"** The trap, and the question I most want. Audited
133,056 blocks: the published rate ≈ max(DAM, RTM), so it is ≥ RTM in 99.9% of
blocks. Deviation arbitrage is impossible by regulatory design. We gave our
optimizer the lever anyway; it never uses it. That is on the Backtest tab.

**"How accurate is the forecast? Isn't that the product?"** It isn't. Perfect
foresight is worth only 8% more than our forecast — ₹0.282 vs ₹0.260 per kWh. We
beat naive persistence, DAM-as-forecast and a 7-day block mean, and report
pinball loss against all three, but I would rather be judged on whether the twin
is right.

**"Your savings look large. What's the counterfactual?"** One steady setpoint per
asset, held all day, chosen to hold inventory — how these plants are actually
run. And the saving is net of bought-in product: when we idle the electrolyser
and buy SMR hydrogen, we charge ourselves for the gas. Without that correction
the headline was 28% higher and would have been wrong.

**"Doesn't your optimizer raise the peak demand?"** Yes — by about ₹25,000/day of
extra demand charge on average, knowingly, because the energy saving is larger.
The point of modelling the term is to price that trade rather than assume it away.

**"How do you get plant data? A PSU won't open its DCS."** And it shouldn't, on
day one. L1 is advisory and read-only over a one-way gateway or a nightly
historian export — the same access an energy auditor gets. Shadow mode for 4–8
weeks, prove savings against actuals, then discuss a write path. Minimum viable
dataset: an energy meter, a tank level, and a production log.

**"What if the LLM hallucinates a constraint?"** It cannot reach the optimizer —
every extraction requires human sign-off. And explanations are generated from the
solver's active bounds, not the model; the LLM is never asked to produce a
reason, only to phrase one. Given an ambiguous sentence it returns nothing and
flags it.

**"Why MILP and not RL?"** No simulator of sufficient fidelity to train against;
no safety guarantee, and a PSU will not accept an unexplainable setpoint; and
MILP gives duals — the shadow price of every plant rule, which is itself a
product.

**"What's your moat? An IIT lab could build this."** The constraint library that
compounds per deployment, the regulatory cost engine that takes months of primary
documents, and negative knowledge that cost me two years. A lab rebuilds the MILP
in a fortnight; it cannot rebuild being wrong for two years.

**"Is any of this validated on a real plant?"** No, and I will not claim
otherwise. The market side is entirely real — 152,542 settled blocks. The plant
side is archetypes with parameters in published ranges. Commissioning means
fitting the twin to a historian, which is 4–8 weeks of shadow mode. What is
proven today is the *method*, and that it produces schedules which survive
independent physics verification.

**"What would make you wrong?"** Three things. If intraday spreads collapse —
they are widening. If plants turn out to have far less buffer than published
ranges suggest — the twin is fitted per site, so we would find out in
commissioning, cheaply. And if the additional-surcharge waiver reverses, open
access gets worse and the DISCOM route dominates — which the engine already
models, so the answer changes but the tool does not.

---

# §14 · GLOSSARY

| Term | Meaning |
|---|---|
| **Block** | A 15-minute settlement interval. 96 per day. |
| **MCP** | Market clearing price — the exchange price. ~60% of what you pay. |
| **Landed cost** | ₹/kWh at your meter, including all charges and duty. |
| **DAM / RTM** | Day-ahead market (closes 12–36 h before) / real-time market. |
| **G-DAM** | Green day-ahead market — renewable-attributed power. |
| **DSM** | Deviation settlement mechanism — the price for drawing off-schedule. |
| **Demand charge** | Monthly charge on **peak kVA**, not energy. With a ratchet. |
| **Ratchet** | Billing demand cannot fall below a % of contract demand. |
| **ToD** | Time-of-day tariff multiplier. |
| **CSS / AS** | Cross-subsidy surcharge / additional surcharge — open-access charges. |
| **Open access** | Buying power from the exchange rather than the DISCOM. |
| **SEC** | Specific energy consumption — kWh per unit of product. |
| **Turndown** | Minimum stable load, as % of design. |
| **CUF / PLF** | Capacity utilisation / plant load factor. |
| **LCOH** | Levelised cost of hydrogen, ₹/kg. |
| **SMR** | Steam methane reforming — the conventional (grey) hydrogen route. |
| **ASU** | Air separation unit — makes O₂/N₂, often stored as cryogenic liquid. |
| **BESS** | Battery energy storage system. |
| **MILP** | Mixed-integer linear program. |
| **CVaR** | Conditional value at risk — expected cost in the worst α% of cases. |
| **Pinball loss** | The scoring rule for quantile forecasts. |
| **Conformal calibration** | Post-hoc widening so an interval covers what it claims. |
| **Tangent hyperplane** | A linear lower bound; the max of several approximates a convex curve. |
| **Duals / shadow price** | What relaxing a constraint by one unit is worth. |
| **OPC-UA** | The industrial protocol for reading/writing DCS data. |
| **DCS** | Distributed control system — the plant's control layer. |
| **Interlock** | A hard safety rule in the DCS. Never bypassed. |
| **P&ID** | Piping and instrumentation diagram. |
| **HAZOP** | Hazard and operability study. |
| **IPMVP** | The standard for measuring and verifying energy savings. |
| **VPP** | Virtual power plant — an aggregation of distributed flexibility. |
