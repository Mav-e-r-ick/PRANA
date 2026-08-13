# SUBMIT THIS
### PRANA — the electrochemical grid battery
**Platinum Jubilee Innovation Hackathon · MC²⁺ · Oil India Limited · IIT Kharagpur**

> **Read this first.** You do not have 24–48 hours of building ahead of you. The
> engine already exists and has been re-aimed at the new industry — the twin is
> written, the backtest has run, the tests pass. What is left is roughly two
> hours of slide-making. The build plan in §6 is a *checklist of what is already
> done*, plus three small things worth doing with the time you have.

---

## 1 · TITLE

> # PRANA
> ## India's Electrochemical Grid Battery
> **Process Response & Adaptive Network Agent**
>
> *The cell house is the battery. We price its flexibility from first-principles
> electrochemistry, dispatch it against the landed cost of power, and let an AI
> agent get the constraints out of the plant.*

---

## 2 · TRACK

### **Digital Asset Management (AI/ML, SCADA, Digital Twin)**

The definitional case, not a stretch. The digital twin here is not a 3D
visualisation — it is a **physics-based reduced-order model whose only purpose is
to make a financial decision about a physical asset every fifteen minutes**, and
whose convexity is *derived from the cell voltage law*, not assumed. AI/ML sits
on top of it: quantile price forecasting, stochastic optimization, and LLM
constraint extraction. It converts an under-utilised physical asset into a
revenue-generating one. That is what digital asset management means when the
asset is a rectifier rather than a token.

**Say this once and move on:** the same twin *is* a green hydrogen electrolyser
(§9), which puts it in the Hydrogen track too. One platform, two tracks, and
Oil India is building the second one at Jorhat right now.

---

## 3 · EXECUTIVE SUMMARY
*(468 words — paste as-is)*

**Problem.** India's grid problem is no longer how much power, but when. On four
years of 15-minute settlement data for the Maharashtra bid area — 152,542 real
blocks — the ratio of mean evening price to mean solar-hour price rose from 1.47
in FY2022-23 to 2.23 in FY2025-26 and 3.53 in FY2026-27 to date, while the share
of the year clearing below ₹2/kWh grew from 4.1% to 21.1%. The consensus answer
is to build batteries: 73.9 GW and 411 GWh by 2031-32. That build must happen.
But it treats storage as something to construct, and overlooks the fact that
India's electrochemical industry already owns 1.3 GW of the most flexible load on
the system and dispatches none of it.

**Working principle.** A chlor-alkali cell house is a battery whose state of
charge is the caustic soda tank. Crucially, its economics are not asserted but
derived: in an electrochemical cell, voltage rises linearly with current density
(V = V₀ + k·i) while Faraday's law makes production proportional to current, so
electrical power is necessarily **quadratic and convex in production rate**.
The National Productivity Council of India publishes that law (Chlor-Alkali
Sector Manual, p.28) and an empirical cell curve (p.29); fitted over the
operating range it implies a quadratic coefficient of 0.30-0.45, against the
0.21 this model uses — so the round-trip loss here is the conservative one. Two consequences follow. First, splitting
production into a turn-down leg and a rebuild leg always burns more kilowatt-hours
than running steady even though total product is identical — that excess is the
true, physical cost of flexibility, the exact analogue of round-trip efficiency
for a lithium cell. Second, and unusually, specific energy consumption *falls* as
the cell turns down. The National Productivity Council's published empirical
cell equation (E = 2.41 + 0.329·i + 0.24·log i) gives a cell whose specific
energy falls monotonically on turn-down — chlor-alkali is the one industrial
process that is paid, in energy terms, to be flexible.

**Method.** A reduced-order digital twin emits a *flexibility cost curve*
φ(ΔMW, Δt) in rupees per MWh shifted. Chlor-alkali demand response is an
established research area — Otashu & Baldea, and Weigert et al., whose dynamic
model is validated against real plant data — and the buffer-as-battery framing
is not claimed as new. What is new is Indian: a four-year settled IEX panel, a
primary MERC tariff order opened to the page, and a landed-cost engine that
prices ToD, surcharges, duty and the demand charge on peak kVA *inside* the
optimisation rather than after it. No reviewed paper does that for India. A stochastic mixed-integer program then dispatches 96 fifteen-minute
blocks against the **landed** cost of power: not the exchange price, but the price
at the meter including time-of-day multipliers, open-access surcharges and the
demand charge on peak billing kVA, which together are 46% of the bill. Prices
enter as a conformally calibrated q10/q50/q90 fan from a LightGBM quantile model;
risk is priced through a CVaR₉₅ term. Deviation settlement is offered to the
optimizer as a decision variable and provably never used, because an audit of
133,056 deviation blocks shows the published rate equals max(day-ahead, real-time)
price. An LLM agent converts standard operating procedures and operator speech
into typed, sign-off-gated constraints, and explains every schedule from the
solver's own binding constraints rather than from the model's imagination.

**Impact.** Replayed over 120 consecutive real delivery days with real forecast
error on a 700 TPD plant: **₹0.133 per kWh of total plant load**, ₹9.17 crore a
year, 1.53% of the electricity bill, with zero constraint violations under
independent verification against the true nonlinear physics. That figure is *net*
of every cost the flexibility creates — membrane life consumed by setpoint
movement, chlorine diverted to the bleach plant, and the extra kVAh from
power-factor droop on turn-down together take back 20% of the gross saving.
Thirteen of the 120 days came out worse than steady-state operation, reported
rather than removed. The critical constraint is not the cell's H₂-in-Cl₂ safety
interlock at 40% load but the **chlorine consumer's turndown**, because chlorine
is made stoichiometrically and cannot be stored; modelled explicitly, it holds the
cell house at 70% of design and makes the deliverable virtual battery **21.8 MW /
748 MWh at zero capital cost**. Sweeping that consumer's flexibility shows the
value is nearly flat between 60% and 80% turndown — the money comes from shedding
at the right *time*, not from shedding *deeply*. At a plant where power is 50–60%
of production cost, ₹9.17 crore is a visible line on the works manager's P&L rather than
a rounding error, which is the test the refinery case failed.

---

## 4 · SOLUTION OVERVIEW

| | |
|---|---|
| **Who loses money today** | Indian chlor-alkali producers. Power is **50–60% of caustic soda production cost** (NPC India, p.22), they are fully grid-exposed, and they run a flat load into a market whose intraday price ratio is now 3.5×. |
| **How much** | **₹0.133/kWh** of avoidable cost *net of membrane wear, chlorine dumped and kVAh droop*, **₹9.17 crore/year** for one 700 TPD plant, ≈**₹155 crore/year across the Indian sector**. |
| **Why nobody has fixed it** | Not because optimization is hard. Because no plant can write down its own constraints — they live in the interlock list, the HAZOP minutes and the board operator's head. |
| **What PRANA does** | Derives the flexibility cost curve from cell physics, dispatches it against landed cost under a risk term, and uses an LLM to extract the constraint set that has never been written down. |
| **Who buys it** | Head of Energy / Works Manager at a chlor-alkali complex. Grasim, DCM Shriram, GACL, Chemplast Sanmar, Meghmani, Andhra Sugars, TGV SRAAC. |
| **Why they say yes** | Zero capex, zero production loss by construction, advisory-only to start, and paid out of verified savings. |

**Why chlor-alkali and not a refinery.** A refinery runs a captive power plant, so
its marginal cost of electricity is flat and the arbitrage does not exist; its air
separation unit is usually owned over-the-fence by an industrial gas company under
take-or-pay. A chlor-alkali plant has none of those problems: it buys from the
grid, it owns its cell house, and power *is* its raw material. **We tested the
refinery case and are reporting why it is the weaker one** — see §10.

---

## 5 · SYSTEM ARCHITECTURE

```
┌─ 1 · DATA ───────────────────────────────────────────────────────────┐
│ IEX DAM/RTM/G-DAM 15-min, Maharashtra  ·  152,542 blocks cached      │
│ MERC tariff order → ToD, wheeling, CSS, demand charge                │
│ Plant historian → rectifier kW, cell voltage, current, tank level    │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 2 · TWIN  (the novel object) ▼──────────────────────────────────────┐
│ V = V0 + k·i   and   q ∝ i   ⇒   P(q) = αq + βq²   (convex, derived) │
│ SEC falls on turn-down (NPC eqn) · caustic tank = state of charge    │
│ H2-in-Cl2 floor at 40% load = HARD SAFETY BOUND, never a soft cost   │
│ CHLORINE BALANCE: Cl2 unstorable ⇒ consumer's turndown is the REAL   │
│   floor (70%), not the cell's interlock. Bleach = sink of last resort │
│ Membrane life charged per unit of setpoint movement                   │
│ ⇒ OUTPUT: φ(ΔMW, Δt) in ₹/MWh — the flexibility cost curve            │
│ 16 tangent hyperplanes, linearization error 0.025%                    │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 3 · FORECAST ───────────────▼───────────────────────────────────────┐
│ LightGBM quantile q10/q50/q90, 500 trees each                        │
│ lead feature: same-block day-ahead price (known 12–36 h ahead)       │
│ + out-of-sample conformal widening (coverage 69.7% → 76.2%)          │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 4 · DECISION ───────────────▼───────────────────────────────────────┐
│ min (1−λ)·E[cost] + λ·CVaR₉₅ + demand charge                          │
│ s.t. cell envelope · caustic inventory · ramp · contract demand      │
│      · agent-supplied constraints                                     │
│ CBC · solves in 0.3 s · deviation offered and never used              │
└──────────────────────────────┬───────────────────────────────────────┘
┌─ 5 · AGENT & UI ─────────────▼───────────────────────────────────────┐
│ elicit()  SOP / interlocks / operator speech → typed constraints      │
│ explain() solver's binding constraints → plain language               │
│ perturb() "cell 3 rectifier is down till 20:00" → re-solve            │
│ Streamlit console · sign-off gated · L1 advisory → L2 supervised      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6 · MVP — WHAT IS ALREADY BUILT

**Status: running, tested, and backtested.** ~3,000 lines of Python.

| Component | Status | Evidence |
|---|---|---|
| Market data pipeline | ✅ **done** | 152,542 blocks, 1,588 complete days, cached |
| Chlor-alkali twin | ✅ **done** | φ curve, SEC falls on turn-down (NPC), lin. error 0.025% |
| Landed-cost engine | ✅ **done** | ToD, wheeling, CSS, duty, demand charge + ratchet |
| Quantile forecaster | ✅ **done** | MAE 1,072 vs 3 baselines; conformal calibration |
| Stochastic MILP | ✅ **done** | CVaR₉₅, CBC, 0.3 s/day |
| Constraint agent | ✅ **done** | structured outputs + deterministic fallback |
| Independent verifier | ✅ **done** | re-simulates true nonlinear physics |
| 120-day backtest, both modes | ✅ **done** | see §8 |
| 5-tab Streamlit console | ✅ **done** | `streamlit run app.py` |
| Terminal fallback demo | ✅ **done** | `python run_demo.py` |
| Regression tests | ✅ **31 passing** | each pins a claim in this document |

### Datasets

| Data | Source | Access |
|---|---|---|
| IEX DAM / RTM / G-DAM, 15-min | `iexindia.com` market-data pages | plain HTML form POST; already scraped and cached |
| Tariff stack | **MERC Case 75 of 2025, post-remand** (primary PDF) | ✅ **VERIFIED** — demand charge ₹650/kVA/mth, energy ₹8.44/kVAh, ToD Table 8. Open-access surcharges remain tagged placeholders. |
| Deviation settlement | WRPC weekly DSM files | already audited, 133,056 blocks |
| Plant historian | OPC-UA / PI / IP.21 | not used — twins are archetypes (stated openly) |

### Models

| Model | Type | Input → Output |
|---|---|---|
| Process twin | First-principles ROM, convex quadratic from cell voltage law | production rate → power, inventory, φ(ΔMW, Δt) |
| Price forecaster | **LightGBM quantile regression**, α = 0.10/0.50/0.90, 500 trees | 15 causal features → 96-block price distribution |
| Dispatcher | **Stochastic MILP + CVaR₉₅** (Rockafellar–Uryasev), CBC | prices + twin envelope → 96-block setpoint schedule |
| Constraint agent | **LLM with structured outputs** (JSON schema), provider-configurable | SOP text / operator speech → typed constraints |

> **Why LightGBM and not an LSTM:** gradient boosting is the strong baseline on
> tabular electricity-price data and trains in minutes — and the forecast is
> worth only 8% of the value (§8), so spending the build on a deep model would
> optimize the least important lever. Say this if asked; it shows judgement.

### The three things worth doing with your remaining hours

1. ~~Verify the MERC numbers~~ — **done.** Demand charge, energy charge and the
   full ToD table are now taken from the operative post-remand order and pinned
   by tests. Three corrections came out of it (§13). Only the open-access
   surcharges remain placeholders.
2. **Rehearse the demo six times**, especially the slider moment and handing a
   judge the keyboard.
3. **Make ten slides.** Content is in §11.

*Do not write new code today.* You have more working software than any other team
will have; the marginal hour is worth more on the pitch.

---

## 7 · DEMO FLOW — WHAT THE JUDGES SEE

**Five minutes. Runs on a laptop, offline, no internet needed.**

| Time | What happens | The line |
|---|---|---|
| 0:00 | RTM price by hour, FY22-23 vs FY26-27, on screen | *"This is settled money, not a forecast. Midday collapsed to ₹1.5/kWh. Evening hits the ₹10 cap."* |
| 0:40 | Photo of a cell house | *"Everyone says build 411 GWh of batteries. This plant already owns 1,410 megawatt-hours. It's just stored as caustic soda."* |
| 1:20 | **Tab 2 — the flexibility cost curve** | *"V equals V-nought plus k-i. Faraday's law. Power is quadratic in production — I didn't assume that convexity, electrochemistry gives it to me. And specific energy **falls** as it turns down — that's the Government of India's own published cell equation, not my assumption. This is the one process in India that is paid to turn down."* |
| 2:10 | **Tab 1 — live solve on 12 July 2026**, a real day: RTM ₹1/MWh at 13:00 → ₹10,000/MWh at midnight. Watch the cell house load the caustic tank at midday and coast through the evening. Production unchanged. | *"Zero point three seconds. Ninety-six blocks. Production output identical."* |
| 2:50 | **THE MONEY SHOT.** Two schedules for the same day, side by side: one optimized against the exchange price, one against the landed bill. **Both settled at the real bill.** | *"Optimize on the exchange price and you leave 0.95% on the table here — about ₹5 crore a year. On a refinery it's 3.3%. That is the cost of treating the market clearing price as the cost of power."* |
| 3:30 | **Tab 3 — hand a judge the keyboard.** They type *"Rectifier B is down till 20:00."* Agent parses it, flags it for sign-off, re-solves, names the binding constraint. Then show the sentence it **refused** to encode. | *"It proposes. A human accepts. And when it can't be sure, it says so instead of guessing."* |
| 4:20 | **Tab 4 — 120-day replay.** ₹0.133/kWh net of wear, **violations: 0**, and 13 loss-making days we show rather than hide. Then the deviation slide. | *"We gave the optimizer the deviation lever. It declines to use it in every single solve — because the DSM rate is max of day-ahead and real-time, and we audited 133,056 blocks to know that."* |
| 4:50 | **Tab 5 — board view**, then the Oil India slide | *"Every electrolyser the Green Hydrogen Mission builds is this same machine. Fifty-seven gigawatts of it by 2030. Oil India is building one at Jorhat right now."* |

**Backup:** if Streamlit fails, `python run_demo.py` prints every number in the
same order. Test it on the venue laptop.

---

## 8 · ECONOMIC IMPACT — REAL NUMBERS

### One plant (700 TPD caustic, ~79 MW connected)

120 consecutive delivery days to 2026-08-06, settled at realised prices, every
schedule independently verified.

| Metric | With forecast error (**quote this**) | Perfect foresight |
|---|---|---|
| Saving per kWh of total plant load | **₹0.133** | ₹0.174 |
| Saving per day | **₹2.51 lakh** | ₹3.31 lakh |
| **Annualised** | **₹9.17 crore** | ₹12.07 crore |
| As % of the electricity bill | 1.53% | 2.01% |
| Days worse than doing nothing | **13 of 120** | 0 |
| Constraint violations | **0** | **0** |
| Solve time per day | 0.6 s | 0.6 s |

**These numbers are net of every cost the flexibility creates**, which is the
part most such studies omit:

| Over the 120 days | ₹ lakh |
|---|---|
| Electricity avoided (gross) | 378.3 |
| *less* membrane life consumed by setpoint movement, chlorine diverted to the bleach plant, and the extra kVAh from power-factor droop on turn-down | **−76.8** |
| **Net saving** | **301.5** |

**One fifth of the gross saving is paid straight back to the plant.** A model
that does not charge these is not conservative, it is wrong.

| | |
|---|---|
| Virtual battery (**deliverable**) | **21.8 MW / 748 MWh** |
| Equivalent BESS capex displaced | **₹450–820 crore** at ₹0.6–1.1 cr/MWh (VGF-implied low end to Ember's ~$125/kWh project cost). Directional only: a process buffer shifts its own load and cannot export to the grid. |
| Capex required | **zero** |
| Production impact | **none** — product output unchanged by construction |

The battery is quoted at the **deliverable** floor of 70% of design, set by the
chlorine consumer — not at the cell's 40% safety interlock. Quoting the interlock
would have claimed 41 MW / 1,410 MWh, and roughly half of that battery does not
exist.

**The cost of optimizing on the wrong price.** Two schedules for the same days,
one built against the exchange clearing price and one against the landed bill,
**both settled at the landed bill**:

| Site | MCP-optimized | Landed-optimized | Penalty |
|---|---|---|---|
| Chlor-alkali | ₹7.196 cr | ₹7.128 cr | **0.95%** ≈ ₹5.0 cr/yr |
| Refinery | ₹9.167 cr | ₹8.862 cr | **3.33%** ≈ ₹22.3 cr/yr |

*(5 high-spread days; the % is the robust figure, the annualisation is indicative.)*

This replaced an earlier demo that toggled the demand charge and watched the peak
move. **That test was invalid** — with the demand charge zeroed the peak variable
is unpriced, so the solver leaves it anywhere and the difference is degeneracy,
not behaviour. Measuring the rupee penalty on a commonly-settled bill is the
correct experiment, and it is now `mcp_only_penalty()` in `prana/backtest.py`.

### The assumption that decides the whole project, and what happens when it moves

Chlorine is made stoichiometrically with caustic and **cannot be stored in bulk**
— it is a Schedule-3 substance under the MSIHC Rules, PESO-licensed, and
deliberately held at minimum inventory. So the cell house can only turn down if
the chlorine *consumer* turns down with it. The consumer's turndown, not the
cell's safety interlock, is the real floor. It is the single most sensitive
number in the model and it is plant-specific, so we swept it (45 days, forecast
error, every schedule verified):

| Chlorine consumer holds | ₹/kWh | ₹ cr/yr | Loss-making days | Violations |
|---|---|---|---|---|
| 60% of design draw | 0.159 | 10.99 | 3 | 0 |
| **70% (our base case)** | **0.158** | **10.90** | 3 | 0 |
| 80% of design draw | 0.151 | 10.45 | 1 | 0 |
| 90% of design draw | 0.108 | 7.46 | 1 | 0 |

**The value is nearly flat from 60% to 80%, and 96% of it survives at 80%.**
That is the important finding, and it is not the obvious one: the money does not
come from shedding *deeply*, it comes from shedding at the *right time* and from
managing peak billing demand. A plant whose chlorine consumer can only turn down
to 80% still captures ₹10.4 crore a year. Only at 90% does the value break.

**What this means for a buyer:** you do not need a flexible chlorine consumer to
buy this. You need a *slightly* flexible one. That widens the addressable market
from "plants with merchant chlorine offtake" to "most of the sector."

### What the engineering review changed

An engineering panel — process, chemical, electrical, mechanical — was asked to
break this. Four objections were real, all four are now in the model, and they
cost us **29% of the headline**:

| Objection | Status | What it did to the number |
|---|---|---|
| **The chlorine balance.** Cl₂ is unstorable, so the downstream consumer's turndown is the binding floor. Encoding it as one `x_min` on the cell "hides an entire plant behind one number." | **Fixed.** Explicit co-product balance with the consumer's min/max take and a capacity-limited bleach plant as sink of last resort, priced at the margin it destroys. | Turn-down floor **40% → 70%**. Virtual battery **1,410 → 748 MWh**. |
| **Membranes are consumed by movement, not runtime.** Charging zero for a setpoint change makes flexibility look free. | **Fixed.** Every setpoint change is charged per tonne/h moved, inside the objective, plus a daily movement budget standing in for the control room's "don't move it all day." | Part of the −₹76.8 lakh. |
| **MERC bills kVAh, not kWh, and rectifier power factor droops on turn-down.** | **Fixed.** Load-dependent power factor, charged block by block at that block's own landed rate. | Small — because the turn-down lands in cheap hours. Measured, not assumed. |
| **A single-train outage is a derate, not a trip.** | **Fixed.** Four rectifier trains: losing one is −25%, not a drop to minimum load. | Made outage re-solves feasible again instead of spuriously infeasible. |

Two further bugs surfaced while fixing those, both now closed: a retail-supplied
site could "deviate" and settle at market DSM rates (a category error that routed
the entire plant through deviation), and the terminal-inventory guard was hard
rather than soft, which turned every genuine multi-hour outage into a false
infeasibility. There are **45 regression tests**; each of the four fixes above has
one that fails if the constraint is ever removed.

### The question an academic will ask: what does a simple rule already capture?

A production-neutral time-of-day rule — shed through the 17:00–24:00 slab, run
at the deliverable maximum in the solar window, depth solved so the day's tonnes
balance — settled on **identical** terms including the terminal-inventory charge:

| 60 days, forecast error | ₹/kWh | vs flat |
|---|---|---|
| PRANA | **0.149** | ₹283,219/day |
| Competent ToD rule | 0.027 | ₹50,881/day |
| **Rule captures** | **18%** | PRANA's incremental value **₹8.48 cr/yr** |

The rule loses money on **15 of 60 days**; PRANA loses on far fewer. The reason
is structural: a fixed rule must stay production-neutral *within* the day, which
caps its shed at ~91% of design, while the MILP moves inventory across the day
and responds to the price *inside* the tariff slab — where ₹2.31/kWh of spread
sits that the four-step ToD tariff prices at zero.

**Two numbers to be straight about.**

*The thirteen bad days.* A single-asset site with a hard 70% floor has no second
lever when the price forecast is wrong. The refinery case had three assets with
complementary ramp rates and a make-vs-buy hydrogen option, and posted zero bad
days. **Portfolio diversity buys robustness** — which is an argument for the
platform, and the honest reason to add a second flexible asset at each site.

*The haircut is 22%, not the refinery's 8%.* Same reason. Forecast skill matters
more when you have only one lever. Report both.

**So why is chlor-alkali still the right flagship, when its ₹/kWh is lower than
the refinery's ₹0.260?** Because ₹/kWh is the wrong denominator for a buying
decision:

| | Refinery | Chlor-alkali |
|---|---|---|
| Saving | ₹21.2 cr/yr | ₹9.17 cr/yr |
| Power as share of cash cost | small — electricity is a minor part of refining opex | **55–70%** |
| Saving as share of gross margin | ~0.7% of GRM | a **visible line** on the P&L |
| Buys its power from the grid? | No — **captive power plant** | **Yes** |
| Owns the flexible asset? | Often not — ASU is over-the-fence, take-or-pay | **Yes** |
| Will the plant head take the meeting? | No | **Yes** |

The refinery saves more rupees and will never sign. The chlor-alkali plant saves
fewer rupees on something that is 60% of its cost base, owns the asset, and buys
from the market. **Deployability, not ₹/kWh, is what makes this the flagship.**

### The sector, with the arithmetic shown

```
Indian caustic soda capacity   ≈ 6.0 MTPA
× specific energy               2,300 kWh/t (membrane cell)
× utilisation                   85%
=                               11.7 TWh/year  ≈ 1.34 GW of rectifier load
× ₹0.133/kWh                 →  ≈ ₹155 crore/year of avoidable cost, sector-wide
```

### The 2030 market — the same twin, 21× bigger

```
National Green Hydrogen Mission   5 MMTPA by 2030
× 50 kWh/kg (alkaline)         =  250 TWh/year
at 50% CUF                     →  ≈ 57 GW of electrolysers
```

**An electrolyser is a chlor-alkali cell with a different membrane.** Same voltage
law, same convex power curve, same φ derivation, same twin — it is already
implemented in this repo as a second archetype. Every electrolyser India builds
for the Hydrogen Mission is a grid battery that nobody is currently planning to
dispatch.

---

## 9 · THE OIL INDIA CONNECTION — do not skip this slide

You are pitching to an oil company with a chlor-alkali flagship. Close the loop
explicitly, in three sentences:

1. **Oil India commissioned a green hydrogen plant at Jorhat.** That electrolyser
   is electrochemically the same machine as the cell house in this demo — the
   twin in `prana/twins.py` already models it.
2. **NRL's expansion needs hydrogen**, and the price-duration analysis on this
   panel says the LCOH minimum sits near 6,000 operating hours, not 8,000. A DPR
   written at 90% CUF is mis-sizing the plant. That is an actionable correction
   to a decision being taken now.
3. **OIL's renewable portfolio faces the mirror image** of this problem — the same
   collapsing midday price that makes flexibility valuable makes solar revenue
   fall. The same panel data measures both.

> *"We are showing this on chlor-alkali because that is where the megawatts and
> the economics are today. It is the same machine you are building at Jorhat, and
> the same machine India will build 57 gigawatts of by 2030."*

---

## 10 · WHY THIS WILL WIN

**Innovation.** The convexity is *derived from Faraday's law and the cell voltage
law*, not assumed — every other flexibility model in this space parameterises a
curve. The flexibility cost curve φ(ΔMW, Δt) is a first-class object no Indian
plant currently has for itself. And the LLM is load-bearing rather than
decorative: it solves the actual bottleneck, which is that the constraint set has
never been written down.

**It runs.** 152,542 real settlement blocks, a 120-day replay with real forecast
error, 31 passing tests, 0.3-second solves. Most teams will demo a slide deck.

**It is honest, and honesty is differentiating.** Savings are net of everything.
The counterfactual is how the plant actually runs today, not a strawman. Every
regulatory placeholder is tagged in the source. **And we will tell the panel which
of our own use cases is weak and why** — the refinery case, killed by captive
power and over-the-fence ASU contracts. A panel that has heard nine teams
overclaim will remember the one that didn't.

**Safety is designed in, not bolted on.** The H₂-in-Cl₂ limit is a hard bound in
the optimizer, not a penalty term. PRANA's feasible set is a strict subset of the
plant's licensed operating envelope. The agent proposes; a human signs off. No
interlock is ever bypassed. Say this before anyone asks.

**It is a business.** Zero capex, gainshare-compatible, a constraint library that
compounds with every deployment, and a natural path to a virtual power plant the
moment India opens a flexibility market — with the 57 GW hydrogen build arriving
exactly as that happens.

---

## 11 · TEN SLIDES

| # | Slide | The one thing it must land |
|---|---|---|
| 1 | Title | *"The cell house is the battery."* |
| 2 | The price shape breaking | 1.47 → 3.53, real settled data, FY26-27 labelled Apr–Aug |
| 3 | Who loses money | Power = 55–70% of caustic cash cost, flat load into a 3.5× market |
| 4 | The insight | 411 GWh to build vs 748 MWh already sitting in one tank, deliverable |
| 5 | **The physics** | V = V₀ + k·i ⇒ P quadratic (NPC India, p.28). SEC falls on turn-down. **Derived, not assumed** |
| 6 | **The flexibility cost curve** | The object no plant has. ₹27–117/MWh shifted |
| 7 | Architecture | Twin → forecast → MILP → agent, one diagram |
| 8 | **MCP-optimized vs landed-optimized** | Both settled at the real bill. ₹5 cr/yr gap here, ₹22 cr/yr on a refinery |
| 9 | 120-day proof | ₹0.133/kWh net of wear, 0 violations, 0 MW deviation, 13 bad days shown |
| 10 | Oil India + the ask | Jorhat → 57 GW by 2030. One plant, 90 days, advisory mode |

---

## 12 · FINAL CHECK

> ### "Would a plant actually use this in 6 months?"

## ✅ YES — for a chlor-alkali plant. Here is precisely why.

**Because the money is material to *them*.** Power is 55–70% of caustic cash cost.
₹9.17 crore a year is not a rounding error on a rounding error — it is a visible
line on the works manager's P&L. This is the test the refinery case failed: there,
₹21 crore was 0.7% of refining margin and nobody senior would spend attention on
it.

**Because they already do this badly by hand.** Chlor-alkali plants in Gujarat and
Tamil Nadu already avoid ToD peak hours manually. We are not asking them to adopt
a new behaviour; we are asking them to do an existing behaviour optimally. That is
a far shorter conversation.

**Because month one requires nothing from their control system.** L1 is advisory:
a nightly historian export, an emailed schedule each morning, and a comparison
against what they actually did at realised prices. No OPC-UA write, no Management
of Change, no HAZOP revalidation, no cyber review. Those are 12–24-month
conversations in an Indian plant and we deliberately do not need them to start.

**Because the safety story is already handled.** The H₂-in-Cl₂ limit is a hard
bound. The cell house is never de-energised. The agent requires human sign-off.
Every schedule is verified against the true nonlinear physics before anyone sees
it — 120 days, zero violations.

**Because the commercial terms carry no risk.** Free shadow mode, then 20% of
verified savings on an IPMVP baseline. No capex, no committee, no capital budget
cycle.

### The 90-day pilot to propose on stage

> **One chlor-alkali plant. 90 days. Advisory only. Nightly historian export.**
>
> - **Weeks 1–4** — fit the cell-house twin to their historian. Deliver
>   φ(ΔMW, Δt): *the number they have never had about their own plant.*
> - **Weeks 5–12** — shadow mode. Recommended profile each morning; compare
>   against actuals each evening at realised prices.
> - **Success metric, agreed up front** — ≥3% reduction in landed power cost
>   versus their own actuals, with zero product-spec excursions and zero
>   approaches to the H₂-in-Cl₂ limit.
> - **Cost to them: zero.** 20% of verified savings if it works.

**What would make us wrong,** and say it: if real membrane cells tolerate less
cycling than the published guidance suggests, the ramp limit tightens and the
saving falls. That is exactly what the 90-day advisory pilot is designed to find
out — cheaply, and without touching a control system.

---

## APPENDIX · WHAT CHANGED FROM THE EARLIER VERSION, AND WHY

An expert review panel — refinery operations, plant management, pipeline
operations, and strategy — rejected the original refinery-and-pipeline targeting.
Three findings, all of which we accepted:

1. **Refineries run captive power plants.** Marginal electricity cost is roughly
   flat, so the intraday arbitrage does not exist for them. Our model had only
   exchange and DISCOM tariff modes, neither of which describes a refinery.
2. **The air separation unit is usually not the refinery's to flex.** It is
   commonly build-own-operate by an industrial gas company under take-or-pay, and
   the liquid tank is contracted outage cover, not free storage.
3. **Slowing a waxy Assam crude pipeline is dangerous**, and throughput is set by
   shipper nominations under PNGRB tariffs, not by an optimizer. Our twin modelled
   power and tank level but not *temperature* — the variable that actually
   constrains that asset.

**We changed the target industry rather than defending the pitch.** The engine did
not change; only the twin it is pointed at. That is itself the argument for the
platform — and it is worth saying on stage if anyone asks how transferable this is.

---

## 13 · WHAT VERIFYING THE MERC ORDER CHANGED

The tariff figures are no longer placeholders. They are read from **MERC Order,
Case No. 75 of 2025 (post-remand proceedings)** — HT I (A) HT-Industry, EHV,
FY2026-27 — and pinned by regression tests so they cannot silently drift.

**First, the provenance matters.** There are two orders in circulation. The
25-June-2025 order was **quashed by the Bombay High Court**; the operative
document is the post-remand order. Anyone quoting the earlier one is quoting a
quashed instrument. *Worth one sentence on stage — it is the kind of detail that
establishes you actually read the source.*

### Three things the primary order says that a summary would get wrong

| # | What we had assumed | What the order actually says |
|---|---|---|
| 1 | Peak ToD window 17:00–**22:00** | **17:00–24:00** — a **7-hour** peak window, not 5 |
| 2 | A night rebate of ~10% | **The night rebate was REMOVED** (para 18.13): rebating at night is "inconsistent with the objective of encouraging load shifting to solar hours." 00:00–09:00 is now flat 0% |
| 3 | A single solar rebate | **Seasonal**: −15% Apr–Sep, −25% Oct–Mar in FY2026-27, escalating to −20%/−30% from FY2028 |

Plus a unit trap: energy charges for loads ≥20 kW are in **₹/kVAh, not ₹/kWh** —
about 2% more per kWh consumed at a 0.98 power factor. The order carries its own
footnote saying so.

### The verified figures, and the multi-year trajectory

| Year | Demand charge | Energy charge |
|---|---|---|
| FY2025-26 | ₹600/kVA/mth | ₹8.68/kVAh |
| **FY2026-27** | **₹650/kVA/mth** | **₹8.44/kVAh** |
| FY2027-28 | ₹700 | ₹8.23 |
| FY2028-29 | ₹730 | ₹7.52 |
| FY2029-30 | ₹750 | ₹7.45 |

*(EHV. A 33 kV connection adds ~₹0.81/kVAh wheeling.)*

**Two things this hands you for free.**

*The demand charge rises 15% over four years while the energy charge falls 12%.*
Flexibility therefore gets **more** valuable, not less, on the regulator's own
published trajectory. That is a forward-looking argument you can make from a
primary source rather than a forecast.

*The regulator is explicitly trying to cause exactly the behaviour PRANA
automates.* Para 18.13 removes a night rebate **because** it competes with
shifting load into solar hours. A −25% solar rebate and a +20% evening charge is
a 45-point spread the regulator built on purpose. PRANA is not arbitraging
against policy; it is the tool that lets an industrial consumer respond to it.

### Effect on the headline

Correcting the demand charge from ₹590 to the verified ₹650 moved the 120-day
result from ₹0.193 to ₹0.187/kWh and from 7 loss-making days to 10.

The engineering review then cost a further 29%: modelling the chlorine balance,
membrane cycling, power-factor droop and single-train derates took the result to
**₹0.133/kWh** and 13 loss-making days. Reported, not hidden. Everything in §8 is
the fully corrected run.

**Still placeholders** (tagged in `prana/config.py`): the open-access surcharges —
wheeling, cross-subsidy, additional surcharge, SLDC — which govern the EXCHANGE
route. The additional-surcharge waiver in particular flips the sign of the
open-access case and remains unverified.
