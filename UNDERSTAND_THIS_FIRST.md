# UNDERSTAND THIS FIRST

*Written for you, not for the panel. Read this end to end. It assumes you know
nothing about the project and explains every word.*

---

# PART 0 — IS THIS REAL OR IS IT HYPOTHETICAL?

**Both. And you need to know exactly which part is which, because that is the
question that will decide whether you survive the panel.**

Here is the honest breakdown. Nothing in this table is spin.

### Tier 1 — REAL. A judge can verify this on their phone, in the room.

| Thing | Why it is real |
|---|---|
| **152,542 electricity prices** | These are actual settled prices from the Indian Energy Exchange, Maharashtra region, every 15 minutes from April 2022 to August 2026. Real money changed hands at these prices. They are in `data/market_15min.csv`. |
| **The MERC tariff** | ₹650 per kVA per month, ₹8.44 per kVAh. This is on **page 100** of a real government order (MERC Case 75 of 2025, dated 25 March 2026). Anyone can download it. I opened it and read the table. |
| **₹22,109 per MW per day** | This is just division: ₹650 ÷ 0.98 × 1000 ÷ 30 days. Nothing to dispute. |
| **The physics equation** | `U = U₀ + k·i` — cell voltage rises with current. This is printed on page 28 of a Government of India (National Productivity Council) manual. Not my idea. Theirs. |
| **The software runs** | 48 automated tests pass. Fresh copy on a clean machine runs in 22 seconds. |

### Tier 2 — REAL METHOD, applied to a plant that DOES NOT EXIST.

The optimiser is correct. The maths is checked. **But there is no chlor-alkali
plant.** The "700 tonne-per-day, 67 MW plant" is invented — a made-up but
realistic example, like a case study in a textbook.

### Tier 3 — EDUCATED GUESSES.

How fast the plant can change load, how big its storage tank is, how far the
chlorine customer can turn down. **We have no source for any of these.** They
are listed with that admission in `ASSUMPTIONS.md`.

### So what does "₹9.17 crore per year" actually mean?

> **Real prices × real tariff × real physics equation × an INVENTED PLANT ×
> GUESSED plant parameters = ₹9.17 crore.**

It is a **simulation**, not a measurement. Nobody has saved ₹9.17 crore. Nobody
has saved one rupee.

**Is that fatal? No — if you say it.** Every feasibility study ever written
works exactly this way. Engineers model plants that don't exist yet all the
time. The sin is not modelling. **The sin is presenting a model as a
measurement.**

You will be fine if you say: *"This is a modelled archetype on real prices."*
You will be destroyed if you say: *"We save ₹9.17 crore."*

### About me, since you raised it

You are right to be suspicious. In building this I made real mistakes:

- I built a comparison test **wrong twice** — the first version made our own
  product look 382% better than it is.
- I told you a battery cost figure was wrong; **I was wrong, not the figure.**
- I put a claim on the slides ("efficiency is best at 53% load") that the very
  physics document we rely on **contradicts**. We removed it.

Each one was caught by checking. **The parts I trust most are the ones where I
opened a document or ran code.** The parts to be careful with are anything I
said without doing either. That is why every number now traces to a file.

---

# PART 1 — THE PROBLEM, IN PLAIN LANGUAGE

Read this five times. If you can say it in your own words, you can survive the
first two minutes.

**Electricity in India used to cost roughly the same all day. It doesn't
anymore.**

Because of solar. In the middle of the day, so much solar power floods the grid
that prices collapse — sometimes to almost zero. In the evening, when the sun
sets but everyone switches on lights and ACs, prices spike.

On our data: the evening is now **3.5 times more expensive** than midday. Four
years ago it was 1.8 times.

**Meanwhile, a factory runs at the same load all day.** It buys expensive
evening power and ignores nearly-free midday power. Nobody planned this — it is
just how factories have always run.

**So why doesn't the factory just shift its load to midday?**

Three reasons:

1. **It doesn't know what shifting costs.** Slowing a plant down and speeding it
   back up wastes energy. Nobody has calculated how much. So the safe answer is
   "don't touch it."
2. **The bill is more complicated than the market price.** There is a separate
   charge based on your single highest moment of demand all month. Shift load
   badly and you create a new peak that costs more than the energy you saved.
3. **Nobody can write down the plant's rules.** "We can't go below X because of
   a safety interlock" lives in an operator's head, not in a computer.

**Our project addresses all three.**

---

# PART 2 — EVERY TECHNICAL WORD, EXPLAINED

## "Physics model" (we call it a digital twin)

**What it is:** a small set of equations that predicts how much electricity a
machine uses at any production rate.

**Analogy:** a car. At 40 km/h it sips fuel. At 140 km/h it guzzles — and not
double, more like four times. Fuel use is not proportional to speed; it curves
upward. Our "physics model" is that curve, for a chemical plant.

**Why we needed it:** to answer "what does it cost to slow down for 4 hours?"
you must know the shape of that curve. Without it you are guessing.

**Why ours is credible:** we did not invent the curve. A Government of India
manual publishes the underlying equation. In an electrolysis cell, voltage rises
as current rises (`U = U₀ + k·i`), and production is proportional to current. Put
those together and power **must** be curved (specifically, quadratic). We derived
it rather than assumed it.

**The one-line version for the panel:**
> *"The physics model tells us what flexibility costs in kWh. We didn't assume
> the shape — it follows from a cell-voltage law the Government of India
> publishes."*

## "Stochastic" model

**What it means:** *stochastic* just means **"accounting for uncertainty."** The
opposite is *deterministic*, which means "pretending you know the future
exactly."

**Why we needed it:** the plan for tomorrow depends on tomorrow's prices, and we
don't know them. We forecast them — but a forecast is never exactly right.

A deterministic model says: *"the price at 6pm will be ₹8."* Then reality is ₹12
and your plan is wrong.

A stochastic model says: *"the price at 6pm will probably be ₹8, but could be ₹4
or ₹15."* It then builds **one plan that works reasonably well across all three
possibilities**.

**How we do it:** the forecast produces three prices for each moment — a low
case, a middle case, and a high case (called q10, q50, q90). The optimiser finds
the single schedule with the best result averaged across all three, with extra
weight on avoiding the bad case.

**The one-line version:**
> *"We don't optimise against a price forecast. We optimise against a range of
> prices, so the plan doesn't fall apart when the forecast is wrong."*

## "MILP" — Mixed-Integer Linear Program

**What it is:** a standard, decades-old mathematical method for finding the best
plan when you have many choices and many rules. Airlines use it for crew
rostering. Refineries use it for blending. It is not exotic and it is not AI.

- **Linear** — the equations are straight lines (which is why we approximate our
  curve with straight lines, see below).
- **Integer** — some decisions are yes/no, not "a bit of both."
- **Program** — an old word for "plan." Nothing to do with programming.

**What ours decides:** for each of the 96 fifteen-minute blocks in a day, what
production rate should the plant run at? That is 96 decisions, all connected
(what you do at 2pm affects what's possible at 6pm), all subject to rules.

**Why not just a simple rule?** We tested exactly that. See Part 6.

## "Tangent hyperplanes" (only if asked)

Our power curve is curved. MILP only handles straight lines. So we approximate
the curve with 16 straight lines that sit just underneath it — like drawing a
curve with a ruler in 16 short strokes. Error: 0.025%.

## "CVaR" (only if asked)

A way of saying "don't just optimise the average, also protect against the worst
5% of outcomes." A risk setting.

## "Landed cost" — **this is your most important term**

**Market price** = what electricity costs on the exchange.
**Landed cost** = what it *actually costs you at your factory meter* after every
charge is added: time-of-day multipliers, wheeling, cross-subsidy surcharge,
electricity duty, and the demand charge.

**On our numbers, 46% of the bill is NOT the energy price.**

Every competing tool optimises the market price. That's 54% of the truth.

**The one-line version — say this on stage:**
> *"Your bill is not the exchange price. Roughly 46% of what you pay isn't
> energy at all."*

## "Demand charge" — **your single strongest fact**

You are billed not only for how much electricity you use, but for your **single
highest 15-minute peak** in the month. In Maharashtra that costs ₹650 per kVA per
month — which works out to **₹22,109 per MW of peak, per day**.

**Why it matters:** if you shift load into cheap midday hours, you may create a
new, higher peak — and that new peak can cost more than the energy you saved.
Tools that ignore this give actively harmful advice.

## "Chlor-alkali" — the example plant

A factory that runs electricity through salt water to make **caustic soda**
(used in soap, paper, aluminium) and **chlorine** (used in PVC, water treatment).

**Why we chose it:** electricity is 50–60% of its production cost — the most
electricity-hungry industry there is. It has storage tanks for caustic soda,
which act like a battery. And it buys from the grid.

## **Your own concern, and you were right**

You wrote: *"the chlor alkali may be used in other process so they dont want to
use it."*

**That instinct is correct, and it is the single most important constraint in
our model.** Chlorine is made at the same time as caustic soda — you cannot make
one without the other. And chlorine **cannot be stored** (it is dangerous and
tightly regulated). So it must be consumed immediately by a downstream unit.

**Which means: the plant can only slow down if the chlorine customer slows down
too.**

We model this explicitly. It is why our plant can only turn down to **70%** of
full rate, not 40% as the cell's own safety limit would allow. Your instinct
found the real constraint.

**And an independent research paper agrees with us.** Weigert et al. (2021),
whose model *is* validated on a real plant, wrote that the electrolysis "cannot
be operated flexibly by itself as storing chlorine is avoided in practice."
Same conclusion, reached separately.

**If a judge raises this, you say:**
> *"That's the binding constraint in our model, and it's why we cap the turndown
> at 70% instead of 40%. We also tested what happens if the chlorine customer is
> even stiffer — at 80% we keep 96% of the value. The money comes from shifting
> at the right *time*, not from shifting *deeply*."*

---

# PART 3 — WHAT WE ACTUALLY BUILT

Nine Python files. Here is what each one does, in one sentence.

| File | What it does |
|---|---|
| `data.py` | Loads the 152,542 real electricity prices and checks them for errors |
| `tariff.py` | **Turns a market price into what you actually pay** (the landed cost) |
| `twins.py` | The physics model — the curve of power vs production rate |
| `forecast.py` | Predicts tomorrow's prices as a low/middle/high range |
| `optimizer.py` | The MILP — decides the production rate for all 96 blocks |
| `agent.py` | Turns operator sentences into machine-readable rules |
| `backtest.py` | Replays 120 real days and **independently re-checks every schedule** |
| `plantdata.py` | Reads a real plant's energy sheet (built after you shared yours) |
| `app.py` | **The Streamlit demo** — 5 tabs |

**The most important one is `backtest.py`.** It does not trust the optimiser. It
takes the schedule and re-calculates everything from scratch using the exact
curved physics, re-checks every rule, and reports violations. Across 120 days it
found **zero**. That is why the result means something.

---

# PART 4 — WHERE THE DEMO IS, AND HOW TO RUN IT

**You have two demos. Both work. I tested both today.**

### Demo 1 — the Streamlit app (the visual one)

```bash
streamlit run app.py
```

Opens in your browser. Five tabs: Today, Twin, Agent, Backtest, Board. I
launched it today and it served correctly.

### Demo 2 — the terminal demo (your safety net)

```bash
python run_demo.py --site chloralkali
```

Prints every headline number in pitch order, in 22 seconds. **No internet, no
browser, no setup.** If the venue laptop or wifi fights you, run this instead.

### Demo 3 — the slide deck itself

`PRANA_DECK.html` — double-click it, opens in any browser, works offline. Slide
8 has an **Optimise** button that shows before/after with the real numbers.

**My advice: present from the deck (Demo 3), and keep the terminal (Demo 2) open
in a second window as proof it's real code.** Only open Streamlit if you have
time and confidence.

---

# PART 5 — WHERE THE MONEY COMES FROM

Three separate sources. Understand these and you can answer "where is the profit?"

**1. Buy energy when it's cheap.** Run harder at midday when power is ₹1–2/kWh,
run softer in the evening when it's ₹8–10/kWh. Same total production, cheaper
electricity.

**2. Don't create an expensive peak.** Every extra MW of peak costs ₹22,109/day.
The optimiser weighs this against the energy saving explicitly.

**3. Use the storage tank as a battery.** Make extra caustic soda when power is
cheap, store it, draw it down when power is expensive. Production to the customer
never changes.

### What we subtract — and this is what makes it credible

| Over 120 days | ₹ lakh |
|---|---|
| Energy saved (gross) | 378.3 |
| **less** membrane wear from changing setpoints, chlorine dumped, power-factor penalty | **−76.8** |
| **Net** | **301.5** |

**One fifth is paid straight back to the plant.** Most studies don't subtract
this. That is your credibility line.

**₹301.5 lakh over 120 days → ₹2.51 lakh/day → ₹9.17 crore/year.**

---

# PART 6 — "COULDN'T A SIMPLE RULE DO THIS?"

This is the question a professor will ask. **We tested it, and the answer is
strongly in your favour.**

We built the rule an experienced operator would write on a whiteboard: *run hard
during solar hours, back off during the evening peak, keep total production the
same.*

| 60 days, same rules for both | Saving/day | % of PRANA |
|---|---|---|
| **PRANA (full optimiser)** | **₹283,219** | 100% |
| Simple time-of-day rule | ₹50,881 | **18%** |

**The simple rule gets 18%. PRANA's extra value is ₹8.48 crore/year.** And the
simple rule *loses money* on 15 of 60 days.

**Why:** a fixed rule must balance production within the same day, which limits
how far it can back off (about 91% of full rate). The optimiser moves inventory
across days and reacts to the actual price *within* each tariff slab.

**Be honest about this too:** I built this comparison wrong twice before getting
it right. The first version forgot to charge the simple rule for inventory it
borrowed, and it appeared to beat PRANA by 382%. Admitting that is a strength.

---

# PART 7 — WHAT TO SAY WHEN YOU DON'T KNOW

You will be asked something you can't answer. **This is normal and survivable.**
The only fatal move is bluffing.

**Use these exact sentences:**

> *"I don't know. It's in the assumptions file as an open item — do you want me
> to walk you through what we do know?"*

> *"That's an assumption, not a measurement. It's listed with a stated direction
> of error."*

> *"I'd have to check the source before answering that."*

**Never say:** "the model shows..." about something you don't understand. Say
"the model assumes..." instead. Judges forgive gaps. They do not forgive bluffing.

### The three questions most likely to come

**"Which plant is this?"**
> *"It isn't one. It's an archetype built on published physics — a design case,
> not a site. The prices and the tariff are real; the plant is modelled. What we
> need to make it real is thirty days of read-only data from one plant."*

**"So you've never tested this on a real plant?"**
> *"Correct. The market and tariff half is real — four years of settled prices
> and a tariff order I can open to page 100. The plant half has never been fitted
> to a real historian. That's eight tags and thirty days, not a research
> programme."*

**"Why should we believe your numbers?"**
> *"Because they're lower than everyone else's. Published studies in this field
> report 4% to 10% savings. We report 1.53%, because we subtract equipment wear
> and because India's demand charge penalises exactly the peak that load-shifting
> creates."*

---

# PART 8 — MY HONEST ADVICE FOR TOMORROW

**You do not need to understand every line of code. You need to understand and
believe three things. Learn only these three.**

### Thing 1 — the real fact (needs no plant, cannot be attacked)

> Your electricity bill is not the exchange price. About 46% of it isn't energy.
> The demand charge alone is ₹22,109 per MW of peak per day — MERC Case 75 of
> 2025, page 100. Every industrial consumer in Maharashtra faces this whether
> they buy anything from us or not.

**This is 100% verifiable and it is your strongest 15 seconds.** Say it early.

### Thing 2 — the idea

> A chemical plant with a storage tank is already a battery. Its "charge" is
> inventory. We calculate what using it costs, from physics, and then decide when
> to use it based on what power actually costs at the meter.

### Thing 3 — the honest boundary

> The prices are real. The tariff is real. The physics equation is published by
> the Government of India. **The plant is a modelled archetype, not a real site.**
> We're asking for thirty days of data from one plant to close that gap.

**If you say only these three things clearly and answer "I don't know" honestly
to everything else, you will do better than most teams in that room.** A panel of
PSU engineers has sat through many confident presentations built on nothing. A
nervous presenter who says "this part is real, this part is modelled, and here's
what I'd need to prove it" is unusual, and they will notice.

### What NOT to do

- Do not claim a plant is saving money. None is.
- Do not defend the ₹155 crore sector number. Call it order-of-magnitude and move on.
- Do not pretend to understand the optimiser internals. Say "it's a standard
  scheduling method — the hard part was the tariff, not the maths."
- Do not open Streamlit if you're nervous. Use the deck and the terminal.

**One last thing.** The strongest thing about this project is not the ₹9 crore.
It is that we tested our own idea in a second sector, found it didn't work there,
and wrote that down. That behaviour is what a pilot partner looks for. Lead with
honesty and the technical gaps become forgivable.
