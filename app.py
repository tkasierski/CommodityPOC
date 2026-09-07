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
HEDGE_SIGNAL_THRESHOLD_PP = 0.75
HISTORICAL_CURVE_PATH = Path("data/barchart_cme_aluminum_2026-09-04.csv")
HISTORICAL_SPOT_PATH = Path("data/barchart_cme_aluminum_cash_2026-09-04.csv")
ILLUSTRATIVE_OPTIONS_PATH = Path("data/illustrative_options_2026-09-04.csv")
NORMAL_GAP_PATH = Path("data/illustrative_normal_gap_35delta.csv")

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
.signal-card { background:#f1f7f3; border:1px solid #cfe2d5; border-left:6px solid #4f7d5d; border-radius:14px; padding:1.05rem 1.25rem; margin:.45rem 0 1rem 0; }
.signal-card.no-signal { background:#f7f8fa; border-color:#e2e6eb; border-left-color:#8894a5; }
.signal-label { color:#486b53; font-size:.76rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
.signal-title { color:#1f3526; font-size:1.25rem; font-weight:750; margin-top:.15rem; }
.signal-copy { color:#4b5c50; font-size:.92rem; line-height:1.5; margin-top:.2rem; }
.math-card { background:#ffffff; border:1px solid #e2e7ed; border-radius:14px; padding:1rem 1.2rem; margin:.35rem 0 1rem 0; }
.math-title { color:#344054; font-size:.9rem; font-weight:750; margin-bottom:.35rem; }
.math-copy { color:#667085; font-size:.86rem; line-height:1.6; }
.section-kicker { color:#7a8699; font-size:.78rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; margin-top:.45rem; }
.section-title { color:#172033; font-size:1.23rem; font-weight:700; }
.section-subtitle { color:#667085; font-size:.9rem; margin-bottom:.55rem; }
.snapshot-pill { display:inline-block; background:#eef3f8; color:#536174; border-radius:999px; padding:.34rem .68rem; font-size:.78rem; margin-bottom:.4rem; }
.small-note { color:#7a8699; font-size:.79rem; line-height:1.45; }
div.stButton > button { border-radius:10px; font-weight:650; min-height:2.6rem; }
</style>
"""

COLORS = {
    "spot": "#344054",
    "lock": "#5E6C84",
    "base": "#8A96A8",
    "adverse": "#C58A21",
    "fill": "rgba(197,138,33,.10)",
    "normal": "#A3ACB9",
    "grid": "#E8EDF3",
    "text": "#475467",
}


def load_historical_curve() -> pd.DataFrame:
    curve = pd.read_csv(HISTORICAL_CURVE_PATH)
    curve["expiry"] = pd.to_datetime(curve["contract_month"] + "-01") + pd.offsets.MonthEnd(0)
    return curve.sort_values("expiry").reset_index(drop=True)


def load_historical_spot() -> float:
    return float(pd.read_csv(HISTORICAL_SPOT_PATH).iloc[0]["spot_price"])


def load_historical_snapshot(target_delta: float) -> Snapshot:
    curve = load_historical_curve()
    futures = curve[["expiry", "forward_price"]].copy()
    options = pd.read_csv(ILLUSTRATIVE_OPTIONS_PATH)
    return build_snapshot_from_frames(
        futures, options, target_delta, "Real CME futures + illustrative synthetic options"
    )


def make_historical_price_chart(base_summary: pd.DataFrame, adverse_summary: pd.DataFrame, spot_price: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=adverse_summary["expiry"],
        y=adverse_summary["current_lock_in_price"],
        mode="lines+markers",
        name="Forward / Lock-In Price",
        line=dict(color=COLORS["lock"], width=3),
        marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=base_summary["expiry"],
        y=base_summary["market_implied_price_scenario"],
        mode="lines+markers",
        name="Base Market Outlook (50Δ)",
        line=dict(color=COLORS["base"], width=2, dash="dot"),
        marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=adverse_summary["expiry"],
        y=adverse_summary["market_implied_price_scenario"],
        mode="lines+markers",
        name="Adverse Cost Scenario (35Δ)",
        line=dict(color=COLORS["adverse"], width=3),
        marker=dict(size=8),
        fill="tonexty",
        fillcolor=COLORS["fill"],
    ))
    fig.add_hline(
        y=spot_price,
        line_dash="dash",
        line_color=COLORS["spot"],
        annotation_text=f"Spot ${spot_price:,.0f}/t",
        annotation_position="bottom right",
    )
    fig.update_layout(
        height=455,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.03),
        font=dict(family="Arial, sans-serif", color=COLORS["text"]),
    )
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="USD per tonne", tickprefix="$", separatethousands=True, gridcolor=COLORS["grid"], zeroline=False)
    return fig


def make_gap_vs_normal_chart(decision: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=decision["expiry"], y=decision["normal_gap_pct"] * 100,
        name="Normal Gap", marker_color=COLORS["normal"],
    ))
    fig.add_trace(go.Bar(
        x=decision["expiry"], y=decision["current_gap_pct"] * 100,
        name="Current Adverse Gap", marker_color=COLORS["adverse"],
    ))
    fig.update_layout(
        barmode="group", height=350, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", y=1.03),
        font=dict(family="Arial, sans-serif", color=COLORS["text"]),
    )
    fig.update_xaxes(showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(title="Gap vs. forward", ticksuffix="%", gridcolor=COLORS["grid"], zeroline=False)
    return fig


def build_decision_frame(summary: pd.DataFrame) -> pd.DataFrame:
    benchmark = pd.read_csv(NORMAL_GAP_PATH)
    benchmark["expiry"] = pd.to_datetime(benchmark["contract_month"] + "-01") + pd.offsets.MonthEnd(0)
    decision = summary.merge(benchmark[["expiry", "normal_gap_pct"]], on="expiry", how="left")
    decision["current_gap_pct"] = decision["potential_hedge_protection_pct"]
    decision["excess_gap_pp"] = (decision["current_gap_pct"] - decision["normal_gap_pct"]) * 100
    decision["hedge_signal"] = decision["excess_gap_pp"] >= HEDGE_SIGNAL_THRESHOLD_PP
    decision["decision"] = decision["hedge_signal"].map({True: "HEDGE SIGNAL", False: "No signal"})
    return decision


def render_signal_table(decision: pd.DataFrame) -> None:
    table = decision.copy()
    table["Procurement Period"] = table["expiry"].dt.strftime("%b %Y")
    table["Current Gap"] = table["current_gap_pct"] * 100
    table["Normal Gap"] = table["normal_gap_pct"] * 100
    table["Excess vs. Normal"] = table["excess_gap_pp"]
    table["Decision"] = table["decision"]
    st.dataframe(
        table[["Procurement Period", "Current Gap", "Normal Gap", "Excess vs. Normal", "Decision"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Gap": st.column_config.NumberColumn(format="%.1f%%"),
            "Normal Gap": st.column_config.NumberColumn(format="%.1f%%"),
            "Excess vs. Normal": st.column_config.NumberColumn(format="%+.1f pp"),
        },
    )


def render_decision_table(summary: pd.DataFrame, spot_price: float) -> None:
    table = summary.copy()
    table["Procurement Period"] = table["expiry"].dt.strftime("%b %Y")
    table["Spot Price"] = spot_price
    table["Forward / Lock-In"] = table["current_lock_in_price"]
    table["Forward vs. Spot %"] = (table["current_lock_in_price"] / spot_price - 1) * 100
    table["Adverse Cost Scenario"] = table["market_implied_price_scenario"]
    table["Scenario Protection"] = table["potential_hedge_protection"]
    table["Scenario Protection %"] = table["potential_hedge_protection_pct"] * 100
    st.dataframe(
        table[[
            "Procurement Period", "Spot Price", "Forward / Lock-In", "Forward vs. Spot %",
            "Adverse Cost Scenario", "Scenario Protection", "Scenario Protection %",
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Spot Price": st.column_config.NumberColumn(format="$%.0f /t"),
            "Forward / Lock-In": st.column_config.NumberColumn(format="$%.0f /t"),
            "Forward vs. Spot %": st.column_config.NumberColumn(format="%+.1f%%"),
            "Adverse Cost Scenario": st.column_config.NumberColumn(format="$%.0f /t"),
            "Scenario Protection": st.column_config.NumberColumn(format="$%.0f /t"),
            "Scenario Protection %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


def render_historical_snapshot(adverse_delta: float) -> None:
    base_summary = load_historical_snapshot(BASE_OUTLOOK_DELTA).summary
    summary = load_historical_snapshot(adverse_delta).summary
    spot_price = load_historical_spot()
    nearest = summary.iloc[0]
    nearest_forward_premium = nearest["current_lock_in_price"] / spot_price - 1
    average_protection = summary["potential_hedge_protection_pct"].mean()

    st.markdown(
        "<span class='snapshot-pill'>Historical CME aluminum snapshot · Sep 4, 2026 · real spot + futures + illustrative options</span>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class='disclosure-card'><b>Demonstration disclosure:</b> Spot and CME aluminum futures are real Sep. 4, 2026 historical market references sourced from Barchart. The option-derived scenarios and recent-history normalization are synthetic placeholders constructed solely to demonstrate the proposed production workflow.</div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Price", f"${spot_price:,.0f}/t")
    c2.metric("Near-Term Forward", f"${nearest['current_lock_in_price']:,.0f}/t", f"{nearest_forward_premium:+.1%} vs spot")
    c3.metric("Near-Term Adverse Scenario", f"${nearest['market_implied_price_scenario']:,.0f}/t")
    c4.metric("Average Scenario Protection", f"{average_protection:.1%}")

    st.markdown("<div class='section-kicker'>Market Context</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Spot today vs. what we can lock vs. what the options market could imply</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>Spot anchors the analysis at the current cash market. The forward curve shows today's lock-in prices for future procurement periods; the option-derived lines add forward-looking risk scenarios.</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        make_historical_price_chart(base_summary, summary, spot_price),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown(f"""
    <div class='math-card'>
        <div class='math-title'>How spot fits into the decision</div>
        <div class='math-copy'>
            <b>Spot</b> answers: where is the cash market now?<br>
            <b>Forward vs. spot</b> answers: what premium or discount do we pay today to lock a future procurement period?<br>
            <b>Adverse scenario vs. forward</b> answers: how much higher could our cost be if we stay unhedged and the adverse scenario materializes?<br><br>
            Spot provides context, but the hedge signal is still based on the <b>adverse-scenario gap versus the forward</b>, normalized for what is typical at that same tenor. That keeps the decision rule focused on the risk we can actually lock today.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if abs(adverse_delta - 0.35) < 1e-9:
        decision = build_decision_frame(summary)
        signaled = decision[decision["hedge_signal"]].sort_values("expiry")

        st.markdown("<div class='section-kicker'>Decision Signal</div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Is the adverse gap unusually wide?</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-subtitle'>We compare each current 35-delta gap with the normal gap for the same horizon, so long-dated options are not automatically treated as more alarming simply because they have more time value.</div>",
            unsafe_allow_html=True,
        )

        if not signaled.empty:
            first_signal = signaled.iloc[0]
            st.markdown(f"""
            <div class='signal-card'>
                <div class='signal-label'>Hedge signal</div>
                <div class='signal-title'>{first_signal['expiry'].strftime('%b %Y')} is the first procurement period above the trigger</div>
                <div class='signal-copy'>Current adverse gap: <b>{first_signal['current_gap_pct']:.1%}</b>. Normal gap for that horizon: <b>{first_signal['normal_gap_pct']:.1%}</b>. The gap is <b>{first_signal['excess_gap_pp']:.1f} percentage points wider than normal</b>, which triggers the illustrative rule to consider adding forward/futures hedge coverage for that expiry.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='signal-card no-signal'>
                <div class='signal-label'>No hedge signal</div>
                <div class='signal-title'>No procurement period is unusually wide enough to trigger the rule</div>
                <div class='signal-copy'>The current adverse gaps remain within the illustrative tolerance around their normal tenor-adjusted levels.</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='math-card'>
            <div class='math-title'>Decision-rule math</div>
            <div class='math-copy'>
                <b>1.</b> Current adverse gap = (35-delta scenario − forward) ÷ forward.<br>
                <b>2.</b> Normal gap = recent historical average 35-delta gap for the same tenor.<br>
                <b>3.</b> Excess gap = current adverse gap − normal gap.<br>
                <b>4.</b> If excess gap ≥ <b>{HEDGE_SIGNAL_THRESHOLD_PP:.2f} percentage points</b>, flag the expiry as a hedge candidate.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.plotly_chart(make_gap_vs_normal_chart(decision), use_container_width=True, config={"displayModeBar": False})
        render_signal_table(decision)
    else:
        st.info("The normalized hedge-signal benchmark in this POC is calibrated only to the default 35-delta adverse scenario.")

    st.markdown("<div class='section-kicker'>Detail</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Procurement decision table</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>Spot is repeated as a common market anchor so each future procurement period can be read relative to where aluminum was trading in the cash market on the snapshot date.</div>",
        unsafe_allow_html=True,
    )
    render_decision_table(summary, spot_price)

    st.markdown(
        "<div class='small-note'>Historical spot reference: Barchart COMEX Aluminum Cash (ALY00), Sep. 4, 2026. Futures source: Barchart public CME/COMEX aluminum market pages. Options and normal-gap benchmark: synthetic POC data. Production would replace the synthetic layers with licensed/live and historical options data.</div>",
        unsafe_allow_html=True,
    )


def render_live_lme(refresh: bool) -> None:
    if refresh or "live_curve" not in st.session_state:
        st.session_state.live_curve = fetch_lme_aluminum_monthly_curve()
        st.session_state.live_curve["expiry"] = pd.to_datetime(st.session_state.live_curve["expiry"])
        st.session_state.live_refreshed = datetime.now().astimezone()
    curve = st.session_state.live_curve
    nearest = curve.iloc[0]
    farthest = curve.iloc[-1]
    st.markdown(f"<span class='snapshot-pill'>LME public market data · delayed ≥15 minutes · refreshed {st.session_state.live_refreshed.strftime('%b %d, %Y · %I:%M %p %Z')}</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Nearest Lock-In Reference", f"${nearest['forward_price']:,.0f}/t")
    c2.metric("Farthest Displayed Contract", f"${farthest['forward_price']:,.0f}/t")
    c3.metric("Curve Change", f"{farthest['forward_price'] / nearest['forward_price'] - 1:+.1%}")
    st.dataframe(curve, use_container_width=True, hide_index=True)


def build_generic_snapshot(source_mode: str, target_delta: float, futures_upload, options_upload) -> Snapshot:
    if source_mode == "Demo data":
        seed = int(datetime.now(timezone.utc).timestamp() // 60)
        futures, options = generate_demo_market_data(seed=seed)
        return build_snapshot_from_frames(futures, options, target_delta, "Illustrative demo data")
    if futures_upload is None or options_upload is None:
        raise ValueError("Upload both the futures CSV and options CSV before refreshing.")
    return build_snapshot_from_frames(pd.read_csv(futures_upload), pd.read_csv(options_upload), target_delta, "Uploaded CSV snapshot")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="◼", layout="wide")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Dashboard Controls")
        source_mode = st.radio(
            "Data mode",
            ["Historical CME + illustrative options", "Live LME futures", "Demo data", "Upload CSVs"],
            index=0,
        )
        adverse_delta = st.slider(
            "Adverse cost scenario", 0.25, 0.45, DEFAULT_ADVERSE_DELTA, 0.05,
            help="Lower delta = less likely but more severe higher-cost scenario. The base outlook remains fixed at 50 delta.",
        )
        futures_upload = options_upload = None
        if source_mode == "Upload CSVs":
            futures_upload = st.file_uploader("Futures / forwards CSV", type="csv")
            options_upload = st.file_uploader("Call options CSV", type="csv")

    left, right = st.columns([4.2, 1.15])
    with left:
        st.markdown("<div class='hero-eyebrow'>Commodity Risk Dashboard</div>", unsafe_allow_html=True)
        st.markdown(f"# {APP_TITLE}")
        st.markdown(
            "<div class='hero-copy'>Spot market context, forward lock-in prices, option-implied cost scenarios, and a tenor-adjusted hedge signal in one view.</div>",
            unsafe_allow_html=True,
        )
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
            st.session_state.snapshot = build_generic_snapshot(source_mode, adverse_delta, futures_upload, options_upload)
        except Exception as exc:
            st.error(str(exc))
            st.stop()

    snap = st.session_state.snapshot
    st.dataframe(snap.summary, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
