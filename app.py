from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_logic import (
    Snapshot,
    build_snapshot_from_frames,
    generate_demo_market_data,
)

APP_TITLE = "Aluminum Market-Implied Price Outlook"
DEFAULT_TARGET_DELTA = 0.50


def make_price_chart(summary: pd.DataFrame, target_delta: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=summary["expiry"],
            y=summary["current_lock_in_price"],
            mode="lines+markers",
            name="Current Lock-In Price",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary["expiry"],
            y=summary["market_implied_price_scenario"],
            mode="lines+markers",
            name="Market-Implied Price Outlook",
        )
    )
    fig.update_layout(
        title=f"Current Lock-In Price vs. {target_delta:.0%}-Delta Market-Implied Outlook",
        xaxis_title="Procurement / option expiry",
        yaxis_title="USD per tonne",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


def make_protection_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary["expiry"],
            y=summary["potential_hedge_protection_pct"] * 100,
            name="Potential Hedge Protection %",
            text=(summary["potential_hedge_protection_pct"] * 100).map(lambda x: f"{x:.1f}%"),
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Potential Hedge Protection vs. Current Lock-In Price",
        xaxis_title="Procurement / option expiry",
        yaxis_title="Percent",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.update_yaxes(ticksuffix="%")
    return fig


def build_snapshot(source_mode: str, target_delta: float, futures_upload, options_upload) -> Snapshot:
    if source_mode == "Demo data":
        seed = int(datetime.now(timezone.utc).timestamp() // 60)
        futures, options = generate_demo_market_data(seed=seed)
        return build_snapshot_from_frames(futures, options, target_delta, "Illustrative demo data")
    if futures_upload is None or options_upload is None:
        raise ValueError("Upload both the futures CSV and options CSV before refreshing.")
    futures = pd.read_csv(futures_upload)
    options = pd.read_csv(options_upload)
    return build_snapshot_from_frames(futures, options, target_delta, "Uploaded CSV snapshot")


def format_summary(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    out["Procurement Period"] = out["expiry"].dt.strftime("%b %Y")
    out["Current Lock-In Price"] = out["current_lock_in_price"]
    out["Market-Implied Price Scenario"] = out["market_implied_price_scenario"]
    out["Potential Hedge Protection"] = out["potential_hedge_protection"]
    out["Potential Hedge Protection %"] = out["potential_hedge_protection_pct"]
    out["Selected Call Delta"] = out["selected_call_delta"]
    return out[
        [
            "Procurement Period",
            "Current Lock-In Price",
            "Market-Implied Price Scenario",
            "Potential Hedge Protection",
            "Potential Hedge Protection %",
            "Selected Call Delta",
        ]
    ]


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption(
        "A management-oriented view of the price available to lock today versus an option-implied higher-cost scenario. "
        "The option-implied line is probability-based and is not a deterministic forecast."
    )

    with st.sidebar:
        st.header("Settings")
        source_mode = st.radio("Market data source", ["Demo data", "Upload CSVs"], index=0)
        target_delta = st.slider(
            "Call delta used for market-implied outlook",
            min_value=0.10,
            max_value=0.90,
            value=DEFAULT_TARGET_DELTA,
            step=0.05,
            help="The app selects the call strike with delta closest to this value for each expiry.",
        )

        futures_upload = None
        options_upload = None
        if source_mode == "Upload CSVs":
            st.markdown("**Futures CSV columns**: `expiry`, `forward_price`")
            futures_upload = st.file_uploader("Upload futures / forwards CSV", type="csv")
            st.markdown("**Options CSV columns**: `expiry`, `strike`, `call_delta`")
            options_upload = st.file_uploader("Upload call options CSV", type="csv")

        st.divider()
        st.caption("POC methodology: use the call strike nearest the selected delta as the market-implied price scenario.")

    left, right = st.columns([3, 1])
    with left:
        if "snapshot" in st.session_state:
            snap = st.session_state.snapshot
            st.caption(
                f"Last refreshed: {snap.refreshed_at.strftime('%b %d, %Y %I:%M:%S %p %Z')} | Source: {snap.source_label}"
            )
        else:
            st.caption("No snapshot loaded yet.")

    with right:
        refresh = st.button("Refresh Market Data", type="primary", use_container_width=True)

    if refresh or "snapshot" not in st.session_state:
        try:
            st.session_state.snapshot = build_snapshot(
                source_mode=source_mode,
                target_delta=target_delta,
                futures_upload=futures_upload,
                options_upload=options_upload,
            )
            st.session_state.snapshot_target_delta = target_delta
        except Exception as exc:
            st.error(str(exc))
            st.stop()

    snap: Snapshot = st.session_state.snapshot

    if st.session_state.get("snapshot_target_delta") != target_delta:
        st.info("The delta setting has changed. Click **Refresh Market Data** to recalculate the snapshot.")

    summary = snap.summary
    nearest = summary.iloc[0]
    farthest = summary.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nearest Lock-In Price", f"${nearest['current_lock_in_price']:,.0f}/t")
    c2.metric("Nearest Market-Implied Price", f"${nearest['market_implied_price_scenario']:,.0f}/t")
    c3.metric("Nearest Hedge Protection", f"${nearest['potential_hedge_protection']:,.0f}/t")
    c4.metric("Farthest Hedge Protection", f"{farthest['potential_hedge_protection_pct']:.1%}")

    st.plotly_chart(make_price_chart(summary, st.session_state.snapshot_target_delta), use_container_width=True)
    st.plotly_chart(make_protection_chart(summary), use_container_width=True)

    st.subheader("Decision Table")
    display = format_summary(summary)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Lock-In Price": st.column_config.NumberColumn(format="$%.0f /t"),
            "Market-Implied Price Scenario": st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection": st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection %": st.column_config.NumberColumn(format="%.1f%%"),
            "Selected Call Delta": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    st.caption(
        "Interpretation: the larger the gap between the current lock-in price and the market-implied price scenario, "
        "the greater the potential protection from hedging today if the adverse price scenario materializes. "
        "Option delta is used as a simple POC proxy and should not be read as an exact real-world probability."
    )

    with st.expander("Methodology & data requirements"):
        st.markdown(
            """
**Current Lock-In Price**  
The futures or forward price for the relevant procurement period.

**Market-Implied Price Scenario**  
For each expiry, the app selects the call strike whose delta is closest to the chosen target delta (default: 0.50).

**Potential Hedge Protection**  
`Market-Implied Price Scenario - Current Lock-In Price`

**Potential Hedge Protection %**  
`Potential Hedge Protection / Current Lock-In Price`

This proof of concept deliberately prioritizes a transparent, intuitive calculation. A production version could replace the delta proxy with a fully calibrated risk-neutral distribution, add regional premiums / basis, and connect directly to a market-data API.
            """
        )


if __name__ == "__main__":
    main()
