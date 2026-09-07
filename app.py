from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lme_data import fetch_lme_aluminum_monthly_curve
from market_logic import Snapshot, build_snapshot_from_frames, generate_demo_market_data

APP_TITLE = "Aluminum Market Outlook"
BASE_OUTLOOK_DELTA = 0.50
DEFAULT_ADVERSE_DELTA = 0.35
HISTORICAL_CURVE_PATH = Path("data/barchart_cme_aluminum_2026-09-04.csv")
ILLUSTRATIVE_OPTIONS_PATH = Path("data/illustrative_options_2026-09-04.csv")

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
.disclosure-card { background:#f5f7fa; border:1px solid #dfe5ec; border-radius:12px; padding:.85rem 1rem; margin:.25rem 0 1rem 0; color:#5a6575; font-size:.84rem; line-height:1.5; }
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
    "base": "#8A96A8",
    "adverse": "#C58A21",
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


def make_historical_price_chart(base_summary: pd.DataFrame, adverse_summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=adverse_summary["expiry"], y=adverse_summary["current_lock_in_price"], mode="lines+markers",
        name="Current Lock-In Price", line=dict(color=COLORS["lock"], width=3), marker=dict(size=7),
        hovertemplate="%{x|%b %Y}<br>Lock-In: $%{y:,.0f}/t<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=base_summary["expiry"], y=base_summary["market_implied_price_scenario"], mode="lines+markers",
        name="Base Market Outlook (50Δ)", line=dict(color=COLORS["base"], width=2, dash="dot"), marker=dict(size=6),
        hovertemplate="%{x|%b %Y}<br>Base outlook: $%{y:,.0f}/t<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=adverse_summary["expiry"], y=adverse_summary["market_implied_price_scenario"], mode="lines+markers",
        name="Adverse Cost Scenario", line=dict(color=COLORS["adverse"], width=3), marker=dict(size=8),
        fill="tonexty", fillcolor=COLORS["fill"],
        hovertemplate="%{x|%b %Y}<br>Adverse scenario: $%{y:,.0f}/t<extra></extra>",
    ))
    fig.update_layout(height=440, paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=20,r=20,t=20,b=20),
                      hovermode="x unified", legend=dict(orientation="h", y=1.03),
                      font=dict(family="Arial, sans-serif", color=COLORS["text"]))
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="USD per tonne", tickprefix="$", separatethousands=True, gridcolor=COLORS["grid"], zeroline=False)
    return fig


def make_price_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=summary["expiry"], y=summary["current_lock_in_price"], mode="lines+markers",
        name="Current Lock-In Price", line=dict(color=COLORS["lock"], width=3), marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=summary["expiry"], y=summary["market_implied_price_scenario"], mode="lines+markers",
        name="Market-Implied Outlook", line=dict(color=COLORS["adverse"], width=3), marker=dict(size=8),
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


def load_historical_snapshot(target_delta: float) -> Snapshot:
    curve = load_historical_curve()
    futures = curve[["expiry", "forward_price"]].copy()
    options = pd.read_csv(ILLUSTRATIVE_OPTIONS_PATH)
    return build_snapshot_from_frames(futures, options, target_delta, "Real CME futures + illustrative synthetic options")


def build_snapshot_from_inputs(source_mode: str, target_delta: float, futures_upload, options_upload) -> Snapshot:
    if source_mode == "Demo data":
        seed = int(datetime.now(timezone.utc).timestamp() // 60)
        futures, options = generate_demo_market_data(seed=seed)
        return build_snapshot_from_frames(futures, options, target_delta, "Illustrative demo data")
    if futures_upload is None or options_upload is None:
        raise ValueError("Upload both the futures CSV and options CSV before refreshing.")
    return build_snapshot_from_frames(pd.read_csv(futures_upload), pd.read_csv(options_upload), target_delta, "Uploaded CSV snapshot")


def render_decision_table(summary: pd.DataFrame, outlook_label: str = "Market-Implied Outlook") -> None:
    table = summary.copy()
    table["Procurement Period"] = table["expiry"].dt.strftime("%b %Y")
    table["Current Lock-In Price"] = table["current_lock_in_price"]
    table[outlook_label] = table["market_implied_price_scenario"]
    table["Potential Hedge Protection"] = table["potential_hedge_protection"]
    table["Potential Hedge Protection %"] = table["potential_hedge_protection_pct"] * 100
    st.dataframe(
        table[["Procurement Period", "Current Lock-In Price", outlook_label, "Potential Hedge Protection", "Potential Hedge Protection %"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Lock-In Price": st.column_config.NumberColumn(format="$%.0f /t"),
            outlook_label: st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection": st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


def render_historical_snapshot(adverse_delta: float) -> None:
    base_snap = load_historical_snapshot(BASE_OUTLOOK_DELTA)
    adverse_snap = load_historical_snapshot(adverse_delta)
    base_summary = base_snap.summary
    summary = adverse_snap.summary
    strongest = summary.loc[summary["potential_hedge_protection_pct"].idxmax()]
    nearest = summary.iloc[0]
    average_protection = summary["potential_hedge_protection_pct"].mean()

    st.markdown("<span class='snapshot-pill'>Historical CME aluminum snapshot · Sep 4, 2026 · real futures + illustrative options</span>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='insight-card'>
        <div class='insight-label'>What stands out</div>
        <div class='insight-text'>In this demonstration, the selected adverse-cost scenario implies as much as <b>{strongest['potential_hedge_protection_pct']:.1%}</b> (<b>${strongest['potential_hedge_protection']:,.0f}/t</b>) of potential hedge protection in <b>{strongest['expiry'].strftime('%b %Y')}</b>. This is scenario protection, not expected savings.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='disclosure-card'><b>Demonstration disclosure:</b> The CME aluminum futures curve is a real Sep. 4, 2026 historical market snapshot sourced from Barchart. Both option-derived curves are synthetic placeholders. The 50-delta line is shown as a base market outlook; the selected lower-delta line is an adverse cost scenario used to illustrate risk protection. Neither should be interpreted as expected savings.</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Near-Term Lock-In Price", f"${nearest['current_lock_in_price']:,.0f}/t")
    c2.metric("Near-Term Adverse Cost Scenario", f"${nearest['market_implied_price_scenario']:,.0f}/t")
    c3.metric("Average Scenario Protection", f"{average_protection:.1%}")

    st.markdown("<div class='section-kicker'>Primary View</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Lock-in price vs. option-implied scenarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>The 50-delta line is a base outlook. The adverse-cost line uses a lower-delta scenario to show a plausible higher-cost outcome worth protecting against.</div>", unsafe_allow_html=True)
    st.plotly_chart(make_historical_price_chart(base_summary, summary), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-kicker'>Decision Support</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Potential hedge protection under the adverse cost scenario</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>This measures protection if that adverse scenario occurs. It is deliberately not labeled as expected savings.</div>", unsafe_allow_html=True)
    st.plotly_chart(make_protection_chart(summary), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-kicker'>Detail</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Procurement decision table</div>", unsafe_allow_html=True)
    render_decision_table(summary, "Illustrative Adverse Cost Scenario")

    st.markdown("<div class='small-note'>Futures source: Barchart public delayed CME/COMEX aluminum market pages, historical snapshot dated Sep. 4, 2026. Options layer: synthetic POC data. Production would replace the synthetic layer with licensed/live options data and calibrate scenario thresholds to the company's risk tolerance.</div>", unsafe_allow_html=True)


def render_live_lme(refresh: bool) -> None:
    if refresh or "live_curve" not in st.session_state:
        st.session_state.live_curve = refresh_live_curve()
        st.session_state.live_refreshed = datetime.now().astimezone()
    curve = st.session_state.live_curve
    refreshed = st.session_state.live_refreshed
    nearest = curve.iloc[0]
    farthest = curve.iloc[-1]
    curve_change = farthest["forward_price"] / nearest["forward_price"] - 1
    st.markdown(f"<span class='snapshot-pill'>LME public market data · delayed ≥15 minutes · refreshed {refreshed.strftime('%b %d, %Y · %I:%M %p %Z')}</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Nearest Lock-In Reference", f"${nearest['forward_price']:,.0f}/t")
    c2.metric("Farthest Displayed Contract", f"${farthest['forward_price']:,.0f}/t")
    c3.metric("Curve Change", f"{curve_change:+.1%}")
    st.markdown("<div class='section-kicker'>Live Market</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>LME aluminum monthly futures curve</div>", unsafe_allow_html=True)
    st.plotly_chart(make_curve_chart(curve), use_container_width=True, config={"displayModeBar": False})


def render_generic_snapshot(snap: Snapshot) -> None:
    summary = snap.summary
    strongest = summary.loc[summary["potential_hedge_protection_pct"].idxmax()]
    nearest = summary.iloc[0]
    st.markdown(f"<span class='snapshot-pill'>{snap.source_label}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='insight-card'><div class='insight-label'>What stands out</div><div class='insight-text'>The largest modeled hedge-protection opportunity is <b>{strongest['potential_hedge_protection_pct']:.1%}</b> in <b>{strongest['expiry'].strftime('%b %Y')}</b>.</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Near-Term Lock-In Price", f"${nearest['current_lock_in_price']:,.0f}/t")
    c2.metric("Near-Term Market Outlook", f"${nearest['market_implied_price_scenario']:,.0f}/t")
    c3.metric("Average Potential Hedge Protection", f"{summary['potential_hedge_protection_pct'].mean():.1%}")
    st.plotly_chart(make_price_chart(summary), use_container_width=True, config={"displayModeBar": False})
    st.plotly_chart(make_protection_chart(summary), use_container_width=True, config={"displayModeBar": False})
    render_decision_table(summary)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="◼", layout="wide")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Dashboard Controls")
        source_mode = st.radio("Data mode", ["Historical CME + illustrative options", "Live LME futures", "Demo data", "Upload CSVs"], index=0)
        adverse_delta = st.slider(
            "Adverse cost scenario",
            min_value=0.25,
            max_value=0.45,
            value=DEFAULT_ADVERSE_DELTA,
            step=0.05,
            help="Lower delta = less likely but more severe higher-cost scenario. The base outlook remains fixed at 50 delta.",
        )

        futures_upload = None
        options_upload = None
        if source_mode == "Upload CSVs":
            futures_upload = st.file_uploader("Futures / forwards CSV", type="csv")
            options_upload = st.file_uploader("Call options CSV", type="csv")

        if source_mode == "Historical CME + illustrative options":
            st.caption("Default executive-demo mode: real Sep. 4, 2026 CME aluminum futures with synthetic 50-delta base and adverse-cost option scenarios.")
        elif source_mode == "Live LME futures":
            st.caption("Live delayed LME futures only. No options-derived outlook is shown in this mode.")

    left, right = st.columns([4.2, 1.15])
    with left:
        st.markdown("<div class='hero-eyebrow'>Commodity Risk Dashboard</div>", unsafe_allow_html=True)
        st.markdown(f"# {APP_TITLE}")
        st.markdown("<div class='hero-copy'>A management view of aluminum prices available to lock, compared with probability-based price-risk scenarios.</div>", unsafe_allow_html=True)
    with right:
        st.write("")
        st.write("")
        refresh = st.button("Refresh Market Data", type="primary", use_container_width=True)

    if source_mode == "Historical CME + illustrative options":
        render_historical_snapshot(adverse_delta)
        return
    if source_mode == "Live LME futures":
        try:
            render_live_lme(refresh)
        except Exception as exc:
            st.error(f"Could not refresh LME data: {exc}")
        return

    if refresh or "snapshot" not in st.session_state:
        try:
            st.session_state.snapshot = build_snapshot_from_inputs(source_mode, adverse_delta, futures_upload, options_upload)
        except Exception as exc:
            st.error(str(exc))
            st.stop()
    render_generic_snapshot(st.session_state.snapshot)


if __name__ == "__main__":
    main()
