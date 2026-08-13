# PRANA — The Molecular Battery Platform

**Process Response & Adaptive Network Agent**
Platinum Jubilee Innovation Hackathon · MC²⁺ · Oil India Limited · IIT Kharagpur
**Track 4 — Digital Asset Management (AI/ML, Digital Twin, Robotics, Corrosion)**

> India's largest grid-scale battery is already built and paid for. It is made of
> molecules — cryogenic liquid, hydrogen, crude in tankage, clinker — and nobody
> is dispatching it.

PRANA converts an industrial process buffer into a dispatchable virtual battery
by deriving its **marginal flexibility cost curve** from process physics, then
trading that curve against the forecast **landed** cost of electricity under an
agent that never proposes a schedule the plant's own interlocks would reject.

- 📕 **[PRANA_MASTER_BRIEF.md](PRANA_MASTER_BRIEF.md)** — **read this one.** The whole project start to end: the physics, every model and why that model, every number and its provenance, impact at three scales, the bugs found, limitations, how to present it, Q&A bank, glossary.
- 📄 **[PRANA_SUBMISSION.md](PRANA_SUBMISSION.md)** — the form-ready submission pack (title, track, 430-word executive summary, architecture, MVP, demo script)
- 📘 **[PRANA_PLAYBOOK.md](PRANA_PLAYBOOK.md)** — earlier strategy document: gap analysis, alternatives considered, long-form pitch scripts

---


## PRANA as a platform

PRANA is **Industrial Flexibility Intelligence**: it answers *how much electrical
flexibility can this process safely and economically use right now* — and it is
built to be able to answer **DO NOTHING**.

Production first. Safety first. Constraints first. Economics second.

| Layer | Module | Knows what the process is? |
|---|---|---|
| Process interface | `prana/process.py` | defines the boundary |
| Process physics | `prana/twins.py` (validated), `prana/generic.py` (illustrative) | **yes** |
| Market / landed cost | `prana/tariff.py`, `prana/data.py` | no |
| Optimiser | `prana/optimizer.py` | no — asserted by a test |
| Decision engine | `prana/decision.py` | no |
| Scenarios | `prana/scenarios.py` | no |

A conforming process answers nine questions (`get_operating_envelope`,
`get_power_curve`, `get_production_constraints`, `get_inventory_state`,
`get_ramp_limits`, `get_recovery_constraints`, `calculate_flexibility_cost`,
`validate_schedule`, `get_binding_constraints`). The optimiser accepts anything
that does, and `test_optimizer_is_process_agnostic` fails if the optimiser ever
learns what the process makes.

**Data status travels with every number:** `VALIDATED` (chlor-alkali only),
`ILLUSTRATIVE` (generic process — requires plant calibration), or
`USER_CONFIGURED`. No savings figure is shown for an uncalibrated archetype.

### Run it

```bash
python -m pytest tests -q                  # 64 tests
python -m prana.scenarios                  # SHIFT / DO NOTHING / DO NOTHING
python run_demo.py --site chloralkali      # validated case study, 22 s
streamlit run app.py                       # full console
```

`PRANA_APP.html` is the browser demo — double-click it, no install, works offline.
Its decision logic is a port of `prana/decision.py` and is checked against the
Python engine on all three scenarios.

## Quick start

```bash
pip install -r requirements.txt
python -m prana.data --build        # cache the IEX panel (one-time)
python -m prana.forecast --train    # train + evaluate the quantile forecaster
python tests/test_prana.py          # 45 regression tests
python run_demo.py                  # every headline number, no Streamlit needed
streamlit run app.py                # the console
```

`prana/data.py` reads the IEX CSVs from the thesis project by default. Point it
elsewhere with `PRANA_IEX_DIR`. The cached panel is self-contained after the
first build.

Optional: set an LLM provider API key to run the constraint agent. Without
it the agent falls back to a deterministic parser and says so — it never
silently degrades.

---

## What's here

| Module | Responsibility |
|---|---|
| `prana/config.py` | Paths, market constants, tariff parameters — **every regulatory placeholder is tagged in the source** |
| `prana/data.py` | 152,542-block IEX panel; DSM rate = max(DAM, RTM); empirical price-cap regimes |
| `prana/tariff.py` | Landed-cost engine: MCP → ₹/kWh at the meter, plus demand charge with ratchet |
| `prana/twins.py` | Three process archetypes; φ(ΔMW, Δt); tangent linearization with error bound |
| `prana/forecast.py` | LightGBM quantile forecast + out-of-sample conformal calibration + 3 baselines |
| `prana/optimizer.py` | 96-block stochastic MILP with CVaR₉₅, solved by CBC |
| `prana/agent.py` | Constraint elicitation, explanation, live perturbation |
| `prana/backtest.py` | Replay + **independent verification against the true nonlinear physics** |
| `app.py` | Five-tab Streamlit console |
| `tests/` | **45 tests**, each pinning a claim made in the submission |

---

## Verified results

All computed by this code on real settlement data.

| Check | Result |
|---|---|
| Market panel | 152,542 blocks · 1,588 complete days · 2022-04-01 → 2026-08-06 |
| Intraday price ratio (evening ÷ solar) | 1.47 (FY22-23) → 2.23 (FY25-26) → 3.53 (FY26-27, Apr–Aug) |
| Tangent linearization error | ASU 0.005% · electrolyser 0.023% · pipeline 0.622% |
| Flexibility cost curve φ | electrolyser ₹7–37 · ASU ₹15–54 · pipeline ₹175–665 per MWh shifted |
| Forecast MAE | **1,072** vs naive 1,189 · DAM 1,271 · 7-day block mean 1,538 ₹/MWh |
| Interval coverage | 69.7% raw → **76.2%** after conformal widening (target 80%) |
| **120-day replay, chlor-alkali, forecast error** (the headline) | **₹0.133/kWh of total plant load** · ₹9.17 cr/yr · 13 days worse than steady state · net of membrane wear, Cl2 dumped and kVAh droop |
| 120-day replay, refinery, with forecast error | ₹0.260/kWh, 0 days worse (pre-pivot site, no co-product coupling) |
| 120-day replay, ammonia–urea, with forecast error | ₹0.085/kWh, 5 days worse (slow assets are worse flexibility assets) |
| Archetypes implemented | **chlor-alkali cell house** · ASU · electrolyser · pipeline · ammonia synthesis loop |
| Deliverable virtual battery, chlor-alkali | **21.8 MW / 748 MWh** at the 70% chlorine-consumer floor (not the 40% cell interlock) |
| Deviation used | **0 MW**, every solve |
| Constraint violations vs true physics | **0** |

### The result worth arguing about

Same plant, same day, same optimizer. The only change is whether the demand
charge is modelled:

| Demand charge | Peak | Electrolyser |
|---|---|---|
| ₹590/kVA/month (reality) | 94.6 MW | runs **1 of 96 blocks** |
| ₹0 — what an MCP-only tool assumes | 110.0 MW | runs **20 of 96 blocks** |

An optimizer that prices energy at the exchange clearing price tells this
refinery to run its electrolyser twenty blocks a day. With the real tariff in
front of it, that is the wrong answer — and raising contract demand doesn't fix
it, because it is the charge, not the cap.

---

## Design decisions worth knowing

**Explanations come from the solver, not the model.** `Schedule.binding` is
derived from active bounds in the solution. The LLM phrases those facts; it is
never asked to produce a reason, so it cannot invent one.

**The optimizer is allowed to cheat and doesn't.** Deliberate deviation from
schedule is offered as a decision variable in every solve. Because the published
DSM rate is approximately max(DAM, RTM) — audited on 133,056 WRPC blocks — it is
never chosen. `max_deviation_mw == 0` ships with every schedule as evidence.

**The counterfactual is honest.** The baseline is one steady setpoint per asset,
held all day, chosen to hold inventory — how these plants are actually run. And
savings are **net of bought-in product**: when PRANA idles the electrolyser and
buys SMR hydrogen, it is charged for the gas.

**Verification is independent of the optimizer.** The MILP works with tangent
hyperplanes; `verify_schedule()` recomputes power from the exact convex curve,
re-integrates inventory block by block, and checks every bound. A schedule that
only satisfies the linearization is reported as a violation.

---

## Limitations — read before quoting any number

1. **Every regulatory figure is a placeholder** pending verification against the
   MERC MYT order; all are tagged in `prana/config.py`. The architecture of the
   landed-cost engine is the contribution — the specific rupees are not yet
   audited. The additional-surcharge parse flips the sign of the open-access
   case and is explicitly unverified.
2. **The twins are archetypes**, with parameters in published ranges but not
   fitted to any specific plant's historian.
3. **FY2026-27 is April–August only** and is seasonally biased upward. Label it
   on every chart.
4. **The 80% forecast interval covers 76.2%**, so the CVaR term is mildly
   optimistic. Reported, not tuned away.
5. **Single-site.** The aggregation/VPP layer is designed, not built.
6. **CO₂ figures are estimates** from a peak-vs-solar grid emission-factor
   difference — cite the CEA CO₂ Baseline Database and label them as estimates.
