from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class Snapshot:
    futures: pd.DataFrame
    options: pd.DataFrame
    summary: pd.DataFrame
    refreshed_at: datetime
    source_label: str


def _normalize_expiry(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def validate_futures(df: pd.DataFrame) -> pd.DataFrame:
    required = {"expiry", "forward_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Futures data is missing columns: {', '.join(sorted(missing))}")
    out = df.copy()
    out["expiry"] = _normalize_expiry(out["expiry"])
    out["forward_price"] = pd.to_numeric(out["forward_price"], errors="coerce")
    out = out.dropna(subset=["expiry", "forward_price"]).sort_values("expiry")
    if out.empty:
        raise ValueError("No valid futures rows were found.")
    return out


def validate_options(df: pd.DataFrame) -> pd.DataFrame:
    required = {"expiry", "strike", "call_delta"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Options data is missing columns: {', '.join(sorted(missing))}")
    out = df.copy()
    out["expiry"] = _normalize_expiry(out["expiry"])
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    out["call_delta"] = pd.to_numeric(out["call_delta"], errors="coerce")
    out = out.dropna(subset=["expiry", "strike", "call_delta"])
    out = out[(out["call_delta"] > 0) & (out["call_delta"] < 1)]
    if out.empty:
        raise ValueError("No valid option rows were found.")
    return out.sort_values(["expiry", "strike"])


def select_market_implied_scenario(futures: pd.DataFrame, options: pd.DataFrame, target_delta: float) -> pd.DataFrame:
    rows = []
    futures_by_expiry = futures.groupby("expiry", as_index=False).first().set_index("expiry")
    for expiry, fut_row in futures_by_expiry.iterrows():
        chain = options[options["expiry"] == expiry].copy()
        if chain.empty:
            continue
        chain["delta_gap"] = (chain["call_delta"] - target_delta).abs()
        chosen = chain.sort_values(["delta_gap", "strike"]).iloc[0]
        forward = float(fut_row["forward_price"])
        scenario = float(chosen["strike"])
        protection = scenario - forward
        rows.append({
            "expiry": expiry,
            "current_lock_in_price": forward,
            "market_implied_price_scenario": scenario,
            "selected_call_delta": float(chosen["call_delta"]),
            "potential_hedge_protection": protection,
            "potential_hedge_protection_pct": protection / forward if forward else np.nan,
        })
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("No matching expiries were found between the futures and options data.")
    return result.sort_values("expiry").reset_index(drop=True)


def generate_demo_market_data(seed: int | None = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    today = pd.Timestamp.today().normalize()
    expiries = pd.date_range(today + pd.offsets.MonthEnd(1), periods=12, freq="ME")
    base = 2550.0
    curve, options = [], []
    for i, expiry in enumerate(expiries):
        forward = base + 12 * i + 18 * np.sin(i / 2.2) + rng.normal(0, 5)
        curve.append({"expiry": expiry, "forward_price": round(forward, 2)})
        t_years = max((expiry - today).days / 365.25, 1 / 365.25)
        vol = 0.18 + 0.015 * np.sqrt(t_years) + rng.normal(0, 0.002)
        strikes = np.arange(round(forward * 0.80 / 25) * 25, round(forward * 1.30 / 25) * 25 + 25, 25)
        for strike in strikes:
            d1 = (np.log(forward / strike) + 0.5 * vol * vol * t_years) / (vol * np.sqrt(t_years))
            call_delta = 1.0 / (1.0 + np.exp(-1.702 * d1))
            options.append({
                "expiry": expiry,
                "strike": float(strike),
                "call_delta": float(np.clip(call_delta, 0.001, 0.999)),
            })
    return pd.DataFrame(curve), pd.DataFrame(options)


def build_snapshot_from_frames(futures: pd.DataFrame, options: pd.DataFrame, target_delta: float, source_label: str) -> Snapshot:
    futures = validate_futures(futures)
    options = validate_options(options)
    summary = select_market_implied_scenario(futures, options, target_delta)
    return Snapshot(futures, options, summary, datetime.now().astimezone(), source_label)
