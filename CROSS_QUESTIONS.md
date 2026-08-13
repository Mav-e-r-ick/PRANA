# PRANA — every cross-question, slide by slide

**Legend**
🟢 **SAFE** — you are strong here, answer with confidence
🟡 **CAREFUL** — true but needs precise wording
🔴 **DANGEROUS** — a real weakness; the answer is honesty, never a bluff

**Universal rules**
1. Answer in **two sentences, then stop.** Silence after a short answer reads as confidence.
2. Never say *"the model shows"* about something you don't understand. Say *"the model assumes."*
3. If you don't know: **"I don't know — that's an open assumption in my register. Want me to tell you what I do know about it?"**

---

# SLIDE 1 · TITLE

### 🟡 "You're at IIT Mandi doing an MBA. What's your engineering background?"
> "Chemical engineering from NIT Rourkela, and I've worked in an ammonia-urea plant on energy monitoring and DCS. So I can read a P&ID and build a process model. I have no first-hand chlor-alkali or refinery experience, and I won't pretend otherwise."

### 🟢 "Did you build this yourself?"
> "Yes — about 3,000 lines of Python, 64 regression tests. It clones and runs in 22 seconds. I can show you the terminal."

### 🟡 "Why the name PRANA?"
> "Process Response and Adaptive Network Agent. प्राण is breath — the plant breathes with the grid instead of holding one rigid setpoint."

### 🟢 "Where do the ₹2.00 and ₹7.06 on your chart come from?"
> "Mean solar-hour and mean evening price from the settled IEX panel — the same 152,542 blocks behind slide 2."

---

# SLIDE 2 · THE MARKET PROBLEM

### 🔴 "3.53 is April–August only. You're cherry-picking your best number."
**This is the most likely opening attack. You already footnote it — say it before they do.**
> "You're right, and it's footnoted for that reason. April to August are India's peak-demand and peak-solar months, so it's biased upward. The like-for-like comparison, April to August at both ends, is 1.83 to 3.53. That's still a doubling, and it's the number I'd defend."

### 🟡 "Why does 2023-24 dip to 1.46? Your trend isn't monotonic."
> "It isn't a trend line, it's five annual observations. The structural break is from 2024-25 onward, when solar penetration started collapsing midday prices. Two flat years then three rising ones is what the data says."

### 🟢 "Maharashtra only. Does this hold nationally?"
> "I only claim Maharashtra, because that's the bid area I have settled data for and the tariff order I've read. The mechanism — solar collapsing midday prices — is national, but I haven't measured it elsewhere and I'm not going to claim it."

### 🟡 "IEX is one of three exchanges. Why should I trust one?"
> "IEX is the largest by volume. For the deviation-rate claim, using IEX alone makes my reference a lower bound, which is the conservative direction. For the price shape, all exchanges clear against the same underlying supply stack."

### 🟢 "Is this data verifiable?"
> "Yes — IEX publishes settled market data. The panel ships with the repo, 152,542 rows. Nothing is modelled."

---

# SLIDE 3 · THE INDUSTRIAL PROBLEM

### 🔴 "Every demand-response company says exactly this. What's new?"
> "The framing isn't new and I won't claim it is. What's new is Indian: a four-year settled price panel, a primary tariff order read to the page, and the landed cost inside the optimisation instead of after it. None of the published work in this field prices an Indian regulatory bill."

### 🔴 "Plants already back off in the evening. You're being paid for what they do free."
**Prepared answer — you have data.**
> "I tested that. A production-neutral time-of-day rule — the one an operator would write on a whiteboard — captures 18% of the value, and it loses money on 15 of 60 days. The reason is structural: a fixed rule must balance production within the same day, which caps how far it can back off at about 91% of design."

### 🟡 "If DO NOTHING is frequent, what am I paying for?"
> "You're paying to know *which* days are worth acting on and which aren't. On my 120-day replay, acting every day would have lost money on 13 of them. Knowing when not to move is most of the value."

### 🟢 "Electricity is a small part of my cost. Why should I care?"
> "For chlor-alkali it's 50–60% of production cost — that's the NPC figure. For a refinery it's smaller, which is exactly why I demonstrated on chlor-alkali first: it's where the physics shows up most clearly."

---

# SLIDE 4 · THE GENERAL SOLUTION

### 🔴 "You've only done chlor-alkali. Why should I believe refinery works?"
> "You shouldn't yet — that's why every other industry says CANDIDATE and carries no savings number. What transfers is the framework: the optimiser, the market engine and the safety logic don't know what the process makes. I have a test that fails if the optimiser ever learns. What has to be rebuilt per industry is the physics module."

### 🟡 "748 MWh — where does that come from?"
> "21.8 MW of safe shed times 34.2 hours of caustic buffer. It's a representation of measured flexibility, not a battery — it can't export to the grid."

### 🟡 "'Candidate' is doing a lot of work on that slide."
> "Deliberately. Refinery utilities and pipeline pumping are coded and they run, but I could not find published grounding for their part-load behaviour, so I show no rupee figure for them. ASU and electrolyser I did find — cryogenic and electrolysis literature."

---

# SLIDE 5 · THE ENGINEERING CORE

### 🟢 "Is V = V₀ + k·i your equation or someone else's?"
**Your strongest single answer. Say it slowly.**
> "Theirs. National Productivity Council, a Government of India body, page 28 of their chlor-alkali sector manual. They also publish an empirical cell curve on page 29. I derived the convexity from their equation — I didn't fit it."

### 🟢 "You use β = 0.21 but the published curve implies 0.30–0.45. Why the discrepancy?"
**This is a gift. It's your conservatism proof.**
> "Because 0.21 charges me a larger round-trip loss than their own data requires. If I used their coefficient my headline number goes *up* about 6%. I kept the conservative one."

### 🔴 "Current efficiency falls at low current density. You've ignored it."
> "You're right that it's not in the model as a term. I tested the effect and the specific-energy claim survives — but it's not modelled explicitly, and I'd list it as an open item for plant calibration."

### 🟡 "16 tangent hyperplanes — why 16?"
> "Measured linearisation error is 0.025%, which is far below every other uncertainty in the model. More tangents would be false precision."

### 🔴 "This is textbook convex optimisation. Where's the innovation?"
> "The optimisation isn't the innovation and I don't claim it is — MILP scheduling is decades old. The contribution is that nobody has connected published process physics to an Indian landed-cost bill and produced a per-plant flexibility price. The hard part was reading the tariff order, not the solver."

---

# SLIDE 6 · THE NOVEL OBJECT φ

### 🔴 "Otashu and Baldea published chlor-alkali demand response years ago."
**If a professor asks this, they know the field. Concede immediately.**
> "They did, and Weigert's group at TU Berlin has a dynamic model validated on real plant data — which mine is not. I'm not claiming the concept. What didn't exist is any of it grounded in an Indian tariff, on Indian settled prices."

### 🟡 "What are the actual φ values?"
> "For the chlor-alkali cell house, tens of rupees per MWh shifted. For pipeline pumping it's roughly ten times higher — that's the cube law showing up as a price."

### 🟢 "Why call it a battery if it can't export?"
> "I'm careful not to. It's a *representation* of safe flexibility expressed in grid units. It can't export, it can't serve any load but its own, and its capacity is inventory that exists to buffer production."

### 🟡 "φ returns infinity — isn't that just a modelling failure?"
> "It's a deliberate answer. A process that cannot move should say so rather than return a large number that the optimiser might still trade against. Infinity is what makes DO NOTHING a real result."

---

# SLIDE 7 · THE SYSTEM

### 🟡 "MAE of 1,072 — is that good? On what scale?"
> "Rupees per MWh, against prices that range from near zero to ten thousand. It beats persistence at 1,189, day-ahead-as-forecast at 1,271, and a seven-day block mean at 1,538. Trained through March, tested April to August — genuinely out of sample."

### 🟢 "Why LightGBM and not a neural network?"
> "Because it wins on this data and it's interpretable. And honestly the forecaster is the smallest lever in the system — perfect foresight is only worth about a quarter more than my forecast. If forecasting were the product this wouldn't be worth doing."

### 🟡 "0.3 seconds for one day. Will it scale to a fleet?"
> "For a multi-day horizon it's about 6 seconds for a week. A fleet is many independent site problems, not one big one, so it parallelises. I haven't stress-tested a hundred sites."

### 🔴 "Can your LLM hallucinate a safety constraint?"
**Answer this crisply — it's a safety question and they're testing you.**
> "No. The agent proposes *candidate* constraints from SOPs or operator speech, each tagged with its source, and an engineer approves them before they enter the model. It cannot set a limit and it cannot pick a setpoint. The explanations come from the solver's own binding constraints, not from the language model."

---

# SLIDE 8 · LANDED COST

### 🔴 "60% plus 46% is 106%."
**FIX THE SLIDE BEFORE YOU PRESENT. If it's still there:**
> "That's a typo on my slide — it should read 54%. The verified non-energy share is 46%, so energy is 54%. Thank you for catching it."

### 🟢 "Where does ₹22,109 per MW per day come from?"
> "₹650 per kVA per month, divided by 0.98 power factor, times 1,000 kVA per MW, divided by 30 days. The ₹650 is MERC Case 75 of 2025, post-remand order, page 100, HT Industry at EHV."

### 🟢 "Are you sure that's the current order?"
**This is where you shine.**
> "Yes — and it's worth knowing that the June 2025 order was quashed by the Bombay High Court. Most published summaries still quote it. The operative one is the post-remand order dated 25 March 2026."

### 🔴 "Does your landed cost include the additional surcharge?"
**Genuine vulnerability. Do not dodge.**
> "It's set to zero, assuming the waiver applies. That's the single largest unquantified risk in my economics — if the waiver doesn't apply, roughly ₹1.39 a unit, the open-access case can invert. It's flagged as a placeholder in my assumptions register."

### 🟡 "How did you calculate the refinery ₹22.3 crore?"
> "Two schedules for the same five high-spread days — one optimised against the market price alone, one against the full landed bill — then both settled at the real bill. The refinery block loses 3.3% by being shown the wrong price. The percentage is the robust figure; the annualisation is indicative only, since those are five high-spread days extrapolated."

### 🔴 "Your chlor-alkali row says 0.95%. Is that current?"
**It is not. Be honest.**
> "That figure is stale — it predates the chlorine-balance constraint I added. On the current model it's much smaller, because once the downstream constraint is properly modelled the plant is too constrained for the price signal to change the answer. The refinery row is where the effect is visible."

---

# SLIDE 9 · PROOF

### 🔴 "Which plant is this?"
**The single most likely question in the room. Pre-empt it on the slide.**
> "It isn't one. It's a 700-TPD archetype built on published physics — a design case, not a named site. The prices and the tariff are real; the plant is modelled. Closing that gap is thirty days of read-only historian data, which is exactly what the pilot asks for."

### 🔴 "So you've never run this on a real plant."
> "Correct. The market and tariff half is real and validated. The plant half has never been fitted to a real historian. That's eight tags and thirty days, not a research programme."

### 🟢 "Thirteen days worse than doing nothing. Why would I buy that?"
**Turn it around — this is a strength.**
> "Because I'm showing you those days instead of removing them. A single-asset site with a hard production floor has no second lever when the forecast is wrong. A second flexible asset removes most of it — that's an argument for the platform, and it's the honest reason to add one."

### 🟡 "1.53% of the bill. That's noise."
> "It's below every published estimate in this field — those cluster between 4 and 10%. I come in lower because I subtract equipment wear and because India's demand charge penalises the very peak that load-shifting creates."

### 🟡 "Why subtract ₹76.8 lakh? Are you sure that's enough?"
> "It's membrane wear from setpoint movement, chlorine diverted to the bleach plant, and power-factor droop — a fifth of the gross, paid straight back. I don't claim it's complete. Rectifier thermal cycling and tap-changer operations are not priced, and I'd list those as open."

### 🟢 "Zero violations — verified how?"
> "Independently. The verifier doesn't re-check the optimiser's arithmetic — it re-integrates inventory from scratch against the exact nonlinear curve and re-checks every bound. The optimiser doesn't get to mark its own homework."

### 🟡 "What exactly is your counterfactual?"
> "One steady setpoint held all day, which is how these plants actually run. And I also compare against a competent time-of-day rule, which captures 18%."

---

# SLIDE 10 · SCALE AND THE ASK

### 🔴 "What does the pilot cost? What's the payback?"
> "Zero capex — no hardware, no control-system change. Phases one and two are a fixed-fee assessment; from phase three we take a share of verified saving, so payback is structural. I'm not going to quote you a licence fee I haven't tested with a buyer."

### 🔴 "What stops us building this ourselves?"
> "The optimiser, nothing — any competent OR group rebuilds it in a month, and I'd say so. What accretes is the regulatory stack across 29 states, each with its own order and surcharge position, and the constraint capture per site, which doesn't transfer."

### 🔴 "Why you rather than an IIT team with a better model?"
**Rehearse this one. It's the closer.**
> "They'll likely have a better model. The model was never the hard part — reading a 123-page tariff order to the correct page was, and knowing which order is operative. I'd rather be the person who read it."

### 🟡 "Who owns the IP after a pilot?"
> "Open to negotiation — the code is mine, the plant's calibration data stays theirs. I'd expect that written into the pilot agreement rather than decided on a slide."

### 🟢 "What are you actually asking for today?"
> "One read-only historian export from one plant. Eight tags, thirty days. The same access you'd give an energy auditor."

---

# CROSS-CUTTING QUESTIONS

### 🔴 "Is this a project or a company?"
> "Today it's a working prototype with a validated case study. It becomes a company the day a plant gives me thirty days of data and the number survives contact with it."

### 🔴 "You're solo. Who builds this?"
> "Solo today. The first hire is a process engineer with chlor-alkali or refinery floor time — the gap in this project is plant access, not software."

### 🟡 "How is this Digital Asset Management?"
> "The twin isn't a 3D visualisation — it's a physics model whose only job is to make a financial decision about a physical asset every fifteen minutes. That's asset management when the asset is a rectifier."

### 🔴 "Why should an oil and gas panel care about a chlorine plant?"
**Your single most important answer. Memorise it.**
> "The demonstrator is chlor-alkali because it's the hardest test — power is 50–60% of its cost and it has an unstorable co-product. The layer that matters to you is the landed-cost engine, and that's true for any HT industrial consumer, including every refinery and compressor station in this room. The physics module changes per industry. Nothing above it does."

### 🟢 "What's your biggest weakness?"
**Answer it straight. Deflecting here costs you more than the weakness does.**
> "No plant data. Everything else is downstream of that. The ramp rate is my least-grounded parameter and it's the one most likely to be wrong on day one."

---

# IF IT ALL GOES WRONG

If you lose the thread completely, say this and stop:

> **"Let me give you the one thing I'd want you to take away. Your bill is not the exchange price — 46% of it isn't energy, and the demand charge alone is ₹22,109 per megawatt of peak per day, from page 100 of the current MERC order. That's true whether or not anyone ever buys this from me."**

Then: **"What else would you like me to address?"**
