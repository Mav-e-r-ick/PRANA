# ASSUMPTIONS

Every number in PRANA that is **not** measured or published. If it is here, it
is an assumption, it is labelled as one on any slide it appears on, and there is
a stated basis and a stated direction of error.

The test of a model is not whether it has assumptions. It is whether you can
list them, say which way each one bends the answer, and show what happens when
they move. That is what this file is for.

---

## The plant itself

**A-01 · The 700 TPD chlor-alkali site does not exist.**
It is an archetype: 67 MW, 29.2 t/h NaOH (100% basis), lye tankage 300–1,800 t.
No specific plant's historian has ever been fitted. Scale mostly cancels in the
₹/kWh headline — it does not cancel in ₹ crore/year.
*Direction:* neutral on ₹/kWh, unknown on absolute rupees.
*To close:* eight tags, 30 days — see A-14.

**A-02 · Power-curve coefficients a/b/c = 0.06 / 0.73 / 0.21.**
*Basis:* BoP share from NPC p.25 (Cl₂ liquefaction 120–200 kWh/t on a ~2,300
base ⇒ 5–9%); curve shape from NPC p.29.
*Direction:* **conservative.** NPC's own equation implies c = 0.30–0.45, i.e.
steeper convexity and a larger round-trip loss than we model. Re-running with
NPC coefficients moves the headline **up** 6%.
*Status:* the twin's self-test (`test_chloralkali_convexity_matches_the_cell_voltage_law`)
fits against a self-chosen voltage law and is therefore **circular**. It pins
internal consistency, not correctness. Do not present it as validation.

**A-03 · Turndown floor `x_min` = 40% of design.**
*Basis:* H₂-in-Cl₂ safety interlock. **No source found at any tier.**
*Effect:* superseded in practice — the chlorine consumer (A-04) binds first at
70%, so this bound is not active in any reported schedule.

**A-04 · Chlorine consumer holds 70–105% of design draw; bleach plant absorbs
12%; diverted Cl₂ valued at ₹9,000/t.**
*Basis:* none. **This is the single most load-bearing assumption in the model** —
it sets the real turndown floor.
*Direction:* unknown, but **swept**: 60% → ₹10.99 cr, 70% → ₹10.90 cr, 80% →
₹10.45 cr, 90% → ₹7.46 cr per year (45-day sample). Value is nearly flat from
60–80% and only breaks at 90%. **Put the sweep on the slide, not the point.**

**A-05 · Ramp rate 60%/hour (0.15 per 15-min block).**
*Basis:* rectifier electrical response. **No source at any tier, and this is the
parameter most likely to be wrong.**
*Direction:* almost certainly **too fast**, because the rectifier is not the
constraint — the brine loop and the chlorine header are. If the true achievable
rate is 10–15%/h, the schedule mis-times the shed and delivers materially less
than modelled on the first day.
*Not swept.* Say so if asked.

**A-06 · Buffer 20.5 h of cover (usable 1,500 t).**
*Basis:* none.
*Direction:* likely **overstated** 3–5× versus real dispatchable lye swing.
*Mitigation:* measured schedules only use 4.2 h — 8% of the band — so a
3–5× error would not bind. This one is robust by accident, and we say that
rather than claim we sized it correctly.

**A-07 · Membrane cycling ₹1,200 per t/h of setpoint travel; movement budget
60 t/h/day.**
*Basis:* a ~₹21.5 cr membrane set over ~4 years, assuming cycling consumes 5%
of life. **An assumption inside an assumption.**
*Direction:* unknown. Contributes to the 20% of gross saving given back.

**A-08 · Power factor 0.98 → 0.85 linearly to minimum load; 4 rectifier trains.**
*Basis:* thyristor firing-angle displacement. Real behaviour follows cos α and
is **not linear**.
*Direction:* charged post-solve, so the reported saving is net of it. **Note:
`pf_penalty_rs` returns 0 in EXCHANGE mode, which is the headline configuration** —
so in the quoted result power factor costs nothing. Disclose.

**A-09 · Terminal shortfall valued at ₹50,000/t.**
*Basis:* chosen high enough that ending the day short is never an arbitrage,
finite enough that a genuine outage stays solvable. Verified: shortfall is
0.00 t on normal days.

## Tariff and market

**A-10 · Open-access stack: wheeling ₹1.08, cross-subsidy ₹1.31, additional
surcharge ₹0.00, SLDC ₹0.06/kWh, duty 9.3%.**
*Basis:* **all placeholders.** The headline runs in EXCHANGE mode, so these are
load-bearing — they are ~46% of the landed cost, which is the "moat" claim.
*The additional surcharge is set to zero (waiver assumed). If the waiver does
not apply (~₹1.39/kWh), the open-access case can invert.* This is the largest
single unquantified risk in the economics. Say it before you are asked.

**A-11 · DSM ≈ max(DAM, RTM), from 133,056 WRPC blocks.**
*Status:* the audit is real but **lives in the thesis project, not this repo**.
A judge cannot reproduce it here. Treat as cited-but-not-shipped.

**A-12 · MD ratchet 75% of contract demand.**
*Basis:* not found in the operative order, which is a review order rather than a
terms-and-conditions schedule. Would be in MYT Order Case 217 of 2024.
*Direction:* caps the value of peak shaving; a lower ratchet would increase
PRANA's value.

**A-13 · Grid emission factors 0.90 / 0.55 tCO₂/MWh (peak / solar).**
*Basis:* approximate. **No CO₂ figure is quoted in any result**, and none
should be until a marginal — not average — factor is sourced.

## Method

**A-14 · The counterfactual.**
The baseline is one steady setpoint held all day. **We also compare against a
production-neutral time-of-day rule** — shed in the 17:00–24:00 slab, run at the
deliverable maximum in the solar window, depth solved so the day balances. That
rule captures **18%** of PRANA's saving and loses money on 15 of 60 days.
*Both baselines are settled on identical terms, including the terminal-inventory
charge.* An earlier version of this comparison omitted that charge and the rule
appeared to beat PRANA by 382%; that was a rigged comparison and is recorded
here so the error is not repeated.

**A-15 · Sector extrapolation ≈ ₹155 crore/year.**
One archetype's ₹/kWh × installed capacity. Assumes every plant is
open-access, has caustic storage, and has a flexible chlorine consumer — none of
which is evidenced. **Order of magnitude only. Never defend it as an estimate.**

**A-16 · Twin parameters for non-flagship archetypes.**
**ASU is now grounded at the same tier as the chlor-alkali twin.** Peer-reviewed
ASU demand-response literature is substantial and real: Pattison, Touretzky,
Johansson, Harjunkoski & Baldea (scheduling with low-order dynamic models, ASU
application); Zhang, Grossmann, Heuberger, Sundaramoorthy & Pinto (ASU with
cryogenic energy storage, energy and reserve markets); Caspari et al. (*AIChE J.*
2019, flexible ASU design with reflux liquid storage, operating range **3.5–28
MW**); Cao et al. (*AIChE J.* 2017, preemptive dynamic operation). PRANA's 55%
floor matches the standard-design bound (columns flood below 50–60%); Caspari's
12.5% applies to a *purpose-designed* flexible ASU with added storage and
refrigeration, and must not be quoted for a standard unit. Electrolyser SEC
50 kWh/kg is supported at technology-class level (<50 kWh/kg nominal). The electrolyser's 15% minimum is
**below** the cited comfortable range (~30% before auxiliaries dominate) and is
likely optimistic. **Refinery utility-block and pipeline twins are coded but
ungrounded — no public source was found for either. No rupee figure is presented
for them.**

## Known limitations, stated plainly

- Layer A (market/tariff) is **TRL 5–6**: validated on real settled data, never
  run live against an actual bill.
- Layer B (process twin) is **TRL 3**: analytical proof of the critical
  characteristic via NPC, **no experimental proof against any real plant**.
- 120 days, one bid area, one price regime, one archetype. Best 20 days carry
  31% of the total saving.
- The demo day (2026-07-12) saves 1.72× the mean. Volunteer this.
- No confidence intervals on any headline figure.
