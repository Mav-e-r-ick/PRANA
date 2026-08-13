# PRANA — 4 minute demo script

Open **PRANA_APP.html** (double-click; works offline, no install).
Keep a terminal open at the repo as proof it is real code.

---

## Opening — 20 s

> "PRANA does not start by asking how much electricity we can save.
> It starts by asking **what the plant is allowed to do**."

Landing screen. Point at the three greyed-out options.

> "Refinery, fertiliser, hydrogen — the framework accepts them. I have not
> calibrated them against plant data, so I show you no savings number for them.
> Two demonstrations are live: one validated, one illustrative."

---

## 1 · Chlor-alkali, the validated case — 70 s

Click **CHLOR-ALKALI**.

> "700 tonne-per-day cell house, 12 July 2026. Real settled IEX prices, real
> MERC tariff — page 100 of the operative order."

Point at the envelope card.

> "The plant can physically go to 40% of design. It goes to **70%**. Not because
> of the cells — because chlorine is made at the same time as caustic soda,
> cannot be stored, and the downstream consumer has to take it. That constraint
> halved the usable flexibility, and an independent 2021 paper validated on a
> real plant reaches the same conclusion."

Point at the peak KPI.

> "Notice the peak went **up** — 79 to 82.9 MW. It bought 3.9 megawatts of peak
> worth ₹85,000 a day, because the energy saving beat it. It knew the price of
> that decision. A tool optimising the exchange price would not have."

Point at violations = 0, then the replay table.

> "Zero violations across 120 days, re-verified against the true nonlinear
> physics. ₹9.17 crore a year — and that is *net* of membrane wear, chlorine
> diverted and power-factor droop, which take back a fifth of the gross."

---

## 2 · The same engine, different physics — 90 s

Back → click **GENERIC PROCESS**.

> "Same optimiser. Same decision logic. Same safety architecture. Different
> physics. Nothing below the process boundary knows what this plant makes."

**Preset A.** → **SHIFT**

> "High price, the process can move, the penalty is below the benefit. Shift."

**Preset B.** → **DO NOTHING**

> "Same electricity price. But this process is mostly standby load and charges
> heavily for movement. The flexibility **exists** — it just costs more than it
> saves. PRANA declines."

**Preset C.** → **DO NOTHING**

> "Same price again. Now a downstream unit is on fixed take. Look at the reason
> code: HARD_CONSTRAINT. The electricity price was never even evaluated —
> constraints are checked before economics, always."

Drag a slider or two.

> "Every one of those reasons comes from the model, not from a language model.
> The LLM's job is to turn an operator's sentence into a *candidate* constraint
> that an engineer approves. It cannot set a limit and it cannot pick a setpoint."

---

## 3 · Close — 20 s

> "PRANA is useful precisely because it can say **no**. Two of those three
> scenarios ended in do-nothing, on a high price, and that is the product
> working correctly.
>
> Chlor-alkali is not the product. It is the proof that the platform can turn
> process physics into an economic flexibility decision."

---

## If asked to prove it is real

```bash
python -m pytest tests -q          # 64 tests
python -m prana.scenarios          # the three decisions, from the engine
python run_demo.py --site chloralkali
```
