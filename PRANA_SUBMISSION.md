# PRANA — Submission Pack
### Platinum Jubilee Innovation Hackathon: Innovation to Shape India's Energy Future
**MC²⁺ · Oil India Limited · IIT Kharagpur**

> Everything marked **[computed]** was produced by the code in this repository, on
> 152,542 real 15-minute IEX settlement blocks (Maharashtra W2 bid area, RTM +
> DAM + G-DAM, 2022-04-01 → 2026-08-06). Nothing in this pack is a projection
> unless it says so. Regulatory figures tagged **[placeholder]** must be
> replaced with verified MERC values before they are quoted — see
> `prana/config.py`, where every one of them is tagged in the source.

---

## STEP 1 — Three high-impact problem statements

### P1. India's grid problem is no longer *how much* power. It is *when*.

**[computed]** On four financial years of settlement data for one bid area:

| FY | share of year below ₹2/kWh | solar 09–17 | evening 18–23 | **ratio** | median intraday spread |
|---|---|---|---|---|---|
| 2022-23 | 4.1% | ₹4.82 | ₹7.08 | **1.47** | ₹8,999/MWh |
| 2023-24 | 4.9% | ₹4.32 | ₹6.32 | **1.46** | ₹7,200 |
| 2024-25 | 8.8% | ₹3.11 | ₹5.82 | **1.87** | ₹7,943 |
| 2025-26 | 17.0% | ₹2.35 | ₹5.22 | **2.23** | ₹8,128 |
| 2026-27* | 21.1% | ₹2.00 | ₹7.06 | **3.53** | ₹9,424 |

\* April–August 2026 only — India's peak-demand, peak-solar months. **Seasonally
biased; never quote as a full-year rate.** It indicates acceleration; it does not
measure it.

Who suffers: the DISCOM buying ₹9–10/kWh evening power; the industrial consumer
paying a flat profile into a 3.5× intraday ratio; the grid operator managing the
evening ramp. Unsolved because the consensus response — build storage — treats
storage as something that must be *constructed*.

### P2. The binding constraint on Indian industrial flexibility is *epistemic*, not technical.

India has run demand-response pilots for over a decade with no regulator-approved
flexibility market. The usual diagnosis is "no market mechanism." That is
incomplete. Ask a plant how many MW it can move, for how long, at what cost,
without touching product spec — **there is no document that answers.** The answer
is in the interlock list, the HAZOP minutes, the SOP for the synthesis loop, and
in a board operator's head. Aggregators therefore offer generic ₹/MW contracts;
plants decline, because an unquantified production risk always beats a quantified
energy saving.

Unsolved because it needs someone who can read a P&ID *and* a MILP. The energy-
software industry hires power engineers; the process industry hires chemical
engineers. That intersection is nearly empty in India.

### P3. Everyone optimizes against the exchange price. The exchange price is not the bill.

The market clearing price is roughly 60% of an Indian industrial consumer's
landed cost. The rest is wheeling, cross-subsidy surcharge, additional surcharge,
electricity duty, and a **demand charge levied on peak billing kVA with a
ratchet**. An optimizer that ignores the demand charge will happily raise the
monthly peak to chase cheap midday energy and hand the plant a larger bill.

**[computed] — and this is the sharpest result in the build.** Running the same
plant, the same day, the same optimizer, changing only whether the demand charge
is modelled:

| Demand charge | Site peak | Electrolyser dispatch |
|---|---|---|
| ₹590/kVA/month (reality) **[placeholder rate]** | 94.6 MW | runs **1 of 96 blocks** |
| ₹0 — what an MCP-only tool implicitly assumes | 110.0 MW | runs **20 of 96 blocks** |

An MCP-only optimizer tells this refinery to run its electrolyser twenty blocks a
day. With the real tariff in front of it, that is the wrong answer. Raising
contract demand to 125 MW changes nothing — it is the *charge*, not the *cap*.

---

## STEP 2 — Three candidate solutions

| | **A · PRANA** ⭐ | **B · HYDRA** | **C · DARPAN** |
|---|---|---|---|
| Idea | Process buffers as dispatchable virtual batteries | Price-duration-optimal green-H₂ sizing and dispatch | India's first settlement-data capture-rate & curtailment index |
| AI | Physics twin → flexibility cost curve; stochastic MILP; LLM constraint agent | MILP sizing over the 15-min price-duration curve | Attribution models + published index |
| System-level? | Yes — ingestion → twin → forecast → decision → agent → DCS | Module-level | Analytics product |
| Buildable now? | **Built** (this repo) | Subsumed as PRANA's electrolyser archetype | Mostly a report, not a system |
| Verdict | **Selected** | Ship inside A | Year-2 data product |

---

## STEP 3 — Selection

**PRANA.** It attacks the largest measured lever, it is a *system* rather than a
model, and it is already running. B is not a separate company — it is PRANA's
most valuable asset archetype and is implemented here as one of three twins. C is
the analytics surface of the same platform.

---

# 🔹 FINAL SUBMISSION

## Title of Proposed Innovation

> ## PRANA — The Molecular Battery Platform
> **Process Response & Adaptive Network Agent**
>
> *Turning the process industry's inventory buffers into India's cheapest
> grid-scale storage, through a physics digital twin that prices flexibility and
> an AI agent that gets the constraints out of the plant.*

---

## Selected Track

### **Track 4 — Digital Asset Management (AI/ML, Digital Twin, Robotics, Corrosion)**

Not a stretch fit — the definitional case. The digital twin here is not a 3D
visualisation; it is a **physics-based reduced-order model whose only purpose is
to make a financial decision about a physical asset every fifteen minutes.**
PRANA does exactly the three things the track names: it builds a twin of an
operating asset, applies AI/ML to it (quantile forecasting, stochastic
optimization, LLM constraint extraction), and converts an under-utilised physical
asset into a revenue-generating one — which is what *digital asset management*
means when the asset is a compressor rather than a token.

Cross-track spillover, worth ten seconds on stage and no more: the electrolyser
archetype is a complete **Track 6 (Hydrogen)** entry on its own, the bio-refinery
is a valid **Track 5 (Bioenergy)** archetype, and the entire premise is created by
**Track 7 (Renewable Energy)** intermittency. One platform, four tracks'
applicability. Track 4 is where it belongs because the twin *is* the innovation.

---

## Executive Summary
*(430 words — submission-ready as written)*

**Problem.** India's grid problem is no longer how much power, but when. On four
years of 15-minute settlement data for the Maharashtra bid area — 152,542 blocks
— the ratio of mean evening-peak price to mean solar-hour price rose from 1.47 in
FY2022-23 to 2.23 in FY2025-26, and 3.53 in FY2026-27 to date. The share of the
year clearing below ₹2/kWh grew from 4.1% to 21.1%, while the evening peak
repeatedly cleared at the ₹10/kWh regulatory cap. The consensus answer is battery
storage — 73.9 GW and 411 GWh by 2031-32, with recent tenders clearing at
₹6.27–6.46/kWh. That build must happen. But it treats storage as something to be
constructed, and ignores the storage India's process industries already own:
cryogenic liquid in an air-separation tank, compressed hydrogen in a buffer,
crude in pipeline tankage, clinker in a silo. None of it is dispatched, because
no plant can quantify what using it costs.

**Working principle.** Any process with an intermediate buffer is a battery whose
state of charge is inventory and whose round-trip loss is a process-efficiency
penalty. Electrical power as a function of production rate is convex, so
splitting production into a turn-down leg and a rebuild leg always burns more
kilowatt-hours than running steady, even though total product is unchanged. That
excess is the true, physical cost of the flexibility — the exact analogue of
round-trip efficiency for an electrochemical cell — and PRANA computes it as a
*flexibility cost curve*, φ(ΔMW, Δt) in ₹ per MWh shifted. This object does not
currently exist anywhere in Indian industry.

**Methodology.** A reduced-order digital twin per asset archetype, fitted to plant
historian data, emits φ and its operating envelope. A stochastic mixed-integer
program dispatches 96 fifteen-minute blocks against the **landed** cost of power —
not the exchange price, but the price at the meter, including time-of-day
multipliers, wheeling and surcharges parsed from primary regulatory orders, and
the demand charge on peak billing kVA. Prices enter as a calibrated q10/q50/q90
fan from a LightGBM quantile model, and risk is priced through a CVaR₉₅ term.
Deviation settlement is modelled as a hard risk constraint, never a revenue
source: an audit of 133,056 deviation blocks shows the published rate equals
max(day-ahead, real-time) price and so exceeds the real-time price in 99.9% of
blocks. An LLM agent converts SOPs, interlock schedules and operator speech into
typed constraints for human sign-off — the real onboarding bottleneck — and
explains each schedule from the solver's own binding constraints.

**Industrial impact.** On a 105 MW refinery utilities block, replayed over 120
consecutive delivery days at realised settlement prices and with real forecast
error: **₹0.26 per kWh of total plant load**, net of bought-in hydrogen, with
zero days worse than steady-state operation and zero constraint violations under
independent verification against the true nonlinear physics. The same three
assets constitute a **28 MW / 294 MWh virtual battery** at zero capital cost —
roughly ₹323 crore of equivalent battery investment displaced — and the
resulting demand profile absorbs midday solar and vacates the evening ramp.

---

## Solution Overview

| | |
|---|---|
| **Problem** | Process plants hold enormous latent storage in intermediate inventory but cannot quantify the cost of using it, so they never do. |
| **Solution** | Derive each buffer's marginal flexibility cost curve from process physics; dispatch it against forecast landed cost with a risk-aware MILP; use an LLM agent to extract the plant's real constraints and explain every decision. |
| **Users** | Refineries, fertilizer and ammonia plants, air separation units, chlor-alkali, cement, and pipeline pumping. Buyer: Head of Energy / Chief Manager (Operations). Champion: plant energy manager. Blocker: production head — which is why the trust ladder below exists. |
| **Impact** | Zero-capex flexibility, verified against physics, that pays the plant and simultaneously absorbs curtailed midday solar and vacates the evening ramp. |

**Why existing solutions fail.** Energy management systems (Schneider, Siemens,
Honeywell) *report* consumption; they do not model process constraints or trade.
APC/RTO vendors optimize the process but treat power price as a constant. DR
aggregators optimize the market but treat the plant as a black box with a fixed
MW pledge. Nobody owns the coupling — and the coupling is the product.

---

## System Architecture

```
┌─ 1 · INGESTION ──────────────────────────────────────────────────────┐
│ Market      IEX DAM/RTM/G-DAM 15-min · RPC deviation settlement      │
│ Plant       OPC-UA / historian: power, flow, tank level, temp, state │
│ Regulatory  SERC tariff orders → ToD, wheeling, CSS, demand charge   │
│ Exogenous   weather, production plan                                 │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 2 · TWIN  (prana/twins.py) ─▼───────────────────────────────────────┐
│ P(x) = P_nom·(a + b·x + c·x²)   convex, increasing; pipeline: P ∝ x³  │
│ SEC(x) = P/q is U-shaped ⇒ turning down AND pushing up both cost      │
│ inventory ODE · ramp · min stable load · min up/down · start cost     │
│ ⇒ OUTPUT: φ(ΔMW, Δt) in ₹/MWh — the flexibility cost curve            │
│ MILP-safe: 16 tangent hyperplanes, linearization error < 0.7%         │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 3 · FORECAST (prana/forecast.py) ───▼───────────────────────────────┐
│ LightGBM quantile q10/q50/q90 + out-of-sample conformal widening      │
│ Lead feature: same-block DAM price, known 12–36 h ahead               │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 4 · DECISION (prana/optimizer.py) ──▼───────────────────────────────┐
│ min (1−λ)·E[cost] + λ·CVaR₉₅ + starts + bought-in product + demand    │
│ s.t. twin envelope · inventory · contract demand · agent constraints  │
│ Procurement legs: hourly DAM · 15-min RTM buy/sell · deviation        │
│ ▸ deviation is offered and provably never used                        │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 5 · AGENT & OUTPUT (prana/agent.py) ▼───────────────────────────────┐
│ elicit()   SOP / interlocks / operator speech → typed constraints     │
│ explain()  solver's binding constraints → plain language              │
│ perturb()  "compressor B down 14:00–18:00" → re-solve                 │
│ Structured outputs (JSON schema) · every constraint needs sign-off    │
│ Surfaces: Streamlit console · REST API · OPC-UA setpoint write        │
└──────────────────────────────────────────────────────────────────────┘
```

**The architectural decision that makes it trustworthy:** explanations are
generated from the *solver*, not the language model. `binding` is derived from
active bounds in the solution; the LLM only phrases those facts. It cannot invent
a reason, because it is never asked to produce one.

**Trust ladder — say this to PSU judges before they ask.**
**L1 Advisory** (read-only, shadow mode, 4–8 weeks) → **L2 Supervised** (one-click
accept, OPC-UA write, every DCS interlock retains absolute veto) → **L3 Bounded
closed loop** (autonomous only inside a pre-approved envelope, automatic reversion
on twin/actual divergence). PRANA's feasible set is always a strict subset of the
plant's licensed operating envelope. No interlock is ever bypassed.

---

## MVP — what is actually built and running

```
prana/config.py      paths, market constants, every regulatory placeholder tagged
prana/data.py        IEX panel → 152,542-block cache; DSM rate = max(DAM, RTM)
prana/tariff.py      landed-cost engine + demand charge with ratchet
prana/twins.py       3 archetypes, φ(ΔMW,Δt), tangent linearization + error bound
prana/forecast.py    LightGBM quantile + conformal calibration + 3 baselines
prana/optimizer.py   96-block stochastic MILP, CVaR₉₅, CBC
prana/agent.py       constraint elicitation / explanation / perturbation
prana/backtest.py    replay + independent verification vs TRUE nonlinear physics
app.py               5-tab Streamlit console
tests/               physics, linearization, DSM, tariff, agent regression tests
```

### Verified results **[computed]**

| Check | Result |
|---|---|
| Market panel | 152,542 blocks, 1,588 complete days, 2022-04-01 → 2026-08-06 |
| Tangent linearization error | ASU 0.005%, electrolyser 0.023%, pipeline 0.622% |
| Flexibility cost curve φ | electrolyser ₹7–37/MWh · ASU ₹15–54 · pipeline ₹175–665 |
| Forecast MAE vs baselines | **1,072** vs naive 1,189 · DAM 1,271 · 7-day block mean 1,538 ₹/MWh |
| 80% interval coverage | 69.7% raw → **76.2%** after conformal widening (×1.20) |
| Deviation used | **0 MW in every solve**, across 6 dates and both forecast modes |
| Constraint violations vs true physics | **0** |
| Solve time | ~2–13 s per 96-block day on a laptop |
| Regression tests | **27 passed, 0 failed** — each pins a claim made in this pack |

### 120-day replay — the number to quote

Consecutive delivery days to 2026-08-06, settled at realised prices, savings net
of bought-in hydrogen, every schedule independently verified.

| Site | Mode | Mean saving | Per kWh of load | Annualised | Days worse | Violations |
|---|---|---|---|---|---|---|
| **Refinery** | **forecast (realistic)** | **₹5.80 lakh/day** | **₹0.260** | ₹21.2 cr/yr | **0** | **0** |
| Refinery | perfect foresight | ₹6.29 lakh/day | ₹0.282 | ₹23.0 cr/yr | 0 | 0 |
| **Ammonia–urea** | forecast (realistic) | ₹0.93 lakh/day | ₹0.085 | ₹3.4 cr/yr | 5 | 0 |

The ammonia–urea row is deliberately included even though it is weaker. A
synthesis loop ramps at ~3%/h and cannot be tripped, so it must commit early —
and under forecast error it is sometimes wrong, which is what those 5 loss-making
days are. **A slow asset is a worse flexibility asset**, and that is itself a
finding: it is why the platform is a portfolio of archetypes rather than one.

**The forecast-error haircut is 8%.** That is the honest cost of not knowing
tomorrow's price — and it is small precisely because the value lives in the
constraint model, not in forecast skill. Quote the realistic row.

### Demo flow (5 minutes)

| Time | Beat |
|---|---|
| 0:00 | One chart: RTM by hour, FY22-23 vs FY26-27. *"Midday collapsed to ₹1.5/kWh. Evening hit the ₹10 cap. Settled money, not a forecast."* |
| 0:40 | *"Everyone says build batteries. This refinery already owns 290 MWh — it's just full of liquid oxygen instead of lithium."* |
| 1:20 | **Tab 2.** The flexibility cost curve. *"This object doesn't exist anywhere in Indian industry. We derive it from process physics."* Point at the pipeline curve sitting 10× above the electrolyser's — that is the cube law, visible. |
| 2:00 | **Tab 1.** Live solve on **12 July 2026**, a real day: RTM ₹1/MWh at 13:00 → ₹10,000/MWh at midnight. Plant absorbs near-free power and coasts through the evening on stored molecules. Production unchanged. |
| 2:50 | **The kill shot.** Drag the demand-charge slider to zero. The electrolyser jumps from 1 block to 20 and the peak jumps to 110 MW. *"That is what every tool that optimizes on exchange price is telling Indian industry to do. It is wrong, and the error is 40% of the bill."* |
| 3:30 | **Tab 3.** Hand the keyboard to a judge: *"Compressor B tripped, back by 21:00."* Agent types it, re-solves, names the binding constraint. Then show the two sentences it **refused** to encode and flagged for the operator. |
| 4:20 | **Tab 4.** Full replay. Savings, and **violations: 0** — verified against the true nonlinear physics, not the linearized model. Then the DSM slide: *"Here is the strategy we deliberately did not build, and the 133,056 settlement blocks that show why."* |
| 4:50 | **Tab 5.** Board view: virtual battery MWh, BESS capex displaced, ₹/kWh. Oil India deployment map: pipelines → NRL utilities → Jorhat H₂. |

---

## Why This Will Win

**Innovation.** The reframe is new: *storage as inventory, not electrons*, and
*the flexibility cost curve as a first-class engineering object*. The AI is
load-bearing, not decorative — the LLM is not a chatbot on a dashboard, it is the
mechanism that solves the actual bottleneck (constraint capture), and the twin is
physics-based for a stated technical reason: you cannot machine-learn your way to
operating points the plant has never visited, and that is precisely where
flexibility lives.

**Industry relevance.** Three Oil India deployment paths — pipeline pumping
stations, NRL's utilities block, and price-optimal dispatch for the green
hydrogen programme. The trust ladder, the interlock discipline, the gainshare
commercial model and the honest treatment of deviation settlement all signal a
team that understands how a PSU actually adopts technology.

**Feasibility.** It runs. 152,542 real blocks already cached, MILP solving in
seconds, zero violations under independent verification, and a demo that executes
on a real historical day. Nothing depends on access nobody has.

**Startup potential.** SaaS ₹25–60 lakh/site/yr plus 15–20% of verified savings on
an IPMVP baseline; a constraint library that compounds with every deployment; a
regulatory cost engine that takes months of primary-document work to replicate;
and a clean path to becoming India's first process-industry VPP the moment a
flexibility market opens.

**And the unfair advantage, said out loud:** a chemical engineer from NIT
Rourkela who ran energy efficiency on an ammonia–urea DCS, then took an MBA in
data science, and has spent two years inside Indian power-market settlement data.
That is exactly the intersection P2 says is empty. The judges will believe the
process constraints are real because the person describing them has stood in
front of the panel.

---

## Anticipated questions

**"Isn't this just demand response? That has failed in India for a decade."**
Agreed on the record, and I think the usual diagnosis is wrong. DR is blamed on
the absence of a market mechanism. The real blocker is that plants cannot
quantify their own flexibility, so they cannot price the production risk, so they
refuse. We attack that directly with the twin and the constraint agent. And
critically we do not wait for a DR market — we monetise through mechanisms that
are live today: exchange exposure, time-of-day tariff, and demand-charge
management. A flexibility market is upside, not a dependency.

**"Why not just install a battery?"** Cost. A 20 MW / 290 MWh system is roughly
₹300 crore, and on this panel a 4-hour merchant battery earns ₹61–85 lakh/MW-yr
against an annualised capital cost in the same range — merchant arbitrage alone
barely covers it. The virtual battery has essentially zero capex, so the returns
are not comparable. They are complements: use the free storage first, then size
the lithium for what is left.

**"What about deviation settlement — isn't the real money in DSM arbitrage?"**
That is the trap, and it is the question I most want. We audited 133,056 WRPC
deviation blocks against the exchange panel: the published rate is approximately
max(DAM, RTM) for the same block — correlation 0.955–0.971, slope ≈ 1.0, peaking
at zero lag — so it is at or above the real-time price in 99.9% of blocks.
Deviation arbitrage is impossible by regulatory design. **We gave our optimizer
the deviation lever anyway and it declines to use it in every single solve.** That
is on the Backtest tab as `max_deviation_mw = 0`.

**"How accurate is the forecast? Isn't that the product?"** It isn't, and I can
show why. In a five-lever ranking on this same data, exchange timing came *last*
at ₹0.13/kWh realistic against ₹0.31 with perfect foresight, while load shifting
came first by roughly an order of magnitude. A better forecast is worth paise; a
better constraint model is worth rupees. We beat naive persistence, DAM-as-
forecast and a 7-day block mean, and we report pinball loss against all three —
but I would rather be judged on whether the twin is right.

**"Your savings look large. What's the counterfactual?"** One steady setpoint per
asset, held all day, chosen to hold inventory — how these plants are actually run,
not a strawman. And the saving is **net of bought-in product**: when PRANA idles
the electrolyser and buys SMR hydrogen instead, we charge ourselves for the gas.
Without that correction the headline was ~28% higher and would have been wrong.

**"How do you get plant data? A PSU won't open its DCS to a startup."** And it
shouldn't, on day one. L1 is advisory and read-only over a one-way gateway or a
nightly historian export — the same access an energy auditor already gets. We run
in shadow mode for 4–8 weeks and prove savings against actuals before anyone
discusses a write path. The minimum viable dataset is genuinely small: an energy
meter, a tank level, and a production log.

**"What's the moat? An IIT lab could rebuild this."** Three things, none of them
the optimizer. The **process constraint library** — every archetype we commission
makes the next deployment in that industry faster, and onboarding cost is the
entire barrier in this market. The **regulatory cost engine** — months of reading
primary SERC orders, where trade-press summaries are demonstrably wrong. And
**negative knowledge**: the deviation finding, the sign-convention trap, the
unit-scale trap. A lab can rebuild the MILP in a fortnight. It cannot rebuild two
years of being wrong.

---

## Honest limitations — state these before a judge finds them

1. **Every regulatory number is a placeholder** pending verification against the
   MERC MYT order. They are tagged in `prana/config.py`. The *architecture* of
   the landed-cost engine is the contribution; the specific rupees are not yet
   audited. The additional-surcharge parse in particular flips the sign of the
   open-access case and is explicitly unverified.
2. **The three twins are archetypes with indicative parameters**, in published
   ranges but not fitted to a specific plant's historian. Commissioning means
   fitting them to real data; the parameters shown are a demonstration of the
   method, not a claim about any real asset.
3. **FY2026-27 is April–August only** and is seasonally biased upward. Labelled
   on every chart it appears in.
4. **The 80% forecast interval covers 76.2%, not 80%** — the test period is more
   volatile than the calibration window. Under-coverage means the CVaR term is
   mildly optimistic; we report it rather than tuning it away.
5. **Single-site.** The aggregation/VPP layer is designed, not built.
6. **CO₂ figures are estimates** from a peak-vs-solar-hour grid emission-factor
   difference. Cite the CEA CO₂ Baseline Database and label them as estimates.

---

## Appendix — a correction to carry forward from the earlier project

The prior submission's BESS NPV sensitivity swept capex at **₹2.5–5.5 crore per
MWh** and concluded the investment is negative-NPV in all 63 cells. Indian
utility-scale BESS is currently on the order of **₹1.0–1.2 crore per MWh
installed** — the sweep is roughly 3–4× high. Re-running the same model at
₹1.0 crore/MWh with the same ₹42,000 crore annual benefit and 15-year life turns
NPV from about **−₹8.8 lakh crore to roughly +₹19,000 crore**: the sign flips.

**Do not reuse that heatmap without fixing the axis** — the conclusion inverts,
and a judge who knows current BESS pricing will catch it. Fixing it strengthens
rather than weakens the PRANA argument: storage economics are far better than
that chart implies, *and* the free storage inside the fence should still be
dispatched first.
