# PRANA — Industrial Flexibility Intelligence

**How much electrical flexibility can an industrial process safely and
economically use right now?**

Production first. Safety first. Constraints first. Economics second. PRANA is a
decision-support layer — it does not control plant equipment, and it is built to
be able to answer **DO NOTHING**.

*Platinum Jubilee Innovation Hackathon · MC²⁺ · Oil India Limited · IIT Kharagpur*
*Track: Digital Asset Management (AI/ML, SCADA, Digital Twin)*

---

## Run it

```bash
pip install -r requirements.txt

python -m pytest tests -q            # 64 regression tests
python -m prana.scenarios            # SHIFT / DO NOTHING / DO NOTHING
python run_demo.py --site chloralkali   # the validated case study, ~22 s
streamlit run app.py                 # full console
```

The market panel and the fitted forecaster ship with the repository, so a fresh
clone reproduces the headline with no external dependency. `PRANA_APP.html` is a
self-contained browser demo — open it directly, no install, works offline.

---

## What it does

Electricity in India is no longer a flat-cost input. On four years of settled
15-minute prices, the evening now costs several times what midday costs. But a
plant cannot simply follow the price: it answers to safety, production, quality,
inventory, ramp rate, equipment limits and whoever is downstream waiting for
product. Electricity cost ranks below every one of those.

PRANA is the layer between the two. It quantifies what moving load would cost
*this* process — **φ(ΔMW, Δt)**, in ₹ per MWh shifted — and compares that against
what the market would pay, at the price the plant actually pays at its meter.

---

## Architecture

The optimiser does not know what the process makes. A test fails if it ever
learns.

| Layer | Module | Process-aware? |
|---|---|---|
| Process interface | `prana/process.py` | defines the boundary |
| Process physics | `prana/twins.py` · `prana/generic.py` | **yes** |
| Market / landed cost | `prana/tariff.py` · `prana/data.py` | no |
| Forecast | `prana/forecast.py` | no |
| Optimiser | `prana/optimizer.py` | no — asserted by a test |
| Decision engine | `prana/decision.py` | no |
| Verification | `prana/backtest.py` | re-simulates true physics |

A conforming process answers nine questions: `get_operating_envelope`,
`get_power_curve`, `get_production_constraints`, `get_inventory_state`,
`get_ramp_limits`, `get_recovery_constraints`, `calculate_flexibility_cost`,
`validate_schedule`, `get_binding_constraints`.

**Decision order — hard gates before economics, always:**

1. hard constraint active → **DO NOTHING**
2. flexibility physically unavailable → **DO NOTHING**
3. net benefit ≤ 0 → **DO NOTHING**
4. otherwise → **SHIFT**

A high price is never on its own sufficient. It enters only at step 3.

---

## Data status

Every number carries one, and it travels with the number:

| Status | Meaning |
|---|---|
| **VALIDATED** | Chlor-alkali only. Backtested on real settled prices, physics grounded in a published source, every schedule independently re-verified. |
| **ILLUSTRATIVE** | The generic process. Mechanism real, parameters are not a specific plant. Requires calibration before any rupee figure means anything. |
| **USER CONFIGURED** | Entered at runtime. |

**No savings figure is claimed for any uncalibrated archetype.**

---

## Evidence

| | |
|---|---|
| Market panel | 152,542 settled IEX blocks · 1,588 complete days · Maharashtra W2 · Apr 2022 – Aug 2026 |
| Tariff | MERC Case 75 of 2025, **post-remand, 25 Mar 2026, p.100**. The 25 Jun 2025 order was quashed by the Bombay High Court — most published summaries still quote it. |
| Physics | Cell voltage law `U = U₀ + k·i`, NPC India Chlor-Alkali Sector Manual p.28; empirical curve p.29 |
| 120-day replay, forecast error | ₹0.133/kWh of total plant load · **0 constraint violations** · **13 loss-making days, reported not removed** |
| Against a competent ToD rule | the rule captures **18%** |
| Tests | 64 |

Results are net of membrane wear, diverted co-product and power-factor droop —
together about a fifth of the gross saving.

**Every number traces to [`SOURCES.md`](SOURCES.md) or [`ASSUMPTIONS.md`](ASSUMPTIONS.md).**
The assumptions file lists all sixteen with a basis *and a stated direction of
error*, including the ones that are still ungrounded.

---

## Honest scope

- The market and tariff layer is validated on real settled data. It has never
  been run live against an actual bill.
- The process twin has analytical grounding but **no experimental proof against
  any real plant.** The chlor-alkali site is a 700 TPD archetype, not a named
  plant. Closing that gap is eight historian tags and thirty days.
- Chlor-alkali demand response is an established research area (Otashu & Baldea;
  Weigert et al., whose model *is* validated on real plant data). The
  buffer-as-battery framing is not claimed as new. What is new here is the
  Indian regulatory grounding and the landed-cost engine inside the optimisation.
- The optional LLM constraint agent proposes *candidates* from SOP text for an
  engineer to approve. It cannot set a limit and it cannot pick a setpoint.
  With no model configured, PRANA runs a deterministic rule-based extractor —
  which is the default in this repository.

---

## Submission documents

`PRANA_PPT.pdf` · `PRANA_Technical_Proposal.pdf`
