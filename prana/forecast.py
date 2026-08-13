"""Quantile price forecasting for the real-time market.

Deliberately not the centrepiece. In a five-lever ranking run on this same
panel, the exchange-timing decision came LAST at Rs 0.13/kWh realistic
(Rs 0.31 with perfect foresight) while load shifting came first by roughly an
order of magnitude. A better forecast is worth paise; a better constraint model
is worth rupees. The forecast exists here because the optimizer needs a
*distribution* to take a risk-aware decision, not because accuracy is the
product.

The single most important feature is the day-ahead clearing price for the same
delivery block: it is known 12-36 hours before delivery and correlates 0.811
with the real-time price, beating same-block previous-day persistence at 0.765.

    python -m prana.forecast --train
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR

QUANTILES = (0.10, 0.50, 0.90)
MODEL_PATH = DATA_DIR / "forecast_lgbm.pkl"

_FEATURES = [
    "dam", "dam_lag1", "dam_lead1", "dam_day_mean", "dam_block_rank",
    "rtm_lag96", "rtm_lag672", "rtm_roll_d7_block", "rtm_prev_day_mean",
    "block", "hour", "dow", "month", "is_weekend",
    "gdam_spread",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Causal features only — nothing here uses information from after the
    day-ahead gate closes for the delivery block being predicted."""
    d = df.sort_values("ts").reset_index(drop=True).copy()

    d["dam_lag1"] = d["dam"].shift(1)
    d["dam_lead1"] = d["dam"].shift(-1)          # same-day DAM curve is known
    d["dam_day_mean"] = d.groupby("date")["dam"].transform("mean")
    d["dam_block_rank"] = d.groupby("date")["dam"].rank(pct=True)

    d["rtm_lag96"] = d["rtm"].shift(96)          # same block, yesterday
    d["rtm_lag672"] = d["rtm"].shift(672)        # same block, last week
    d["rtm_roll_d7_block"] = (
        d.groupby("block")["rtm"].transform(lambda s: s.shift(1).rolling(7).mean())
    )
    d["rtm_prev_day_mean"] = (
        d.groupby("date")["rtm"].transform("mean").shift(96)
    )
    d["is_weekend"] = (d["dow"] >= 5).astype(int)
    d["gdam_spread"] = d["gdam"].fillna(d["dam"]) - d["dam"]
    return d


def _pinball(y: np.ndarray, yhat: np.ndarray, q: float) -> float:
    e = y - yhat
    return float(np.mean(np.maximum(q * e, (q - 1) * e)))


class QuantileForecaster:
    """LightGBM quantile regression, one model per quantile."""

    def __init__(self) -> None:
        self.models: dict[float, object] = {}
        self.metrics: dict[str, float] = {}
        self.trained_through: str | None = None
        self.spread_scale: float = 1.0     # conformal widening factor

    def fit(
        self,
        df: pd.DataFrame,
        train_end: str = "2026-03-31",
        calib_days: int = 90,
    ) -> "QuantileForecaster":
        import lightgbm as lgb

        d = build_features(df).dropna(subset=_FEATURES + ["rtm"])
        train = d[d["ts"] <= train_end]
        if train.empty:
            raise ValueError("no training rows before train_end")

        # Hold out the tail of the training window for interval calibration, so
        # the widening factor is not fitted on data the trees have memorised.
        cut = pd.Timestamp(train_end) - pd.Timedelta(days=calib_days)
        core = train[train["ts"] <= cut]
        calib = train[train["ts"] > cut]
        fit_on = core if len(core) > 5000 else train

        X, y = fit_on[_FEATURES], fit_on["rtm"]
        for q in QUANTILES:
            m = lgb.LGBMRegressor(
                objective="quantile", alpha=q,
                n_estimators=500, learning_rate=0.05,
                num_leaves=63, min_child_samples=40,
                subsample=0.85, subsample_freq=1, colsample_bytree=0.85,
                verbose=-1, n_jobs=-1,
            )
            m.fit(X, y)
            self.models[q] = m

        self.spread_scale = self._calibrate(calib) if len(calib) > 500 else 1.0
        self.trained_through = str(train_end)
        return self

    def _calibrate(self, calib: pd.DataFrame, target: float = 0.80) -> float:
        """Scale the q10/q90 offsets so the interval actually covers `target`.

        Quantile GBMs systematically under-cover on heavy-tailed price data.
        A single multiplicative factor, fitted out-of-sample, is the cheapest
        honest fix and keeps the CVaR term from being overconfident.
        """
        X, y = calib[_FEATURES], calib["rtm"].to_numpy()
        lo = np.asarray(self.models[0.10].predict(X), dtype=float)
        med = np.asarray(self.models[0.50].predict(X), dtype=float)
        hi = np.asarray(self.models[0.90].predict(X), dtype=float)
        dn, up = np.maximum(med - lo, 1e-6), np.maximum(hi - med, 1e-6)

        best, best_gap = 1.0, 9e9
        for k in np.arange(1.0, 3.01, 0.05):
            cov = np.mean((y >= med - k * dn) & (y <= med + k * up))
            gap = abs(cov - target)
            if gap < best_gap:
                best, best_gap = float(k), gap
        return best

    def _apply_scale(self, lo, med, hi):
        k = self.spread_scale
        return (
            np.clip(med - k * (med - lo), 0.0, 10_000.0),
            np.clip(med, 0.0, 10_000.0),
            np.clip(med + k * (hi - med), 0.0, 10_000.0),
        )

    def predict(self, df_day: pd.DataFrame, history: pd.DataFrame) -> dict[float, np.ndarray]:
        """Predict the 96 blocks of one delivery day.

        `history` must contain the run-up so lag features resolve; the day
        itself is appended and only its rows are returned.
        """
        ctx = pd.concat(
            [history[history["ts"] < df_day["ts"].min()].tail(1400), df_day],
            ignore_index=True,
        )
        feats = build_features(ctx).tail(len(df_day))
        X = feats[_FEATURES].ffill().bfill()
        raw = {q: np.asarray(m.predict(X), dtype=float) for q, m in self.models.items()}
        # enforce monotone quantiles, then widen by the calibration factor
        stack = np.sort(np.vstack([raw[q] for q in QUANTILES]), axis=0)
        lo, med, hi = self._apply_scale(stack[0], stack[1], stack[2])
        return {0.10: lo, 0.50: med, 0.90: hi}

    # ------------------------------------------------------------ evaluation
    def evaluate(self, df: pd.DataFrame, test_start: str = "2026-04-01") -> dict[str, float]:
        d = build_features(df).dropna(subset=_FEATURES + ["rtm"])
        test = d[d["ts"] >= test_start]
        if test.empty:
            return {}
        X, y = test[_FEATURES], test["rtm"].to_numpy()

        res: dict[str, float] = {"n_test_blocks": float(len(test)),
                                 "spread_scale": self.spread_scale}
        raw = {q: np.asarray(self.models[q].predict(X), dtype=float) for q in QUANTILES}
        stack = np.sort(np.vstack([raw[q] for q in QUANTILES]), axis=0)
        lo, med_, hi = self._apply_scale(stack[0], stack[1], stack[2])
        preds = {0.10: lo, 0.50: med_, 0.90: hi}
        for q in QUANTILES:
            res[f"pinball_q{int(q*100)}"] = _pinball(y, preds[q], q)
        res["pinball_mean"] = float(np.mean([res[f"pinball_q{int(q*100)}"] for q in QUANTILES]))
        res["coverage_80"] = float(np.mean((y >= preds[0.10]) & (y <= preds[0.90])))

        med = preds[0.50]
        res["mae_median"] = float(np.mean(np.abs(y - med)))
        res["rmse_median"] = float(np.sqrt(np.mean((y - med) ** 2)))

        # Three honest baselines, scored on the same rows.
        for label, series in (
            ("naive_persistence", test["rtm_lag96"].to_numpy()),
            ("dam_as_forecast", test["dam"].to_numpy()),
            ("block_mean_7d", test["rtm_roll_d7_block"].to_numpy()),
        ):
            res[f"mae_{label}"] = float(np.mean(np.abs(y - series)))
            res[f"pinball50_{label}"] = _pinball(y, series, 0.50)
        return res

    # ------------------------------------------------------------ persistence
    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(
                {"models": self.models, "metrics": self.metrics,
                 "trained_through": self.trained_through,
                 "spread_scale": self.spread_scale}, fh)

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "QuantileForecaster":
        obj = cls()
        with open(path, "rb") as fh:
            blob = pickle.load(fh)
        obj.models = blob["models"]
        obj.metrics = blob.get("metrics", {})
        obj.trained_through = blob.get("trained_through")
        obj.spread_scale = blob.get("spread_scale", 1.0)
        return obj

    @classmethod
    def available(cls, path: Path = MODEL_PATH) -> bool:
        return path.exists()


def perfect_foresight(df_day: pd.DataFrame) -> dict[float, np.ndarray]:
    """Upper bound: the realised price as all three quantiles.

    Used to separate the value of flexibility from the value of forecast skill.
    Always report both numbers; the gap is the forecast-error haircut.
    """
    r = df_day["rtm"].to_numpy(dtype=float)
    return {q: r.copy() for q in QUANTILES}


def _cli() -> None:
    from .data import load_market

    ap = argparse.ArgumentParser(description="PRANA price forecaster")
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--train-end", default="2026-03-31")
    ap.add_argument("--test-start", default="2026-04-01")
    args = ap.parse_args()

    df = load_market()
    f = QuantileForecaster()
    if args.train or not QuantileForecaster.available():
        print(f"training on blocks up to {args.train_end} ...")
        f.fit(df, train_end=args.train_end)
    else:
        f = QuantileForecaster.load()

    m = f.evaluate(df, test_start=args.test_start)
    f.metrics = m
    f.save()

    print(f"\nheld-out blocks from {args.test_start}: {int(m['n_test_blocks']):,}\n")
    print(f"{'model':<22}{'MAE Rs/MWh':>13}{'pinball q50':>14}")
    print("-" * 49)
    print(f"{'PRANA LightGBM':<22}{m['mae_median']:>13,.0f}{m['pinball_q50']:>14,.1f}")
    for label, nice in (
        ("naive_persistence", "naive persistence"),
        ("dam_as_forecast", "DAM as forecast"),
        ("block_mean_7d", "7-day block mean"),
    ):
        print(f"{nice:<22}{m['mae_' + label]:>13,.0f}{m['pinball50_' + label]:>14,.1f}")
    print(f"\nq10/q50/q90 pinball : "
          f"{m['pinball_q10']:.1f} / {m['pinball_q50']:.1f} / {m['pinball_q90']:.1f}")
    print(f"80% interval coverage: {m['coverage_80']*100:.1f}%  (target 80%), "
          f"conformal widening x{m['spread_scale']:.2f}")
    print(f"\nsaved -> {MODEL_PATH}")


if __name__ == "__main__":
    _cli()
