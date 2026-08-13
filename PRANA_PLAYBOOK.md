# PRANA — The Molecular Battery Platform
### Winning playbook: "Innovation to Shape India's Energy Future" (MC²+ · Oil India · IIT Kharagpur)

> **One line:** India's largest grid-scale battery is already built and paid for. It is made of molecules — cryogenic liquid, hydrogen, ammonia, crude in a tank, clinker in a silo — and nobody is dispatching it.

> **⚠️ SUPERSEDED FOR SUBMISSION PURPOSES.** The submission-ready document is
> **[PRANA_SUBMISSION.md](PRANA_SUBMISSION.md)**, which matches the hackathon's
> actual track list and carries the measured results from the working build in
> `prana/`. This playbook remains the deeper strategy document — gap analysis,
> alternatives considered, and the long-form pitch scripts — but where the two
> disagree on a number, the submission pack and the code are correct.

**Status of numbers in this document:** every figure tagged **[computed]** was calculated during preparation of this playbook on 152,542 real 15-minute IEX settlement blocks (Maharashtra W2 bid area, DAM / RTM / G-DAM, 2022-04-01 → 2026-08-06) already held on disk. Script: `evidence/compute_flex_value.py`. Everything else is cited or flagged as an estimate. Figures about Oil India's asset base are directional and should be refreshed from OIL's latest Annual Report before submission.

---

## STEP 1 — Five deep, non-obvious problem gaps

### Gap 1 — The binding constraint on Indian industrial demand flexibility is *epistemic*, not technical

**Who suffers:** every process plant with >5 MW connected load; the DISCOM that buys ₹9–10/kWh evening power; the grid operator managing a ~52 GW evening ramp.

**Why the current system fails:** India has run demand-response pilots for over a decade and still has no regulator-approved demand-flexibility market. The standard diagnosis is "no market mechanism." That diagnosis is incomplete. The deeper failure is that **no Indian industrial plant can write down its own flexibility constraint set.** Ask a fertilizer plant "how many MW can you shed for how long, at what cost, without touching product spec?" and there is no document that answers it. The answer lives in operators' heads, in the interlock list, in HAZOP minutes, in the SOP for the ammonia synthesis loop, in the LOX tank's minimum inventory rule. Aggregators therefore offer generic ₹/MW DR contracts; plants decline, because an unquantified production risk always beats a quantified energy saving.

**Why it's still unsolved:** solving it requires someone who can read a P&ID *and* a MILP. The energy-software industry hires power engineers; the process industry hires chemical engineers. The intersection is almost empty in India.

**Data availability:** high, and mostly already inside the plant — DCS/historian tags (Aspen IP.21, OSIsoft PI), energy meters, tank level transmitters, SOPs and interlock schedules. Externally: IEX 15-min DAM/RTM/G-DAM (public), state SLDC schedules, MERC/SERC tariff orders.

**Economic impact: [computed]** On the Maharashtra RTM panel, the mean spread between the 24 dearest and 24 cheapest 15-min blocks of the *same day* was **₹5,228/MWh in FY2025-26 and ₹6,419/MWh in FY2026-27 (Apr–Aug)**. A plant that can move 20% of its load across a 6-hour buffer captures **₹19–28 lakh per MW of connected load per year** on the exchange price component alone, before any ToD tariff benefit.

---

### Gap 2 — Everyone optimizes against exchange price. The bill is not the exchange price.

**Who suffers:** C&I consumers, open-access traders, and every DR startup whose savings evaporate at the meter.

**Why the current system fails:** the market clearing price (MCP) is roughly 60% of what an Indian industrial consumer actually pays. The rest is the regulatory stack — wheeling, cross-subsidy surcharge, additional surcharge, ToD multipliers, electricity duty, and a **demand charge levied on billing kVA with a ratchet**. The last one is the killer: an optimizer that piles shifted load into cheap midday hours raises the monthly maximum demand, and the demand-charge penalty can exceed the energy saving. No commercial Indian tool models this at 15-minute resolution.

**Why it's still unsolved:** the cost stack is only knowable by reading primary SERC orders, and trade-press summaries of it are demonstrably wrong. In prior work on this exact question, **a single paragraph in a MERC MYT order (¶11.1.3, declining the Additional Surcharge on open access from FY2025-26) was worth ₹1.39/kWh and flipped the sign of the open-access business case** — from +₹1.26/kWh in favour of open access to −₹0.13/kWh against it.

**Data availability:** medium-hard but done — MERC/SERC tariff orders (PDF), MSEDCL/Mahadiscom tariff schedules, CERC market data. This work is already complete for Maharashtra HT-Industry in the author's thesis.

**Economic impact:** non-energy charges are **~40% of a Maharashtra C&I consumer's landed cost**. Optimizing on MCP alone can produce a schedule that is 40% mispriced and occasionally negative-value.

---

### Gap 3 — Green-hydrogen DPRs in India are being written on annual-average power prices. The 15-minute price-duration curve is what actually sets LCOH.

**Who suffers:** every PSU with a green H₂ investment decision in front of it right now — Oil India (Jorhat pilot), NRL, IOCL, GAIL, NTPC — and the National Green Hydrogen Mission's cost trajectory.

**Why the current system fails:** the standard electrolyser business case maximizes capacity utilisation factor (CUF) to amortise capex, and takes a single blended ₹/kWh for power. Both assumptions are now wrong, because India's intraday price shape has collapsed. The correct object is the **price-duration curve**, and LCOH is minimised at an *interior* CUF, not at maximum CUF.

**[computed] Mean RTM price of the cheapest N hours of the year, Maharashtra:**

| FY | 2000 h | 3000 h | 4000 h | 5000 h | 6000 h | 7000 h | all 8760 h |
|---|---|---|---|---|---|---|---|
| 2022-23 | ₹2.60 | ₹2.93 | ₹3.21 | ₹3.51 | ₹3.84 | ₹4.26 | ₹5.63 |
| 2023-24 | ₹2.53 | ₹2.81 | ₹3.03 | ₹3.25 | ₹3.50 | ₹3.86 | ₹5.04 |
| 2024-25 | ₹2.09 | ₹2.38 | ₹2.60 | ₹2.79 | ₹2.97 | ₹3.19 | ₹4.21 |
| **2025-26** | **₹1.53** | **₹1.83** | **₹2.08** | **₹2.29** | **₹2.48** | **₹2.67** | **₹3.59** |

**[computed] Resulting LCOH frontier** (alkaline, 50 kWh/kg, capex ₹45,000/kW, 10% WACC / 20 y, O&M 3% of capex, grid RTM energy only — *excludes* open-access charges and SIGHT incentives; treat as a shape, not a quote):

| FY | 2000 h | 3000 h | 4000 h | 6000 h | 8000 h |
|---|---|---|---|---|---|
| 2024-25 | ₹271/kg | ₹230 | ₹213 | **₹204** | ₹224 |
| 2025-26 | ₹242/kg | ₹202 | ₹187 | **₹179** | ₹190 |

**The finding: the LCOH minimum sits at ~6,000 hours, not 8,000.** Running the last 2,000 hours a year costs more in expensive power than it saves in capex amortisation — and the gap is widening every year. A DPR built on 90% CUF is systematically overstating LCOH *and* mis-sizing the electrolyser and buffer.

**Bonus [computed] finding — the green premium has collapsed exactly where green generates.** G-DAM over DAM in the 09:00–17:00 solar window fell from **₹535/MWh (FY22-23) to ₹43/MWh (FY24-25) and ₹251/MWh (FY25-26)**, while the *evening* premium rose (₹508 → ₹586). Translation for a refinery: **buying certified green power in solar hours now costs 4–25 paise/kWh more than brown power; buying it in the evening costs 59 paise.** Solar-hour electrolysis is therefore near-free to make green, without owning a single panel. Nobody has published this.

---

### Gap 4 — Oil & gas midstream is an unrecognised national flexibility fleet

**Who suffers:** Oil India, IOCL, HPCL, BPCL, GAIL — and the grid, which is missing hundreds of MW of free ramp.

**Why the current system fails:** a crude or product pipeline is a chain of pumping stations with **tankage at both ends and at intermediate points**. Physically this is *identical* to a pumped-storage scheme with a chemical working fluid: pumping is a schedulable load, tank level is state-of-charge, batch scheduling and interface-contamination limits are the constraints. Yet pipeline pumping is scheduled on throughput targets and operator convenience, never against a 15-minute price. The same is true of every ASU, every water-treatment train, every raw-mill and cement grinding circuit.

**Why it's still unsolved:** pipeline scheduling software (batch tracking, hydraulics) and energy trading software are different vendor ecosystems that have never been coupled. Nobody owns the interface.

**Data availability:** SCADA at pumping stations, tank gauging, batch schedules — all internal to the operator, all already instrumented. This is precisely why a PSU partner makes the MVP deployable.

**Economic impact:** Indian crude and product pipeline networks span tens of thousands of km with large aggregate pumping loads. At the **[computed]** ₹19–28 lakh/MW-yr flexibility value above, a 100 MW aggregate pumping fleet with 6-hour tank buffering is a **₹19–28 crore/year** line item, at essentially zero capex.

---

### Gap 5 — The deviation-arbitrage business model is already dead, and almost nobody knows it

**Who suffers:** every team at every hackathon and every early-stage DR startup that builds a "DSM arbitrage" product.

**Why the current system fails:** the intuitive flexibility play is to deliberately under- or over-draw against schedule and settle at the DSM rate. A prior audit of 133,056 WRPC DSM blocks against the exchange panel established that **the published DSM rate ≈ max(DAM ACP, RTM ACP) for the same delivery block** (correlation 0.955–0.971; slope ≈ 1.0; correlation peaks at zero lag). Consequence: **the DSM rate is ≥ the RTM price in 99.9% of blocks in the backtest window.** Deviation arbitrage is impossible *by regulatory design*, not by bad luck.

**Why it's still unsolved:** it isn't documented anywhere public. It is only visible if you download the settlement files and check their own arithmetic — which also surfaces two silent traps (the deviation sign convention flips between files, and the rate column is ₹/MWh in one schema and paise/kWh in two others, a factor-of-ten step).

**Economic impact:** negative — this gap destroys value by attracting capital to a dead strategy. Knowing it is a moat. It also has a constructive corollary: **DAM price is the single strongest legitimate predictor of RTM price** (corr 0.811, beating same-block previous-day persistence at 0.765) and is known 12–36 h ahead. Any serious flexibility scheduler must be built on DAM-informed RTM forecasting with DSM as a hard *risk constraint*, never a profit source.

---

## STEP 2 — Three breakthrough solutions

### Idea A — **PRANA**: the Molecular Battery Platform ⭐

| | |
|---|---|
| **Problem** | Process plants hold enormous latent energy storage in their intermediate inventories, but cannot quantify the cost of using it, so they never do. |
| **Solution** | A process-physics digital twin that derives each buffer's **marginal flexibility cost curve** (₹/MWh vs MW shifted vs duration), a stochastic MILP that dispatches it against forecast 15-min landed cost, and an LLM constraint agent that extracts the plant's real operating rules from SOPs, interlock lists and operator dialogue. |
| **Target user** | Refineries, fertilizer/ammonia, air separation, chlor-alkali, cement, pipeline pumping. Buyer: Head of Energy / Chief Manager (Operations). Champion: plant energy manager. Blocker: production head. |
| **Why existing solutions fail** | Energy management systems (Schneider, Siemens, Honeywell) *report* consumption; they do not model process constraints or trade. APC/RTO vendors optimize the process but treat power price as a constant. DR aggregators optimize the market but treat the plant as a black box with a fixed MW pledge. Nobody owns the coupling. |
| **AI/Tech** | Reduced-order process twins (first-principles + historian-fitted); LightGBM quantile price forecast; stochastic MILP with CVaR (HiGHS); LLM agent for constraint elicitation, schedule explanation and what-if; RAG over tariff orders and SOPs. |
| **Data** | IEX DAM/RTM/G-DAM 15-min (held); WRPC/RPC DSM (held); NASA POWER weather (held); MERC/SERC tariff orders (parsed); plant historian via OPC-UA. |
| **MVP** | High — the market data is already on disk and the twins are 150–300 lines of Python each. |
| **Revenue** | SaaS ₹25–60 lakh/site/yr + 15–20% verified gainshare + VPP aggregation take-rate later. |

### Idea B — **HYDRA**: price-duration-optimal green hydrogen for refineries

Sizes and dispatches an electrolyser + H₂ buffer against the real 15-min price-duration curve, co-optimized against the refinery's grey-H₂ (SMR) marginal cost, so hydrogen is made when power is cheap and drawn from buffer when it is not. Output: the LCOH frontier above, plus optimal electrolyser oversizing ratio and buffer size, plus a G-DAM green-attribution strategy exploiting the collapsed solar-hour green premium. Directly targets Oil India's Jorhat pilot and NRL's expansion hydrogen demand. **Verdict: this is not a separate company — it is PRANA's most valuable asset archetype.** Ship it as a module.

### Idea C — **DARPAN**: capture-rate & curtailment risk engine for RE assets and PPAs

The supply-side mirror. Publishes India's first settlement-data capture-rate index (**[computed]** Maharashtra solar-window capture ratio has fallen RTM 0.857 → 0.654 and DAM 0.821 → 0.539 across four complete FYs), attributes curtailment to economic vs transmission cause at 15-min resolution, and prices merchant risk in PPAs. This is the Modo Energy / Pexapark business model, unbuilt for India. **Verdict: it is the analytics/data-product surface of the same platform, and a strong Year-2 revenue line — not the hackathon build.** Too little of it is a *system*; most of it is a report.

---

## STEP 3 — The choice: **PRANA**

| Criterion | Why PRANA wins |
|---|---|
| **Impact** | Attacks the largest measured lever. In the author's own five-lever ranking on this data, load shifting beat exchange-timing by roughly an order of magnitude — and load shifting is the one lever with no product behind it. |
| **Win probability** | It is a *system*, not a model. It has a physics layer an IIT professor can interrogate, a market layer a PSU energy manager recognises, and an AI layer that is genuinely necessary rather than decorative. |
| **PSU relevance** | Oil India can be customer #1 in three places at once: pipeline pumping stations, NRL's utilities block (ASU, hydrogen, cooling), and the Jorhat/NRL green-H₂ programme. |
| **Startup potential** | Recurring SaaS + gainshare, a defensible constraint library that compounds per deployment, and a natural evolution into a VPP the moment India's flexibility market opens. |
| **Defensibility** | The regulatory cost engine took months of primary-document work. The DSM finding kills the obvious competing strategy. The process-constraint library is the moat and it grows with every site. |

Ideas B and C are folded in as **a module** and **a data product**, so the pitch is one platform with three revenue surfaces — not three half-ideas.

---

## STEP 4 — The full solution

### 🚀 Name
**PRANA** — *Process Response & Adaptive Network Agent*
प्राण, the life-breath. Tagline: **"India's biggest battery is already built. It's made of molecules."**

### 🧠 Core innovation (the one sentence)
> **PRANA converts any industrial process buffer into a dispatchable virtual battery by deriving its marginal flexibility cost curve from process physics, then trading that curve against forecast 15-minute *landed* electricity cost under an agent that never proposes a schedule the plant's own interlocks would reject.**

Two claims inside it, both non-obvious:
1. **State-of-charge is inventory, not electrons.** A LOX tank, an H₂ buffer, an intermediate ammonia storage, a crude tank, a clinker silo — each is a battery whose round-trip efficiency is a process penalty, not an electrical one.
2. **The optimizer was never the hard part.** Getting the constraints out of the plant is. That is where the LLM belongs — not writing the schedule, but eliciting the feasible set.

### 🏗 System architecture

```
┌─ LAYER 1 · INGESTION ────────────────────────────────────────────────┐
│  Market   IEX DAM / RTM / G-DAM 15-min · RPC DSM · SLDC schedules    │
│  Plant    OPC-UA / Modbus → historian (PI, IP.21): power, flow,      │
│           tank level, temp, pressure, product spec, equipment state  │
│  Regulatory  SERC tariff orders, ToD schedule, OA charges (RAG)      │
│  Exogenous   NASA POWER weather, plant production plan               │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌─ LAYER 2 · TWIN  (the novel object) ─────────────────────────────────┐
│  Reduced-order process model per asset archetype                     │
│    • specific power curve P(load) with part-load efficiency penalty  │
│    • inventory dynamics  I(t+1) = I(t) + prod(t) − demand(t) − loss  │
│    • ramp / min-up / min-down / start cost                           │
│    • quality & safety envelope (spec drift, interlock margins)       │
│  ⇒ OUTPUT: FLEXIBILITY COST CURVE  φ(ΔMW, Δt) in ₹/MWh               │
│     Fitted to historian data, validated on held-out plant history.   │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌─ LAYER 3 · FORECAST ─────────────────────────────────────────────────┐
│  Quantile LightGBM (q10/q50/q90) for RTM landed cost, 96 blocks      │
│  Key feature: DAM_t (known 12–36h ahead, corr 0.811 with RTM)        │
│  + lags, ToD block, weather, day-type, coal stock, demand            │
│  Baselines it must beat: naive persistence, DAM-persistence, ARIMA   │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌─ LAYER 4 · DECISION ENGINE ──────────────────────────────────────────┐
│  Stochastic MILP, 96×15-min rolling horizon, HiGHS via CVXPY/PuLP    │
│  min  Σ_b [ energy(b)·landed_price(b) ] + demand_charge(max kVA)     │
│        + start/ramp costs + φ(process penalty) + λ·CVaR₉₅(cost)      │
│  s.t. inventory bounds · ramp · min-up/down · production target      │
│       · DSM band (hard risk constraint — never a profit term)        │
│       · contract-demand ceiling · interlock-derived no-go windows    │
│  ▸ SAFETY GUARD: feasible set ⊂ DCS operating envelope. Any schedule │
│    violating a rate-of-change or inventory rule is rejected pre-UI.  │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌─ LAYER 5 · AGENT & OUTPUT ───────────────────────────────────────────┐
│  LLM agent (tool-calling), three jobs — none of them "chatbot":      │
│   1. CONSTRAINT ELICITATION — reads SOPs / interlock lists / HAZOP   │
│      and interviews the operator; emits typed MILP constraints for   │
│      human sign-off. This is the product's real onboarding engine.   │
│   2. EXPLANATION — "why is the ASU at 70% at 19:15?" with the        │
│      binding constraint and the ₹ consequence of overriding it.      │
│   3. PERTURBATION — "Compressor B is down 14:00–18:00" in plain      │
│      language → constraint injected → re-solve → diff explained.     │
│  Surfaces: Streamlit/React console · REST API · DCS setpoint write   │
└──────────────────────────────────────────────────────────────────────┘
```

### 🤖 AI components, and why each is *needed*

| Component | Method | Why not simpler |
|---|---|---|
| Price forecast | Quantile LightGBM, q10/q50/q90 | Point forecasts make the MILP overconfident; the buffer decision is inherently a risk decision. CVaR needs distributions. |
| Load / production forecast | Gradient boosting on production plan + historian | Flexibility available tomorrow depends on tomorrow's campaign. |
| Process twin | First-principles ROM, parameters fitted to historian | A pure ML twin cannot extrapolate to operating points the plant has never visited — which is exactly where flexibility lives. **This is the reason it must be physics-based.** |
| Dispatch | Stochastic MILP + CVaR | RL is the wrong tool: no simulator fidelity, no safety guarantee, and a PSU will never accept an unexplainable policy. MILP gives duals → shadow price of every constraint → the ₹ cost of each plant rule. That number is itself a product. |
| LLM agent | Tool-calling + RAG over SOPs and tariff orders | The onboarding bottleneck is constraint capture. This is the one place where an LLM is not decoration. |
| Digital twin simulation | Monte Carlo over price scenarios × outage scenarios | Needed for the annual ₹ claim and for M&V baselining. |

### 🔐 The trust ladder (say this to PSU judges — it is what they are actually worried about)

- **L1 Advisory** — PRANA proposes, operator reads, nothing is written. Value proven in shadow mode against actuals for 4–8 weeks.
- **L2 Supervised** — one-click accept; setpoints written via OPC-UA; every DCS interlock retains absolute veto.
- **L3 Bounded closed loop** — autonomous only inside a pre-approved envelope agreed with the production head, with automatic reversion to the nominal schedule on any twin/actual divergence.

No step bypasses a safety interlock. Ever. PRANA's feasible set is a strict subset of the plant's licensed operating envelope.

### 📊 Data pipeline

```
SOURCE                 CLEAN                      FEATURES                 MODEL          OUTPUT
IEX HTML form POST  →  31-day windowing, block  → DAM_t, lags 1/96/672,  → LGBM        → 96-block
(RTM/DAM/G-DAM)        ID → timestamp, dedupe     rolling μ/σ, ToD flag,   quantile       price
                       cap/floor flagging         holiday, temp, humidity  forecast       distribution
RPC DSM files       →  per-file sign-convention → lagged DSM rate ONLY   → risk         → DSM band
(3 schemas!)           detection; unit fix        (same-block = leakage)   constraint
SERC orders (PDF)   →  clause extraction + RAG  → ToD multiplier, demand → landed      → ₹/kWh
                       human verification         charge ₹/kVA, CSS/AS     cost engine    at meter
Plant historian     →  resample to 15-min,      → specific power curve,  → process     → φ(ΔMW,Δt)
(OPC-UA)               outlier + downtime mask    inventory dynamics       twin fit       cost curve
                                                                            ↓
                                          Stochastic MILP (96 blocks, CVaR₉₅)
                                                                            ↓
                                    Setpoint schedule + ₹ attribution + explanation
```

**Two data traps we already handle, and will name on stage** (they prove the work is real): the RPC deviation **sign convention flips between files, not along schema or date lines**; and the DSM rate column is **₹/MWh in one schema but paise/kWh in two others**. Both corrupt silently. Our parser detects convention per file and asserts the file's own arithmetic closes.

### ⚡ Real-world use case — walk the judges through this

> **12 July 2026, Numaligarh-class refinery utilities block, 100 MW connected load. [computed — real IEX day]**
>
> **07:00** — PRANA ingests the published DAM curve for the day. Forecast q50 shows a trough at **13:00 (RTM cleared at ₹1/MWh — effectively free)** and a spike to the **₹10,000/MWh price cap at 00:00**, with the evening block above ₹7,000. Same-day spread: ₹9,999/MWh.
>
> **07:05** — The twin reports what is actually movable. The ASU can run its main air compressor to 108% between 10:00 and 16:00 and bank 6 hours of LOX/LIN in the cryogenic tanks; the electrolyser can lift to full rate and fill the H₂ buffer to 90%; two pipeline pumping stations can front-load their batch. Total: **20 MW × 6 h = 120 MWh of virtual battery.** The twin also reports what is *not* movable — the crude unit charge pump, the reformer, anything on the critical path.
>
> **07:06** — The MILP prices each option against forecast landed cost *including the demand-charge term*, and finds that shifting the full 20 MW would breach contract demand at 12:45. It shifts 17 MW and staggers the electrolyser start by 30 minutes. Net position stays inside the DSM band all day — no deviation exposure, because the DSM rate is ≥ RTM 99.9% of the time and deviation is never a profit source.
>
> **10:00–16:00** — Plant absorbs cheap solar-hour power. Inventories fill.
>
> **18:30** — Board operator types: *"Compressor B tripped, back by 21:00."* The agent injects the outage, re-solves in ~2 s, draws down LOX inventory instead of restarting a compressor into the ₹8,000/MWh peak, and states the binding constraint and the cost of overriding it.
>
> **19:00–00:00** — Plant coasts on stored molecules through the entire peak. Production output for the day: **unchanged.**
>
> **Result on this single real day: ~₹10.7 lakh avoided on a 100 MW site.** Annualised at FY26-27 spreads: **₹20.6 lakh per MW per year.**

---

## STEP 5 — Track mapping

**Primary track: Digital Asset Management (AI/ML, Digital Twin).** ✅

This is not a stretch fit — it is the definitional case. The digital twin is not a 3D visualisation; it is a **physics-based reduced-order model whose purpose is to make a financial decision about a physical asset every 15 minutes.** PRANA does the three things the track names: it builds a twin of an operating asset, it applies AI/ML (quantile forecasting, stochastic optimization, LLM constraint extraction) to that twin, and it converts an under-utilised physical asset into a revenue-generating one — which is what "digital asset management" means when the asset is a compressor rather than a token.

**Why it beats a Renewable Energy submission:** the RE track will be crowded with solar forecasting and MPPT projects. PRANA *addresses* renewable intermittency — the collapse in solar-window capture is the entire reason it exists — but does so from the demand side, where the competition isn't.

**Cross-track spillover to name in the pitch (a strength, not a hedge):** the electrolyser archetype is a complete **Hydrogen** submission on its own (the LCOH-vs-CUF frontier in Gap 3), and the bio-refinery/ethanol plant is a valid archetype for **Bioenergy**. One platform, three tracks' worth of applicability. Say this in ten seconds and move on.

---

## STEP 6 — Executive summary (submission-ready, ~470 words)

**PRANA — The Molecular Battery Platform**

**Problem.** India's grid problem is no longer generation; it is shape. On four years of 15-minute IEX settlement data for the Maharashtra bid area (152,542 blocks), the ratio between mean evening-peak price and mean solar-window price rose from **1.47 in FY2022-23 to 2.23 in FY2025-26, and 3.53 in FY2026-27 to date**. Blocks clearing below ₹2/kWh grew from 4.1% to 21.1% of the year. Simultaneously the evening peak hardened, repeatedly clearing at the ₹10/kWh cap. The country is being told the answer is battery storage — 73.9 GW / 411.4 GWh by 2031-32, at tariffs of ₹6.27–6.46/kWh. But India's process industries already own hundreds of GWh of latent storage in their intermediate inventories — cryogenic liquid, hydrogen, ammonia, crude in tankage, clinker — and dispatch none of it, because no plant can quantify what using it costs.

**Working principle.** Any process with an intermediate buffer is a battery whose state of charge is inventory and whose round-trip loss is a process efficiency penalty. PRANA makes that battery dispatchable in three steps. A **physics-based reduced-order digital twin**, fitted to plant historian data, derives each buffer's *marginal flexibility cost curve* φ(ΔMW, Δt) in ₹/MWh — the first-class object the industry currently lacks. A **stochastic mixed-integer optimizer** dispatches that curve against a quantile forecast of the **landed** cost of power — not the exchange price, but the price at the meter, including time-of-day multipliers, the demand charge on billing kVA, and open-access surcharges parsed from primary SERC orders, which together are roughly 40% of an Indian industrial consumer's electricity cost. An **LLM constraint agent** solves the real onboarding bottleneck by reading SOPs, interlock schedules and operator dialogue and emitting typed optimizer constraints for human sign-off, then explaining every dispatch decision and its binding constraint in plain language.

**Methodology.** Rolling 96-block horizon; LightGBM quantile forecasts (q10/q50/q90) driven principally by the day-ahead clearing price, which is known 12–36 hours in advance and correlates 0.811 with real-time price; MILP solved by HiGHS with a CVaR₉₅ risk term; deviation settlement modelled strictly as a hard risk constraint, never a revenue source, because audit of 133,056 deviation-settlement blocks shows the published rate equals max(day-ahead, real-time) price and therefore exceeds real-time price in 99.9% of blocks. Deployment follows a three-stage trust ladder — advisory, supervised, then bounded closed loop — and PRANA's feasible set is always a strict subset of the plant's licensed operating envelope; no DCS interlock is ever bypassed.

**Industrial impact.** Measured on real settlement data, a plant able to move 20% of load across a six-hour buffer captures **₹19–28 lakh per MW of connected load per year**. For a 100 MW refinery or fertilizer complex that is a 20 MW / 120 MWh virtual battery — displacing roughly **₹130 crore of battery capital expenditure at zero capex** — and, on 12 July 2026, ₹10.7 lakh avoided in a single day with no loss of production.

---

## STEP 7 — Hackathon MVP

### What actually gets built

| # | Module | Effort | Deliverable | Fallback if time runs out |
|---|---|---|---|---|
| 1 | **Market data core** | 1 h | 152k-block IEX panel already on disk, loaded and validated | — (already done) |
| 2 | **Landed-cost engine** | 3 h | ₹/kWh at meter per block: MCP + ToD × + wheeling + duty; demand-charge term on rolling monthly max kVA | Energy charge + ToD only, demand charge as a post-hoc check |
| 3 | **Process twins ×3** | 6 h | ASU+LOX tank · electrolyser+H₂ buffer · pipeline pump+tankage. Each: specific-power curve, part-load penalty, inventory ODE, ramp/min-up/min-down | Ship 2 archetypes, present the third as a spec |
| 4 | **Price forecaster** | 3 h | LightGBM quantile q10/q50/q90; features DAM_t + lags + ToD + weather; backtested vs naive and DAM-persistence baselines | Use realised prices in "perfect foresight" mode and report the forecast-error haircut separately |
| 5 | **MILP dispatcher** | 5 h | CVXPY + HiGHS, 96 blocks, inventory/ramp/demand/DSM constraints, CVaR₉₅ | Drop CVaR, run deterministic on q50, quote the q10/q90 envelope |
| 6 | **LLM agent** | 4 h | Tool-calling agent: constraint elicitation from a sample SOP; "explain this schedule"; natural-language perturbation → re-solve | Pre-script two perturbations; keep it live if stable |
| 7 | **Streamlit console** | 4 h | 5 tabs (below) | Merge tabs 4 & 5 |
| 8 | **Backtest & M&V** | 2 h | Full-year replay FY2025-26 + FY2026-27 partial; ₹ saved, zero constraint violations, CO₂ proxy | Single-quarter replay |

### The console — 5 tabs

1. **Today** — price forecast fan chart (q10/q50/q90), the dispatch schedule as a stacked area, inventory trajectories with limit bands, live ₹ counter.
2. **Twin** — the flexibility cost curve φ(ΔMW, Δt) per asset. *This is the money slide. Nobody else will have one.*
3. **Agent** — chat. Judge types an outage. Schedule visibly re-solves. Agent names the binding constraint and the ₹ cost of overriding it.
4. **Backtest** — a full year replayed: actual flat operation vs PRANA, cumulative ₹, worst-day and best-day, constraint-violation count (must read **0**).
5. **Board** — the CFO view: ₹/yr, ₹/kWh, % of energy bill, MW/MWh virtual-battery equivalent, BESS capex displaced, tCO₂.

### Demo flow (5 minutes, rehearsed to the second)

| Time | Beat |
|---|---|
| 0:00 | One chart. RTM price by hour, FY22-23 vs FY26-27. The duck curve deepening in real numbers. *"Midday collapsed to ₹1.5/kWh. Evening hit the ₹10 cap. This is not a forecast — this is settled money."* |
| 0:40 | *"Everyone says: build batteries. India needs 411 GWh by 2032. Here's what nobody says —"* → the LOX tank photo. *"This refinery already owns 120 MWh of storage. It's just full of liquid oxygen instead of lithium."* |
| 1:20 | Tab 2. The flexibility cost curve. *"This is the object that doesn't exist anywhere in Indian industry. We derive it from process physics."* |
| 2:00 | Tab 1. Live run on **12 July 2026 — a real day.** Watch the plant absorb ₹1/MWh power at 13:00 and coast through the ₹10,000/MWh evening on stored molecules. **₹10.7 lakh, one day, one site.** |
| 3:00 | Tab 3. **Judge types the curveball.** "Compressor B down 14:00–18:00." Re-solve. Explanation. *(Ask a judge to type it — the moment they participate, you've won the room.)* |
| 4:00 | Tab 4. Full-year backtest. ₹ saved. **Constraint violations: 0.** Then the DSM slide: *"Here's the strategy we deliberately did NOT build, and the 133,056 settlement blocks that show why."* |
| 4:40 | Tab 5. ₹19–28 lakh/MW-yr. ₹130 crore of BESS capex displaced per 100 MW site. Oil India deployment map: pipelines → NRL utilities → Jorhat H₂. |

### Key metrics to put on the board

- **₹19–28 lakh / MW-yr** captured (real data, 20% shift depth, 6 h buffer)
- **₹10.7 lakh in one day** on a 100 MW site (12 July 2026, actual prices)
- **20 MW / 120 MWh** virtual battery per 100 MW site → **~₹130 crore** BESS capex displaced
- **0** constraint violations across the full-year backtest
- Forecast: **pinball loss and MAPE vs three baselines** (naive, DAM-persistence, ARIMA) — and the honest statement that forecast skill is *not* where the value is
- **tCO₂ avoided** from shifting into high-RE hours (state the grid EF assumption on the slide)

---

## STEP 8 — Pitch

### 🎤 60-second pitch

> "In FY23, an Indian industrial plant paid 1.5× more for evening power than midday power. This year it's 3.5×. Midday power in Maharashtra has cleared at **one rupee per megawatt-hour** — free — while the evening hits the ten-rupee cap. I know this because I've analysed 152,000 real settlement blocks.
>
> India's answer is batteries: 411 gigawatt-hours by 2032, at six and a half rupees a unit.
>
> But every refinery in this country already owns a battery. It's the liquid oxygen tank. And the hydrogen buffer. And the crude tankage. A 100 MW plant is sitting on 120 megawatt-hours of storage that is already built, already paid for, and completely undispatched — because no plant can answer the one question that matters: *what does it cost me to move that load?*
>
> **PRANA answers it.** A physics-based digital twin derives each buffer's flexibility cost curve. A stochastic optimizer trades that curve against the real landed price of power, fifteen minutes at a time. And an AI agent gets the constraints out of the plant's SOPs and out of the operator's head — which is the part everyone else skips, and the reason Indian demand response has failed for a decade.
>
> On real market data: **₹19 to 28 lakh per megawatt per year. Zero capex. Zero production loss.** For Oil India, that starts with the pumping stations and ends with green hydrogen at Numaligarh.
>
> India's biggest battery is already built. We're just the first ones dispatching it."

### 🎤 3-minute pitch

**[0:00–0:30 · The number nobody has]**
"I'm going to start with a number from real settlement data, not a projection. Over four years of 15-minute IEX prices for Maharashtra — 152,000 blocks — the ratio of evening-peak price to solar-hour price has gone from 1.47 to 3.53. The share of the year clearing below ₹2 per unit went from 4% to 21%. In FY27 so far, the midday trough has hit ₹1 per megawatt-hour and the evening has repeatedly hit the ₹10,000 cap. India's grid problem is no longer how much power. It's *when*."

**[0:30–1:00 · The consensus, and what it misses]**
"The consensus answer is storage — 73.9 GW, 411 GWh by 2032, tenders clearing at ₹6.27 to ₹6.46 a unit. That build has to happen. But it treats storage as something we have to construct, and it ignores the storage already sitting on Indian industrial sites. An air separation unit with a full LOX tank is a battery. An electrolyser with an H₂ buffer is a battery. A pipeline with tankage at both ends is a pumped-storage scheme with crude as the working fluid. Same physics. State of charge is inventory instead of electrons."

**[1:00–1:40 · Why it has never been used]**
"So why doesn't anyone dispatch it? Not because the optimization is hard — that's a solved problem. Because **nobody can write down the constraints.** Ask a plant how many megawatts it can move, for how long, at what cost, without touching product spec. There is no document. The answer is in the interlock list, the HAZOP minutes, the SOP for the synthesis loop, and in the head of a board operator with thirty years' service. That's why India has run demand-response pilots for a decade and has no demand-flexibility market. I spent two years in an ammonia-urea plant. I know exactly where those constraints live."

**[1:40–2:20 · PRANA]**
"PRANA has three layers. One: a **physics-based reduced-order twin**, fitted to historian data, that outputs each buffer's marginal flexibility cost curve in rupees per megawatt-hour — an object that does not currently exist anywhere in Indian industry. Two: a **stochastic MILP** that trades that curve against a quantile forecast of the *landed* cost of power. Not the exchange price — the price at the meter, with time-of-day multipliers, the demand charge on billing kVA, and open-access surcharges parsed from primary SERC orders. That stack is 40% of an Indian industrial power bill, and one paragraph in one MERC order is worth ₹1.39 a unit and flips the sign of the open-access business case. Every tool that optimizes on exchange price alone is 40% wrong. Three: an **LLM agent** that reads the SOPs and interviews the operator to build the constraint set, and then explains every decision — because a plant manager will not accept a setpoint they can't interrogate."

**[2:20–2:45 · Proof and safety]**
"On real prices: ₹19 to 28 lakh per megawatt per year. On 12 July 2026 — an actual day — a 100 MW site would have avoided ₹10.7 lakh, absorbing near-free power at 1 PM and coasting through the evening cap on stored molecules, with unchanged production. Full-year backtest: zero constraint violations. And we deploy on a trust ladder — advisory, then supervised, then bounded closed loop. PRANA's feasible set is always a strict subset of the plant's licensed envelope. No interlock is ever bypassed."

**[2:45–3:00 · The ask]**
"For Oil India this is three deployments in one: pipeline pumping stations, NRL's utilities block, and price-optimal dispatch for green hydrogen — where our data shows the LCOH minimum sits at 6,000 hours of operation, not 8,000, which means the DPRs being written today are mis-sizing the plant. India's biggest battery is already built. Give us one site and ninety days, and we'll dispatch it."

### ❓ Judge Q&A — the hard ones

**Q: "This is just demand response. DR has failed in India for a decade. Why are you different?"**
A: "Agreed, and I'd say the standard diagnosis is wrong. DR is usually blamed on the absence of a market mechanism. The real blocker is that plants can't quantify their own flexibility, so they can't price the production risk, so they refuse. We attack that directly with the process twin and the constraint agent. And critically, **we don't wait for a DR market to exist** — we monetise through mechanisms that are live today: exchange price exposure, ToD tariff, and demand-charge management. The DR market is upside, not a dependency."

**Q: "Why wouldn't the plant just install a battery?"**
A: "Cost. A 20 MW / 120 MWh battery is roughly ₹130 crore, and on our data a 4-hour merchant battery earns ₹61–85 lakh/MW-yr against an annualised capital cost in the same range — merchant arbitrage alone barely covers it. Our virtual battery earns ₹19–28 lakh/MW-yr at essentially zero capex, so the return on invested capital isn't comparable. They're complements: use the free storage first, then size the lithium for what's left."

**Q: "What about deviation settlement charges? Isn't the real money in DSM arbitrage?"**
A: "That's the trap, and it's the question I most wanted. We audited 133,056 WRPC deviation-settlement blocks against the exchange panel. **The published DSM rate is approximately max(DAM, RTM) for the same block** — correlation 0.955 to 0.971, slope ~1.0, peaks at zero lag. Which means the DSM rate is greater than or equal to the RTM price in **99.9%** of blocks. Deviation arbitrage is impossible by regulatory design. Any business plan built on it is dead. We model DSM strictly as a hard risk constraint and schedule through DAM and RTM."

**Q: "How accurate is your forecast? Isn't that the whole product?"**
A: "It isn't, and I can show you why. In a five-lever ranking I ran on this same data — every decision an industrial consumer can make, on one ₹/kWh axis — the exchange-timing decision came **last**, at ₹0.13/kWh realistic and ₹0.31 with perfect foresight. Load shifting came first, at an order of magnitude more. So a better forecast is worth paise; a better constraint model is worth rupees. We report pinball loss against three baselines because we should, but I'd rather be judged on whether the twin is right."

**Q: "How do you get plant data? PSUs won't open their DCS to a startup."**
A: "And they shouldn't, on day one. Level 1 is advisory and read-only, over a one-way OPC-UA gateway or even a nightly historian export — the same access an energy auditor already gets. We run in shadow mode for 4–8 weeks and prove the savings against actuals before anyone discusses a write path. Level 2 needs a single OPC-UA write tag with the DCS interlocks untouched above us. The minimum viable dataset is genuinely small: an energy meter, a tank level, and a production log."

**Q: "What if the plant isn't exposed to exchange prices — it's on a DISCOM tariff or a long-term PPA?"**
A: "Then the twin is unchanged and the value simply comes from different terms: the ToD multiplier, the demand charge on billing kVA — which is where a surprising amount of it sits — and, for a site with a captive power plant, the fuel-versus-grid decision in the steam and power network. That last one is the ammonia-plant problem I used to live with: HP/MP/LP header balance, back-pressure versus condensing turbine, letdown valve losses. Same optimizer, different objective terms."

**Q: "What's your moat? An IIT lab could build this."**
A: "Three things, and none of them is the optimizer. First, the **process constraint library** — every archetype we commission makes the next deployment in that industry faster, and onboarding cost is the entire barrier in this market. Second, the **regulatory cost engine**: months of reading primary SERC orders, where the trade-press summaries are demonstrably wrong. Third, **negative knowledge** — the DSM finding, the deviation sign-convention trap, the unit-scale trap. Those cost me weeks and they aren't published anywhere. A lab can rebuild the MILP in a fortnight. It cannot rebuild two years of being wrong."

**Q: "Where's the Oil India relevance?"**
A: "Three places. Pipeline pumping stations are the cleanest archetype in the country — tankage at both ends, a schedulable pump, and no product-quality risk beyond batch interfaces. NRL's utilities block through the 9 MMTPA expansion — the ASU, hydrogen, and cooling loads are exactly our target. And the green hydrogen programme, where our data shows something actionable right now: LCOH minimises around 6,000 operating hours, not 8,000, and the G-DAM green premium in solar hours has collapsed from ₹535 to as low as ₹43 per megawatt-hour — so solar-hour electrolysis is nearly free to certify green. If DPRs are being written on 90% CUF and annual-average power prices, they are mis-sizing the plant."

**Q: "Safety. What happens when the model is wrong?"**
A: "The model being wrong must never be a safety event, so we don't rely on it not being wrong. PRANA's feasible set is a strict subset of the plant's licensed operating envelope; every DCS interlock sits above us with absolute veto; a guard layer rejects any schedule that violates a rate-of-change or inventory bound before it reaches a human, let alone a controller; and the twin runs continuously against actuals, reverting to the nominal schedule on divergence beyond a threshold. Commercially, the model being wrong costs money. Physically, it can't do anything the plant wouldn't already allow an operator to do."

**Q: "What's the business model and how big can this get?"**
A: "SaaS of ₹25–60 lakh per site per year by connected MW, plus 15–20% of verified savings measured on an IPMVP regression baseline — PSUs prefer gainshare because it's opex-neutral. Later, aggregation: once a flexibility market opens we're already holding the constraint models for a portfolio, which is the hard part of being a VPP. On sizing — and I'll flag this as an estimate, not a measurement — Indian industrial and commercial consumption is on the order of 700 billion units a year. If 15% of that sits in buffer-bearing processes and a fifth of that is shiftable, that's about 21 BU moved annually against a ₹5/kWh spread — a gross value pool in the low ten-thousands of crores, of which a platform take is in the low thousands. I'd rather win one refinery first."

---

## STEP 9 — Why this wins

**Innovation.** The reframe is genuinely new: *storage as inventory, not electrons*, and *the flexibility cost curve as a first-class engineering object*. The AI is load-bearing rather than decorative — the LLM is not a chatbot bolted onto a dashboard, it is the mechanism that solves the actual bottleneck (constraint capture), and the twin is physics-based for a stated technical reason (you cannot ML your way to operating points the plant has never visited, which is precisely where flexibility lives).

**Feasibility.** The market data is already on disk and validated — 152,542 blocks, four years, three segments, 100% day coverage. Not "we will scrape it." The process twins are tractable ODEs. The MILP is a solved class of problem. The demo runs on a real historical day with real cleared prices. Nothing in the MVP depends on access nobody has.

**Impact.** ₹19–28 lakh/MW-yr, measured. ~₹130 crore of battery capex displaced per 100 MW site. And system-level: this is dispatchable demand that shows up exactly where the grid is breaking — absorbing curtailed midday solar and vacating the evening ramp — which is a public good the plant gets paid to provide.

**PSU relevance.** Three Oil India deployment paths, and one of them (the green-H₂ CUF finding) is an actionable correction to decisions being made in PSU boardrooms this quarter. The trust ladder, the interlock discipline, the gainshare commercial model, and the honest treatment of DSM all signal that the team understands how a PSU actually adopts technology.

**Startup potential.** Recurring revenue, a compounding constraint library, a regulatory data asset that takes months to replicate, and a clean path to becoming India's first process-industry VPP the moment the flexibility market opens.

**And the unfair advantage the pitch should name out loud:** a chemical engineer from NIT Rourkela who ran energy efficiency on an ammonia-urea DCS, then did an MBA in data science, and has spent two years on the Indian power-market settlement data. That is the exact intersection Gap 1 says is empty. The judges will believe the process constraints are real because the person describing them has stood in front of the panel.

---

## Appendix A — Computed evidence (all from `evidence/compute_flex_value.py`)

**A1. Mean RTM price by hour (₹/MWh), Maharashtra**

| Hour | FY22-23 | FY23-24 | FY24-25 | FY25-26 | FY26-27* |
|---|---|---|---|---|---|
| 03:00 | 4,476 | 3,922 | 3,369 | 3,015 | 4,882 |
| 09:00 | 5,225 | 4,910 | 3,680 | 2,668 | 1,788 |
| 12:00 | 4,348 | 3,741 | 2,603 | 1,846 | 1,550 |
| **13:00** | **3,819** | **3,281** | **2,304** | **1,646** | **1,559** |
| 16:00 | 5,751 | 5,364 | 4,087 | 3,287 | 2,871 |
| 19:00 | 8,317 | 7,339 | 6,759 | 6,183 | 6,950 |
| **22:00** | **6,706** | **6,011** | **5,606** | **5,040** | **8,051** |

\* FY26-27 = April–August 2026 only. **Seasonally biased — India's peak-demand, peak-solar months. Never quote as a full-year figure.** It indicates acceleration; it does not measure it.

**A2. The shape is collapsing**

| FY | blocks | share <₹2/kWh | share <₹1.5/kWh | solar 09-17 (₹/kWh) | evening 18-23 | **ratio** | median intraday spread |
|---|---|---|---|---|---|---|---|
| 2022-23 | 35,040 | 4.1% | 1.3% | 4.82 | 7.08 | **1.47** | ₹8,999/MWh |
| 2023-24 | 35,136 | 4.9% | 1.5% | 4.32 | 6.32 | **1.46** | ₹7,200 |
| 2024-25 | 35,038 | 8.8% | 3.3% | 3.11 | 5.82 | **1.87** | ₹7,943 |
| 2025-26 | 35,040 | 17.0% | 7.8% | 2.35 | 5.22 | **2.23** | ₹8,128 |
| 2026-27* | 12,288 | 21.1% | 11.2% | 2.00 | 7.06 | **3.53** | ₹9,424 |

**A3. Energy-neutral load-shift value, per MW of connected load** (shift 20% of a flat load from the K dearest to the K cheapest blocks of the same day; K = buffer hours × 4)

| FY | buffer | spread captured | ₹/kWh of total load | **₹ lakh/MW-yr (RTM)** | ₹ lakh/MW-yr (DAM) |
|---|---|---|---|---|---|
| 2024-25 | 4 h | ₹5,456/MWh | 0.18 | 15.9 | 18.0 |
| 2024-25 | 6 h | ₹4,643 | 0.23 | 20.3 | 23.5 |
| 2025-26 | 4 h | ₹5,228 | 0.17 | 15.3 | 17.8 |
| **2025-26** | **6 h** | **₹4,369** | **0.22** | **19.1** | **22.9** |
| 2026-27* | 6 h | ₹6,419 | 0.32 | 28.1 | 33.6 |

Note the two framings, and keep them straight on stage: **₹0.17–0.32 per kWh of *total* plant load** at 20% shift depth, which is the same thing as **₹4.4–6.4 per kWh actually moved.**

**A4. Benchmark — 4-hour BESS, perfect-foresight merchant arbitrage, 85% RTE**

| FY | median daily 4h spread | ₹ lakh/MW-yr |
|---|---|---|
| 2022-23 | ₹5,660/MWh | 65.1 |
| 2024-25 | ₹5,924 | 62.9 |
| 2025-26 | ₹5,147 | 61.3 |
| 2026-27* | ₹8,005 | 84.7 |

Against ~₹4–5 crore/MW installed for a 4-hour system, merchant arbitrage alone roughly covers annualised capital and no more — which is the argument for using the free storage first.

**A5. Demo-day candidates (FY26-27, highest intraday RTM spread)**

| Date | spread | min | max |
|---|---|---|---|
| **2026-07-12** | ₹9,999/MWh | **₹1 @ 13:00** (solar window) | ₹10,000 @ 00:00 |
| 2026-06-05 | ₹9,999 | ₹1 @ 07:45 | ₹10,000 @ 20:45 |
| 2026-04-15 | ₹10,000 | ₹0 @ 07:00 | ₹10,000 @ 00:00 |

**Use 2026-07-12** — the trough lands squarely in the solar window, which makes the duck-curve narrative visual and self-explanatory.

---

## Appendix B — Build order (do it in this sequence)

1. **Landed-cost engine first.** Every downstream number depends on it, and it is the differentiator nobody else will have. Get the demand-charge term in early — it is the one that will otherwise invalidate a savings claim on stage.
2. **One twin, end to end** (do the ASU — best documented, cleanest physics) before starting the second. A single archetype wired all the way through to the console beats three half-built ones.
3. **Deterministic MILP on realised prices** next, so you have a working ₹ number early. Add the forecast, then CVaR, only after that.
4. **Backtest before polish.** The full-year replay with zero constraint violations is what makes the claim credible; a prettier chart is not.
5. **LLM agent last**, and keep it narrow — constraint elicitation from one sample SOP plus one live perturbation. A scoped agent that works beats an ambitious one that stalls in front of judges.
6. **Rehearse the demo six times.** The judge-types-the-curveball moment is the highest-variance and highest-payoff thirty seconds in the pitch; it has to be reliable.

## Appendix C — Pre-submission checklist

- [ ] Refresh Oil India / NRL asset figures (renewable MW, refinery capacity, Jorhat H₂ plant specs) from OIL's latest Annual Report — the figures in this playbook are directional.
- [ ] Insert verified MERC MYT FY2025-26 numbers into the landed-cost engine (energy charge, ToD multipliers, demand charge ₹/kVA, ratchet %). Cite the order and paragraph on the slide.
- [ ] State the grid emission factor source on the CO₂ slide (CEA CO₂ Baseline Database) and label the estimate as approximate.
- [ ] Label FY2026-27 as April–August partial on **every** chart it appears in. A judge who catches an unlabelled seasonal figure will discount everything else.
- [ ] Label the LCOH frontier "grid RTM energy only — excludes open-access charges and SIGHT incentives" wherever it appears.
- [ ] Confirm the hackathon's IP terms and team-size rules before submitting anything with startup intent.
