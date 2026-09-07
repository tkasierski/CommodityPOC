from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lme_data import fetch_lme_aluminum_monthly_curve
from market_logic import Snapshot, build_snapshot_from_frames, generate_demo_market_data

APP_TITLE = "Aluminum Market Outlook"
DEFAULT_TARGET_DELTA = 0.50
HISTORICAL_CURVE_PATH = Path("data/barchart_cme_aluminum_2026-09-04.csv")

PAGE_CSS = """
<style>
.stApp { background:#f6f8fb; color:#1f2937; }
.block-container { max-width:1220px; padding-top:2rem; padding-bottom:3rem; }
h1,h2,h3 { color:#172033; letter-spacing:-0.02em; }
div[data-testid="stSidebar"] { background:#fff; border-right:1px solid #e8edf3; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #e5eaf0; border-radius:14px; padding:1rem 1.1rem; }
.hero-eyebrow { color:#64748b; font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
.hero-copy { color:#526072; font-size:.98rem; line-height:1.55; max-width:900px; }
.insight-card { background:#fffaf0; border:1px solid #f0dfb8; border-left:5px solid #c58a21; border-radius:14px; padding:1rem 1.2rem; margin:.35rem 0 1rem 0; }
.insight-label { color:#8a5f13; font-size:.76rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
.insight-text { color:#3e4653; font-size:.96rem; line-height:1.5; }
.section-kicker { color:#7a8699; font-size:.78rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; margin-top:.45rem; }
.section-title { color:#172033; font-size:1.23rem; font-weight:700; }
.section-subtitle { color:#667085; font-size:.9rem; margin-bottom:.55rem; }
.snapshot-pill { display:inline-block; background:#eef3f8; color:#536174; border-radius:999px; padding:.34rem .68rem; font-size:.78rem; margin-bottom:.4rem; }
.small-note { color:#7a8699; font-size:.79rem; line-height:1.45; }
div.stButton > button { border-radius:10px; font-weight:650; min-height:2.6rem; }
</style>
"""

COLORS = {
    "lock": "#5E6C84",
    "outlook": "#C58A21",
    "fill": "rgba(197,138,33,.10)",
    "bar": "#7C91B2",
    "grid": "#E8EDF3",
    "text": "#475467",
}


def make_curve_chart(curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve["expiry"], y=curve["forward_price"], mode="lines+markers",
        name="Current Lock-In Price", line=dict(color=COLORS["lock"], width=3), marker=dict(size=8),
        hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}/t<extra></extra>",
    ))
    fig.update_layout(height=390, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=20,r=20,t=20,b=20), showlegend=False,
                      font=dict(family="Arial, sans-serif", color=COLORS["text"]))
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="USD per tonne", tickprefix="$", separatethousands=True,
                     gridcolor=COLORS["grid"], zeroline=False)
    return fig


def make_price_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=summary["expiry"], y=summary["current_lock_in_price"], mode="lines+markers",
        name="Current Lock-In Price", line=dict(color=COLORS["lock"], width=3), marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=summary["expiry"], y=summary["market_implied_price_scenario"], mode="lines+markers",
        name="Market-Implied Price Outlook", line=dict(color=COLORS["outlook"], width=3), marker=dict(size=8),
        fill="tonexty", fillcolor=COLORS["fill"],
    ))
    fig.update_layout(height=430, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=20,r=20,t=20,b=20),
                      hovermode="x unified", legend=dict(orientation="h", y=1.03),
                      font=dict(family="Arial, sans-serif", color=COLORS["text"]))
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="USD per tonne", tickprefix="$", separatethousands=True, gridcolor=COLORS["grid"], zeroline=False)
    return fig


def make_protection_chart(summary: pd.DataFrame) -> go.Figure:
    pct = summary["potential_hedge_protection_pct"] * 100
    fig = go.Figure(go.Bar(
        x=summary["expiry"], y=pct, marker_color=COLORS["bar"],
        text=pct.map(lambda x: f"{x:.1f}%"), textposition="outside",
        hovertemplate="%{x|%b %Y}<br>Potential protection: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(height=315, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=20,r=20,t=20,b=20),
                      font=dict(family="Arial, sans-serif", color=COLORS["text"]))
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="Protection vs. lock-in", ticksuffix="%", gridcolor=COLORS["grid"], zeroline=False)
    return fig


def refresh_live_curve() -> pd.DataFrame:
    curve = fetch_lme_aluminum_monthly_curve()
    curve["expiry"] = pd.to_datetime(curve["expiry"])
    return curve


def load_historical_curve() -> pd.DataFrame:
    curve = pd.read_csv(HISTORICAL_CURVE_PATH)
    curve["expiry"] = pd.to_datetime(curve["contract_month"] + "-01") + pd.offsets.MonthEnd(0)
    return curve.sort_values("expiry").reset_index(drop=True)


def build_snapshot_from_inputs(source_mode: str, target_delta: float, futures_upload, options_upload) -> Snapshot:
    if source_mode == "Demo data":
        seed = int(datetime.now(timezone.utc).timestamp() // 60)
        futures, options = generate_demo_market_data(seed=seed)
        return build_snapshot_from_frames(futures, options, target_delta, "Illustrative demo data")

    if futures_upload is None or options_upload is None:
        raise ValueError("Upload both the futures CSV and options CSV before refreshing.")
    return build_snapshot_from_frames(
        pd.read_csv(futures_upload), pd.read_csv(options_upload), target_delta, "Uploaded CSV snapshot"
    )


def render_curve_table(curve: pd.DataFrame, historical: bool = False) -> None:
    if historical:
        table = curve[["contract_month", "barchart_symbol", "forward_price"]].copy()
        table = table.rename(columns={
            "contract_month": "Contract Month",
            "barchart_symbol": "Barchart Symbol",
            "forward_price": "Historical Futures Price",
        })
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={"Historical Futures Price": st.column_config.NumberColumn(format="$%.2f /t")},
        )
        return

    display_cols = [c for c in ["expiry", "contract", "bid", "ask", "forward_price"] if c in curve.columns]
    table = curve[display_cols].copy()
    if "expiry" in table:
        table["expiry"] = pd.to_datetime(table["expiry"]).dt.strftime("%b %Y")
    table = table.rename(columns={
        "expiry": "Contract Month", "contract": "LME Contract", "bid": "Bid", "ask": "Ask", "forward_price": "Mid / Lock-In Reference"
    })
    st.dataframe(table, use_container_width=True, hide_index=True,
                 column_config={
                     "Bid": st.column_config.NumberColumn(format="$%.0f /t"),
                     "Ask": st.column_config.NumberColumn(format="$%.0f /t"),
                     "Mid / Lock-In Reference": st.column_config.NumberColumn(format="$%.0f /t"),
                 })


def render_historical_snapshot() -> None:
    curve = load_historical_curve()
    nearest = curve.iloc[0]
    farthest = curve.iloc[-1]
    peak = curve.loc[curve["forward_price"].idxmax()]
    curve_change = farthest["forward_price"] / nearest["forward_price"] - 1

    st.markdown(
        "<span class='snapshot-pill'>Historical CME aluminum snapshot · Sep 4, 2026 · sourced from Barchart delayed market pages</span>",
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div class='insight-card'>
        <div class='insight-label'>Historical market snapshot</div>
        <div class='insight-text'>These are real CME aluminum futures prices captured from Barchart for the Sep. 4, 2026 market snapshot. The archived option-chain rows were not reproducibly accessible from the public page, so this mode intentionally does <b>not</b> display a fabricated options-derived outlook.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sep 2026 Futures", f"${nearest['forward_price']:,.2f}/t")
    c2.metric("Peak Displayed Contract", f"${peak['forward_price']:,.2f}/t", peak["contract_month"])
    c3.metric("Sep '26 to Aug '27 Curve", f"{curve_change:+.1%}")

    st.markdown("<div class='section-kicker'>Historical Market</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>CME aluminum futures curve — Sep. 4, 2026</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>A real dated market curve for the executive POC. Production would refresh from a licensed futures/options feed.</div>", unsafe_allow_html=True)
    st.plotly_chart(make_curve_chart(curve), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-title'>Contract detail</div>", unsafe_allow_html=True)
    render_curve_table(curve, historical=True)
    st.markdown(
        "<div class='small-note'>Source: Barchart public delayed CME/COMEX aluminum futures pages, snapshot dated Sep. 4, 2026. Prices are reference market data for demonstration, not executable quotes.</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="◼", layout="wide")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Dashboard Controls")
        source_mode = st.radio(
            "Data mode",
            ["Historical CME snapshot", "Live LME futures", "Demo data", "Upload CSVs"],
            index=0,
        )
        target_delta = st.slider("Options outlook setting", 0.10, 0.90, DEFAULT_TARGET_DELTA, 0.05)

        futures_upload = None
        options_upload = None
        if source_mode == "Upload CSVs":
            futures_upload = st.file_uploader("Futures / forwards CSV", type="csv")
            options_upload = st.file_uploader("Call options CSV", type="csv")

        if source_mode == "Live LME futures":
            st.caption("Live mode uses LME public monthly futures quotes, delayed at least 15 minutes. The options-based outlook is intentionally disabled until a valid options chain is available.")
        elif source_mode == "Historical CME snapshot":
            st.caption("This mode uses a real Sep. 4, 2026 Barchart CME aluminum futures snapshot. Options remain disabled because archived public chain rows could not be captured reliably.")

    left, right = st.columns([4.2, 1.15])
    with left:
        st.markdown("<div class='hero-eyebrow'>Commodity Risk Dashboard</div>", unsafe_allow_html=True)
        st.markdown(f"# {APP_TITLE}")
        st.markdown("<div class='hero-copy'>A management view of aluminum prices available to lock, with an option-derived risk layer when valid options data is supplied.</div>", unsafe_allow_html=True)
    with right:
        st.write("")
        st.write("")
        refresh = st.button("Refresh Market Data", type="primary", use_container_width=True)

    if source_mode == "Historical CME snapshot":
        render_historical_snapshot()
        return

    if source_mode == "Live LME futures":
        if refresh or "live_curve" not in st.session_state:
            try:
                st.session_state.live_curve = refresh_live_curve()
                st.session_state.live_refreshed = datetime.now().astimezone()
            except Exception as exc:
                st.error(f"Could not refresh LME data: {exc}")
                st.stop()

        curve = st.session_state.live_curve
        refreshed = st.session_state.live_refreshed
        nearest = curve.iloc[0]
        farthest = curve.iloc[-1]
        curve_change = farthest["forward_price"] / nearest["forward_price"] - 1

        st.markdown(f"<span class='snapshot-pill'>LME public market data · delayed ≥15 minutes · refreshed {refreshed.strftime('%b %d, %Y · %I:%M %p %Z')}</span>", unsafe_allow_html=True)

        st.markdown("""
        <div class='insight-card'>
            <div class='insight-label'>Current state</div>
            <div class='insight-text'>This view uses real delayed LME aluminum futures quotes. The option-implied risk layer is not shown because a reliable free automated aluminum options feed has not been identified.</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Nearest Lock-In Reference", f"${nearest['forward_price']:,.0f}/t")
        c2.metric("Farthest Displayed Contract", f"${farthest['forward_price']:,.0f}/t")
        c3.metric("Curve Change", f"{curve_change:+.1%}")

        st.markdown("<div class='section-kicker'>Live Market</div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>LME aluminum monthly futures curve</div>", unsafe_allow_html=True)
        st.markdown("<div class='section-subtitle'>Midpoint of public LME bid/ask quotes for the first six monthly contracts.</div>", unsafe_allow_html=True)
        st.plotly_chart(make_curve_chart(curve), use_container_width=True, config={"displayModeBar": False})

        st.markdown("<div class='section-title'>Contract detail</div>", unsafe_allow_html=True)
        render_curve_table(curve)
        st.markdown("<div class='small-note'>Source: London Metal Exchange public delayed monthly futures quotes. This is a market-data reference for the POC, not an executable dealer quote.</div>", unsafe_allow_html=True)
        return

    if refresh or "snapshot" not in st.session_state:
        try:
            st.session_state.snapshot = build_snapshot_from_inputs(source_mode, target_delta, futures_upload, options_upload)
            st.session_state.snapshot_target_delta = target_delta
        except Exception as exc:
            st.error(str(exc))
            st.stop()

    snap: Snapshot = st.session_state.snapshot
    summary = snap.summary
    strongest = summary.loc[summary["potential_hedge_protection_pct"].idxmax()]

    st.markdown(f"<span class='snapshot-pill'>Refreshed {snap.refreshed_at.strftime('%b %d, %Y · %I:%M %p %Z')} · {snap.source_label}</span>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='insight-card'>
        <div class='insight-label'>What stands out</div>
        <div class='insight-text'>The largest modeled hedge-protection opportunity is <b>{strongest['potential_hedge_protection_pct']:.1%}</b> in <b>{strongest['expiry'].strftime('%b %Y')}</b>.</div>
    </div>
    """, unsafe_allow_html=True)

    nearest = summary.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Near-Term Lock-In Price", f"${nearest['current_lock_in_price']:,.0f}/t")
    c2.metric("Near-Term Market Outlook", f"${nearest['market_implied_price_scenario']:,.0f}/t")
    c3.metric("Average Potential Hedge Protection", f"{summary['potential_hedge_protection_pct'].mean():.1%}")

    st.markdown("<div class='section-kicker'>Primary View</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Lock-in price vs. market-implied outlook</div>", unsafe_allow_html=True)
    st.plotly_chart(make_price_chart(summary), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-title'>Potential hedge protection by procurement period</div>", unsafe_allow_html=True)
    st.plotly_chart(make_protection_chart(summary), use_container_width=True, config={"displayModeBar": False})

    table = summary.copy()
    table["Procurement Period"] = table["expiry"].dt.strftime("%b %Y")
    table["Current Lock-In Price"] = table["current_lock_in_price"]
    table["Market-Implied Price Outlook"] = table["market_implied_price_scenario"]
    table["Potential Hedge Protection"] = table["potential_hedge_protection"]
    table["Potential Hedge Protection %"] = table["potential_hedge_protection_pct"]
    st.dataframe(table[["Procurement Period", "Current Lock-In Price", "Market-Implied Price Outlook", "Potential Hedge Protection", "Potential Hedge Protection %"]],
                 use_container_width=True, hide_index=True,
                 column_config={
                     "Current Lock-In Price": st.column_config.NumberColumn(format="$%.0f /t"),
                     "Market-Implied Price Outlook": st.column_config.NumberColumn(format="$%.0f /t"),
                     "Potential Hedge Protection": st.column_config.NumberColumn(format="$%.0f /t"),
                     "Potential Hedge Protection %": st.column_config.NumberColumn(format="%.1f%%"),
                 })


if __name__ == "__main__":
    main()
