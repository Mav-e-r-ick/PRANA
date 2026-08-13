"""
Hackathon evidence pack: value of PROCESS-BUFFER flexibility ("molecular battery")
on the project's own Maharashtra IEX settlement panel.

Computes, on real data only:
  A. Hourly price shape by FY (solar trough vs evening peak)
  B. Energy-neutral load-shift value: shift X% of a flat industrial load out of
     the evening window into the cheapest blocks of the SAME day (buffer-limited).
     -> Rs/kWh of total load, Rs/MW-yr
  C. Comparison: 4h BESS perfect-foresight arbitrage (import/export, 85% RTE)
  D. Electrolyser price-duration curve: mean price of cheapest N hours/yr
     -> the CUF vs power-cost frontier that sets green-H2 LCOH
  E. G-DAM green premium by window (is green power cheap in solar hours?)
"""
import pandas as pd, numpy as np, sys

BASE = r"C:/Users/mysti/Downloads/Thesis Energy Project/data/processed/iex"

def load(seg):
    df = pd.read_csv(f"{BASE}/{seg}_W2_Maharashtra.csv",
                     usecols=["timestamp", "Price (Rs./MWh)"])
    df["ts"] = pd.to_datetime(df["timestamp"])
    df = df.rename(columns={"Price (Rs./MWh)": "p"}).drop(columns=["timestamp"])
    df["date"] = df["ts"].dt.date
    df["hour"] = df["ts"].dt.hour
    # Indian financial year
    y, m = df["ts"].dt.year, df["ts"].dt.month
    df["fy"] = np.where(m >= 4, y.astype(str) + "-" + (y % 100 + 1).astype(str).str.zfill(2),
                        (y - 1).astype(str) + "-" + (y % 100).astype(str).str.zfill(2))
    return df.sort_values("ts").reset_index(drop=True)

rtm, dam, gdam = load("RTM"), load("DAM"), load("GDAM")
FULL = ["2022-23", "2023-24", "2024-25", "2025-26"]

print("=" * 78)
print("A. HOURLY PRICE SHAPE  (RTM, Rs/MWh, mean by hour)")
print("=" * 78)
sh = rtm.pivot_table(index="hour", columns="fy", values="p", aggfunc="mean")
print(sh[FULL + [c for c in sh.columns if c not in FULL]].round(0).to_string())

print("\n" + "=" * 78)
print("B. ENERGY-NEUTRAL LOAD SHIFT  (buffer-limited, same-day, per 1 MW flat load)")
print("=" * 78)
print("Shift a fraction f of a flat load out of the K most expensive blocks of the")
print("day into the K cheapest blocks of the same day (K = buffer hours x 4).")
print()
hdr = f"{'FY':<10}{'buf(h)':>7}{'shift%':>8}{'Rs/MWh avoided':>16}{'Rs/kWh of load':>16}{'Rs lakh/MW-yr':>15}"
for seg, df in [("RTM", rtm), ("DAM", dam)]:
    print(f"\n-- {seg} --\n{hdr}")
    for fy in FULL + ["2026-27"]:
        d = df[df.fy == fy]
        if d.empty:
            continue
        ndays = d["date"].nunique()
        for buf_h in (2, 4, 6):
            K = buf_h * 4
            for f in (0.20,):
                # per day: move f MW of load from K dearest to K cheapest blocks
                g = d.groupby("date")["p"]
                exp = g.apply(lambda s: s.nlargest(K).mean() if len(s) >= 2 * K else np.nan)
                chp = g.apply(lambda s: s.nsmallest(K).mean() if len(s) >= 2 * K else np.nan)
                spread = (exp - chp).dropna()
                # energy shifted per day (MWh) = f * 1MW * K blocks * 0.25h
                mwh_shift = f * K * 0.25
                saving_day = spread * mwh_shift                    # Rs/day per MW
                total_mwh_day = 24.0                               # 1 MW flat
                rs_per_mwh_load = saving_day.mean() / total_mwh_day
                annual = saving_day.mean() * 365 / 1e5             # Rs lakh/MW-yr
                print(f"{fy:<10}{buf_h:>7}{f*100:>7.0f}%{spread.mean():>16,.0f}"
                      f"{rs_per_mwh_load/1000:>16.2f}{annual:>15.1f}")

print("\n" + "=" * 78)
print("C. BENCHMARK: 4h BESS perfect-foresight arbitrage (85% RTE), Rs lakh/MW-yr")
print("=" * 78)
for fy in FULL + ["2026-27"]:
    d = rtm[rtm.fy == fy]
    if d.empty:
        continue
    g = d.groupby("date")["p"]
    hi = g.apply(lambda s: s.nlargest(16).mean())
    lo = g.apply(lambda s: s.nsmallest(16).mean())
    # 4 MWh per MW, discharge revenue - charge cost with RTE
    daily = (hi * 4 * 0.85 - lo * 4)
    print(f"  {fy:<10} median daily spread {np.median(hi-lo):>8,.0f} Rs/MWh   "
          f"-> {daily.mean()*365/1e5:>7.1f} lakh/MW-yr")

print("\n" + "=" * 78)
print("D. ELECTROLYSER FRONTIER: mean RTM price of the cheapest N hours of the year")
print("=" * 78)
print(f"{'FY':<10}" + "".join(f"{h:>10}" for h in
      ["2000h", "3000h", "4000h", "5000h", "6000h", "7000h", "8760h"]))
for fy in FULL:
    d = rtm[rtm.fy == fy]["p"].sort_values().values
    nb = len(d)
    row = f"{fy:<10}"
    for hrs in (2000, 3000, 4000, 5000, 6000, 7000, 8760):
        k = min(int(hrs * 4 * nb / 35040), nb)
        row += f"{d[:k].mean()/1000:>10.2f}"
    print(row + "   (Rs/kWh)")

print("\n  Rough LCOH sensitivity (alkaline, 50 kWh/kg, capex 45,000 Rs/kW,")
print("  10% WACC 20y -> ~5,290 Rs/kW-yr, O&M 3% capex, no incentive):")
print(f"{'FY':<10}{'CUF hrs':>9}{'power Rs/kWh':>14}{'LCOH Rs/kg':>12}")
CAPEX, ANN, KWH_KG = 45000.0, 0.1175, 50.0   # annuity factor ~ 0.1175 @10%/20y
for fy in ["2024-25", "2025-26"]:
    d = rtm[rtm.fy == fy]["p"].sort_values().values
    nb = len(d)
    for hrs in (2000, 3000, 4000, 6000, 8000):
        k = min(int(hrs * 4 * nb / 35040), nb)
        pwr = d[:k].mean() / 1000
        kg = hrs * 1.0 / KWH_KG                      # kg per kW-yr
        fixed = CAPEX * (ANN + 0.03) / kg
        print(f"{fy:<10}{hrs:>9}{pwr:>14.2f}{pwr*KWH_KG + fixed:>12.0f}")

print("\n" + "=" * 78)
print("E. G-DAM GREEN PREMIUM over DAM by window (Rs/MWh)")
print("=" * 78)
m = dam[["ts", "p", "fy", "hour"]].merge(gdam[["ts", "p"]], on="ts", suffixes=("_d", "_g"))
m["win"] = np.where(m.hour.between(9, 16), "solar 09-17",
           np.where(m.hour.between(17, 23), "evening 17-24", "other"))
print(m[m.fy.isin(FULL)].groupby(["fy", "win"]).apply(
    lambda x: pd.Series({"premium": (x.p_g - x.p_d).mean(),
                         "DAM": x.p_d.mean(), "GDAM": x.p_g.mean()}),
    include_groups=False).round(0).to_string())
