import pandas as pd

from market_logic import select_market_implied_scenario, validate_futures, validate_options


def test_selects_closest_delta_and_calculates_protection():
    futures = validate_futures(pd.DataFrame({
        "expiry": ["2026-10-31"],
        "forward_price": [2600.0],
    }))
    options = validate_options(pd.DataFrame({
        "expiry": ["2026-10-31", "2026-10-31", "2026-10-31"],
        "strike": [2600.0, 2650.0, 2700.0],
        "call_delta": [0.55, 0.49, 0.42],
    }))
    result = select_market_implied_scenario(futures, options, 0.50).iloc[0]
    assert result["market_implied_price_scenario"] == 2650.0
    assert result["potential_hedge_protection"] == 50.0
    assert round(result["potential_hedge_protection_pct"], 6) == round(50 / 2600, 6)
