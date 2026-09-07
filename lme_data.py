from __future__ import annotations

from io import StringIO
import re

import pandas as pd
import requests


LME_ALUMINUM_MONTHLY_URL = (
    "https://www.lme.com/en/Market-data/Reports-and-data/LME-monthly-futures-quotes"
)


def _flatten_columns(columns) -> list[str]:
    flattened = []
    for col in columns:
        if isinstance(col, tuple):
            text = " ".join(str(part) for part in col if str(part) != "nan")
        else:
            text = str(col)
        flattened.append(re.sub(r"\s+", " ", text).strip().lower())
    return flattened


def _third_wednesday(year: int, month: int) -> pd.Timestamp:
    first = pd.Timestamp(year=year, month=month, day=1)
    days_until_wednesday = (2 - first.weekday()) % 7
    first_wednesday = first + pd.Timedelta(days=days_until_wednesday)
    return (first_wednesday + pd.Timedelta(days=14)).normalize()


def _parse_contract_month(value: str) -> pd.Timestamp | None:
    text = str(value).strip()
    match = re.search(r"\b([A-Za-z]{3})\s+(\d{2})\b", text)
    if not match:
        return None

    month_text, year_text = match.groups()
    try:
        parsed = pd.to_datetime(f"01 {month_text} 20{year_text}", format="%d %b %Y")
    except ValueError:
        return None
    return _third_wednesday(parsed.year, parsed.month)


def fetch_lme_aluminum_monthly_curve(timeout: int = 20) -> pd.DataFrame:
    """Fetch the free 15-minute-delayed LME Aluminum 3W monthly outright curve.

    LME currently publishes the first six monthly contracts on its public website.
    The returned forward_price is the midpoint of displayed bid and ask quotes.
    """

    response = requests.get(
        LME_ALUMINUM_MONTHLY_URL,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            )
        },
    )
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    candidate = None

    for table in tables:
        frame = table.copy()
        frame.columns = _flatten_columns(frame.columns)
        cols = set(frame.columns)
        if any("contract" in c for c in cols) and "bid" in cols and "ask" in cols:
            candidate = frame
            break

    if candidate is None:
        raise RuntimeError(
            "The LME page loaded, but the monthly aluminum quote table could not be parsed. "
            "The page structure may have changed."
        )

    contract_col = next(c for c in candidate.columns if "contract" in c)
    out = candidate[[contract_col, "bid", "ask"]].copy()
    out.columns = ["contract", "bid", "ask"]

    out["expiry"] = out["contract"].map(_parse_contract_month)
    out["bid"] = pd.to_numeric(out["bid"], errors="coerce")
    out["ask"] = pd.to_numeric(out["ask"], errors="coerce")
    out = out.dropna(subset=["expiry", "bid", "ask"])

    if out.empty:
        raise RuntimeError("No usable LME aluminum monthly bid/ask quotes were found.")

    out["forward_price"] = (out["bid"] + out["ask"]) / 2.0
    return (
        out[["expiry", "contract", "bid", "ask", "forward_price"]]
        .sort_values("expiry")
        .reset_index(drop=True)
    )
