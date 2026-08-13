# PRANA — 6 minute speaker notes

**Read the FIX FIRST section before you present. Then rehearse the script twice
out loud with a timer. Nothing else matters.**

---

# ⚠ FIX FIRST — three corrections, ten minutes of work

### 1. Slide 8 has an arithmetic error a judge can catch instantly

The slide says the market price is **"about 60%"** of the bill, and that the
other charges are **"the other 46%"**.

**60 + 46 = 106.** That cannot be right, and someone in that room will add it up.

**Change "about 60%" to "about 54%."** The verified non-energy share is 46%, so
energy is 54%. One word, and the slide becomes airtight.

### 2. Slide 7 says "45 regression tests" — you now have **64**

Understating is safe, so this is not urgent. But if you show the repo, say 64.

### 3. Slide 9 says the forecast haircut is 22% — it is **23.6%**

(₹0.174 − ₹0.133) ÷ ₹0.174 = 23.6%. Either change it to 24% or say "about a
quarter." Do not say 22% if the slide is on screen and someone divides.

### Optional, only if you have time

Slide 8 quotes **₹22.3 cr/year** for a refinery. Slide 10 says *"No savings are
claimed for any unvalidated industry."* Those sit slightly awkwardly together.
It is defensible — the ₹22.3 cr is a *penalty for optimising on the wrong price*,
not a savings claim — but if asked, say exactly that. Do not defend it as a
refinery saving.

---

# THE 6-MINUTE SCRIPT

**Total 5:55. Sentences in bold are the ones that must survive if you rush.**
Say the words. Do not improvise — you have one slot.

---

## SLIDE 1 · Title — 20 seconds

> "Good morning. I'm Buddharatna Hingole.
>
> **Every plant in this room buys electricity. Almost none of them buys it at
> the right time.**
>
> PRANA answers one question: *how much electrical flexibility can an industrial
> plant safely afford to use?* Not how much can it shed — how much can it
> **afford**. The production objective never moves."

*Do not read the slide. Say those words and click.*

---

## SLIDE 2 · The market problem — 35 seconds

> "This is not a projection. This is 152,542 settled 15-minute prices from the
> Indian Energy Exchange, Maharashtra, since April 2022.
>
> **The evening now costs three and a half times what midday costs. Four years
> ago it was one and a half.**
>
> A fifth of the year clears below two rupees a unit. The evening repeatedly
> hits the ten-rupee cap.
>
> One honest note — that 3.53 is April to August only, India's peak months, so
> it is biased upward. It shows acceleration; it does not measure the full year.
> **The like-for-like number is 1.83 to 3.53, and that is still a doubling.**"

*The honest caveat is deliberate. It buys you credibility for the next four
minutes. Do not skip it.*

---

## SLIDE 3 · The industrial problem — 40 seconds

> "So why doesn't the plant just follow the price?
>
> **Because a price signal is not an operating instruction.**
>
> The market says two things: cheap, use more; expensive, use less. Both rules
> are completely ignorant of what the plant is making.
>
> The plant answers to safety, production, quality, inventory, ramp rate,
> equipment limits, and whoever is downstream waiting for product. **Electricity
> cost ranks below every one of those, and it always will.**
>
> The missing layer is the decision between them. PRANA is that layer. Every
> morning it returns one of three answers — shift, hold, or **do nothing**.
>
> **Do nothing is a valid and frequent result, and I will show you why that
> matters.**"

---

## SLIDE 4 · The general solution — 30 seconds

> "PRANA does not assume any process is flexible. It **discovers** whether it is.
>
> Refineries, chemicals, fertiliser, hydrogen — all candidates. **None of them
> is assumed flexible until its own physics says so.**
>
> Chlor-alkali is the one I have actually demonstrated, over 120 days, and I'll
> be precise about what that does and doesn't prove.
>
> Look at the diagram: four rectifier trains, one caustic tank. **The tank is
> the state of charge.** Run the cells hard on cheap power, coast through the
> evening on stored product. Tonnes shipped stay exactly the same."

---

## SLIDE 5 · The engineering core — 45 seconds

**This slide wins you Technical Soundness. Slow down here.**

> "Here is why this is engineering and not a dashboard.
>
> In an electrolysis cell, voltage rises with current — **V equals V-nought plus
> k-i**. That is the cell voltage law. Faraday's law says production is
> proportional to current.
>
> Put those together and electrical power is **necessarily quadratic in
> production rate**. I did not fit that curve. It falls out of the
> electrochemistry.
>
> **And it is not my equation — it is published by the National Productivity
> Council, a Government of India body, page 28 of their chlor-alkali manual.**
>
> Why does convexity matter? Because splitting production into a turn-down leg
> and a rebuild leg always burns more kilowatt-hours than running steady. **That
> excess is the true physical cost of flexibility.**
>
> One more thing — their published curve implies a coefficient between 0.30 and
> 0.45. **I use 0.21. I charge myself the larger round-trip loss than their own
> data requires.**"

---

## SLIDE 6 · The novel object — 40 seconds

> "That gives the plant a number it has never had.
>
> **Phi of delta-MW, delta-t.** What it costs *this specific process* to move
> its electrical load by so many megawatts, for so many hours, with output held
> constant.
>
> Three regimes. Low cost — the process can absorb the move for less than the
> market pays. Shift.
>
> High cost — membrane wear and diverted product eat the spread. Hold.
>
> **And infinity. The flexibility does not exist at that depth. Phi returns
> infinity rather than a number, and the answer is do nothing.**
>
> The virtual battery on the right is a *representation* of measured flexibility.
> **It is not a physical battery and it cannot export to the grid.** We don't
> assume a plant is a battery — we find what it can spare, then describe it in
> units the grid understands."

---

## SLIDE 7 · The system — 25 seconds

*Move fast. This is the slide to compress if you are behind.*

> "Five stages, all built and running. Real settled market data. The physics
> twin. A quantile price forecast — beats persistence, day-ahead price, and a
> seven-day mean. A stochastic optimiser that solves 96 blocks in a third of a
> second. And an agent that turns operator language into constraints.
>
> **Sixty-four tests. And every schedule is re-simulated against the true
> nonlinear physics before anyone sees it** — the optimiser does not get to mark
> its own homework."

---

## SLIDE 8 · Landed cost — 45 seconds

**This is your strongest, most unattackable claim. Land it clearly.**

> "Now the part most tools get wrong.
>
> **A plant does not pay the market clearing price. It pays the landed bill.**
>
> Market price, plus wheeling, plus surcharges, plus duty, plus a demand charge
> on your single highest peak of the month. **The market price is about 54% of
> what you actually pay. The other 46% is not energy at all.**
>
> That demand charge alone is **₹22,109 per megawatt of peak, per day** — and
> that is not my estimate. It's MERC Case 75 of 2025, post-remand order, page
> 100. I read the primary order.
>
> So we put the whole bill *inside* the optimisation instead of after it. Same
> physics, same days, only the price the optimiser was shown differs — and the
> gap is real money.
>
> **And the regulator is pushing the same way**: the demand charge rises 15%
> over four years while the energy charge falls 12%. Flexibility gets more
> valuable on the published trajectory, not less."

---

## SLIDE 9 · Proof — 55 seconds

**Your Prototype Maturity score lives here. Do not rush it.**

> "120 consecutive delivery days, replayed at real settled prices, against the
> plant's real counterfactual — one steady setpoint held all day, which is how
> these plants actually run.
>
> **13.3 paise per kilowatt-hour of total plant load. ₹9.17 crore a year. Zero
> constraint violations. Zero deviation.**
>
> Now the two numbers I want you to notice.
>
> **Thirteen of those 120 days came out worse than doing nothing. I report them.
> I did not remove them.** A single-asset site with a hard production floor has
> no second lever when the forecast is wrong.
>
> And the bar chart. Gross benefit was 378 lakh. **I subtract 77 lakh for
> membrane wear, chlorine diverted to bleach, and power-factor droop. One fifth
> of the gross, paid straight back.** A model that does not charge those is not
> being conservative — it is simply wrong.
>
> **And I want to be precise: this is a modelled archetype on real prices. The
> prices and the tariff are real. The plant is a 700-TPD design case, not a
> named site.**"

---

## SLIDE 10 · Scale and the ask — 40 seconds

> "One demonstrator. A platform.
>
> Refinery, chemicals, fertiliser, hydrogen — **no savings number is claimed for
> any of them. Each one earns its number the same way chlor-alkali did.**
>
> What I'm asking for is a 90-day advisory pilot. Weeks one to four, fit the twin
> to your historian — read-only, eight tags. Weeks five to eight, produce the
> flexibility cost curve, the number they have never had. Weeks nine to twelve,
> shadow mode: we produce a schedule every day, nobody executes it, and we
> compare against what the plant actually did.
>
> **Zero safety violations. Zero product-spec excursions. No production authority
> transferred at any point.**
>
> **PRANA does not tell a plant what equipment to sacrifice. It tells the plant
> what flexibility it can safely afford.**
>
> Thank you — I'll take your hardest question."

---

# HOW THIS HITS THEIR FIVE CRITERIA

Say this to yourself before you go in. Every criterion has a designated moment.

| Criterion | Where you score it |
|---|---|
| **Problem Relevance & Track Fit** | Slides 2–3. Real settled data, and a digital twin making a financial decision about a physical asset every 15 minutes — that *is* Digital Asset Management. |
| **Innovation / Novelty** | Slide 6. φ(ΔMW, Δt) is a number no Indian plant currently has for itself. |
| **Technical Soundness** | Slide 5 (physics derived, not fitted, from a Govt of India source) + slide 7 (64 tests, independent re-simulation). |
| **Industrial / Commercial Impact** | Slides 8–9. Landed cost + ₹9.17 cr, net of process costs. |
| **Feasibility & Prototype Maturity** | Slide 9 (120 days, 0 violations) + slide 10 (90-day pilot, no authority transferred). |

---

# Q&A — the questions you will actually get

**Answer in one or two sentences, then stop talking.**

### "Which plant is this? Have you deployed it?"
> "No. It's a modelled archetype — a 700 TPD design case built on published
> physics. The prices and the tariff order are real; the plant is not a named
> site. Closing that gap is thirty days of read-only historian data, which is
> exactly what the pilot asks for."

### "Why should a chlorine plant matter to Oil India?"
> "The demonstrator is chlor-alkali because it's the hardest test — power is
> 50-60% of its cost and it has an unstorable co-product. But the layer that
> matters to you is the landed-cost engine, and that's true for any HT
> industrial consumer, including every refinery and compressor station in this
> room. The physics module changes per industry; nothing above it does."

### "A time-of-day rule would get most of this."
> "I tested exactly that. A production-neutral ToD rule captures **18%**. And it
> loses money on 15 of 60 days, because a fixed rule has to balance production
> within the same day, which caps how far it can back off."

### "What if the model is wrong?"
> "It's advisory. The operator is the controller. Safety bounds sit outside the
> optimiser where the model cannot trade against them, and if a schedule is
> infeasible the system says infeasible — it never prints a rupee figure off a
> failed solve."

### "Isn't this just an AI wrapper?"
> "The forecaster is the smallest lever in the system. Perfect foresight is only
> worth about a quarter more than our forecast. If forecasting were the product,
> this wouldn't be worth doing. The product is the landed-cost stack and the
> constraint capture."

### "Chlorine is used downstream — they can't turn down."
> "That is exactly right, and it's the binding constraint in my model. It's why
> the plant floors at 70% of design and not at the 40% the cells could take.
> An independent 2021 paper, validated on real plant data, reaches the same
> conclusion."

### "How much does it cost? What's the payback?"
> "Zero capex — no hardware, no control-system change. Phases one and two are a
> fixed-fee assessment; from phase three we take a share of *verified* saving,
> so payback is structural. I'm not going to quote you a licence fee I haven't
> tested with a buyer."

### "Aren't these savings too small?"
> "They're smaller than everyone else's. Published studies in this field report
> 4 to 10%. I report 1.53%, because I subtract equipment wear and because
> India's demand charge penalises the very peak that load-shifting creates."

### If you genuinely don't know
> **"I don't know. That's an open assumption in my assumptions register — do you
> want me to tell you what I do know about it?"**

Judges forgive gaps. They do not forgive bluffing. **Never say "the model shows"
about something you don't understand — say "the model assumes."**

---

# IF YOU BLANK

Three sentences. Any one of them buys you ten seconds and gets you back on track.

1. *"A price signal is not an operating instruction."*
2. *"Your bill is not the exchange price — 46% of it isn't energy."*
3. *"Do nothing is a valid answer, and that's the whole point."*

---

# YOUR POSITION IN THIS FIELD

Look at the other 19 titles. Seismic denoising, drilling reports, reservoir
interpretation, prospect screening, corrosion, leakage, hydrogen production.

**Almost every other entry is upstream — finding and producing hydrocarbons.
You are the only one on the demand side of the electricity meter.**

That is genuine differentiation, and it's also your one risk: they may not
immediately see why it's theirs. **That's what slide 4 and the second Q&A answer
are for.** Use them.

---

# THE LAST THING

Your real advantage in that room is not the ₹9.17 crore. It's that you show 13
loss-making days, subtract a fifth of your own gross saving, and use a
coefficient that charges you more than the published data requires.

**Most presentations today will claim everything works. Yours says exactly where
it doesn't. Lead with that and the technical gaps become forgivable.**

Timer on. Rehearse twice. Go.
