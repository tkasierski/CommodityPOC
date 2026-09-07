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

APP_TITLE = "Aluminum Market Outlook"
DEFAULT_TARGET_DELTA = 0.50


PAGE_CSS = """
<style>
    .stApp {
        background: #f6f8fb;
        color: #1f2937;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 2.0rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #172033;
        letter-spacing: -0.02em;
    }

    div[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e8edf3;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5eaf0;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }

    div[data-testid="stMetricLabel"] {
        color: #667085;
        font-size: 0.84rem;
    }

    div[data-testid="stMetricValue"] {
        color: #152238;
    }

    .hero-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
        border: 1px solid #dfe7f0;
        border-radius: 18px;
        padding: 1.45rem 1.6rem 1.35rem 1.6rem;
        margin: 0.4rem 0 1.1rem 0;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
    }

    .hero-eyebrow {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    .hero-title {
        color: #172033;
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 0.45rem;
    }

    .hero-copy {
        color: #526072;
        font-size: 0.98rem;
        line-height: 1.55;
        max-width: 900px;
    }

    .insight-card {
        background: #fffaf0;
        border: 1px solid #f0dfb8;
        border-left: 5px solid #c58a21;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin: 0.25rem 0 1rem 0;
    }

    .insight-label {
        color: #8a5f13;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    .insight-text {
        color: #3e4653;
        font-size: 0.96rem;
        line-height: 1.5;
    }

    .section-kicker {
        color: #7a8699;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        margin-top: 0.45rem;
        margin-bottom: 0.15rem;
    }

    .section-title {
        color: #172033;
        font-size: 1.23rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .section-subtitle {
        color: #667085;
        font-size: 0.9rem;
        margin-bottom: 0.55rem;
    }

    .snapshot-pill {
        display: inline-block;
        background: #eef3f8;
        color: #536174;
        border-radius: 999px;
        padding: 0.34rem 0.68rem;
        font-size: 0.78rem;
        margin-bottom: 0.4rem;
    }

    .small-note {
        color: #7a8699;
        font-size: 0.79rem;
        line-height: 1.45;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 650;
        min-height: 2.6rem;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #e4e9ef;
        border-radius: 12px;
        overflow: hidden;
    }

    hr {
        border-color: #e9edf2;
    }
</style>
"""


CHART_COLORS = {
    "lock": "#5E6C84",
    "outlook": "#C58A21",
    "fill": "rgba(197, 138, 33, 0.10)",
    "bar": "#7C91B2",
    "grid": "#E8EDF3",
    "text": "#475467",
}


def make_price_chart(summary: pd.DataFrame, target_delta: float) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=summary["expiry"],
            y=summary["current_lock_in_price"],
            mode="lines+markers",
            name="Current Lock-In Price",
            line=dict(color=CHART_COLORS["lock"], width=3),
            marker=dict(size=7),
            hovertemplate="%{x|%b %Y}<br>Lock-In: $%{y:,.0f}/t<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=summary["expiry"],
            y=summary["market_implied_price_scenario"],
            mode="lines+markers",
            name="Market-Implied Price Outlook",
            line=dict(color=CHART_COLORS["outlook"], width=3),
            marker=dict(size=8),
            fill="tonexty",
            fillcolor=CHART_COLORS["fill"],
            hovertemplate="%{x|%b %Y}<br>Outlook: $%{y:,.0f}/t<extra></extra>",
        )
    )

    fig.update_layout(
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color=CHART_COLORS["text"]),
        ),
        font=dict(family="Arial, sans-serif", color=CHART_COLORS["text"]),
    )
    fig.update_xaxes(
        title=None,
        showgrid=False,
        tickformat="%b\n%Y",
        zeroline=False,
    )
    fig.update_yaxes(
        title="USD per tonne",
        tickprefix="$",
        separatethousands=True,
        gridcolor=CHART_COLORS["grid"],
        zeroline=False,
    )
    return fig


def make_protection_chart(summary: pd.DataFrame) -> go.Figure:
    pct = summary["potential_hedge_protection_pct"] * 100
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary["expiry"],
            y=pct,
            name="Potential Hedge Protection",
            marker_color=CHART_COLORS["bar"],
            text=pct.map(lambda x: f"{x:.1f}%"),
            textposition="outside",
            hovertemplate="%{x|%b %Y}<br>Potential protection: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=315,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        font=dict(family="Arial, sans-serif", color=CHART_COLORS["text"]),
    )
    fig.update_xaxes(title=None, showgrid=False, tickformat="%b\n%Y", zeroline=False)
    fig.update_yaxes(
        title="Protection vs. lock-in",
        ticksuffix="%",
        gridcolor=CHART_COLORS["grid"],
        zeroline=False,
    )
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
    out["Market-Implied Price Outlook"] = out["market_implied_price_scenario"]
    out["Potential Hedge Protection"] = out["potential_hedge_protection"]
    out["Potential Hedge Protection %"] = out["potential_hedge_protection_pct"]
    return out[
        [
            "Procurement Period",
            "Current Lock-In Price",
            "Market-Implied Price Outlook",
            "Potential Hedge Protection",
            "Potential Hedge Protection %",
        ]
    ]


def build_exec_insight(summary: pd.DataFrame) -> str:
    strongest = summary.loc[summary["potential_hedge_protection_pct"].idxmax()]
    period = strongest["expiry"].strftime("%b %Y")
    protection_pct = strongest["potential_hedge_protection_pct"]
    protection_dollars = strongest["potential_hedge_protection"]

    return (
        f"The largest current hedge-protection opportunity appears in <b>{period}</b>, "
        f"where the market-implied outlook is <b>{protection_pct:.1%}</b> "
        f"(<b>${protection_dollars:,.0f}/t</b>) above the price available to lock today."
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="◼", layout="wide")
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Dashboard Controls")
        st.caption("These settings are intended for the analyst maintaining the view, not for the executive audience.")

        source_mode = st.radio(
            "Market data source",
            ["Demo data", "Upload CSVs"],
            index=0,
        )

        target_delta = st.slider(
            "Market-implied outlook setting",
            min_value=0.10,
            max_value=0.90,
            value=DEFAULT_TARGET_DELTA,
            step=0.05,
            help="Uses the call strike with delta closest to this value for each expiry.",
        )

        futures_upload = None
        options_upload = None
        if source_mode == "Upload CSVs":
            st.divider()
            futures_upload = st.file_uploader("Futures / forwards CSV", type="csv")
            options_upload = st.file_uploader("Call options CSV", type="csv")

        st.divider()
        with st.expander("Technical methodology"):
            st.caption(
                "For each expiry, the app selects the call strike nearest the chosen delta. "
                "That strike is used as a simple market-implied price outlook for this proof of concept."
            )

    top_left, top_right = st.columns([4.2, 1.15])

    with top_left:
        st.markdown("<div class='hero-eyebrow'>Commodity Risk Dashboard</div>", unsafe_allow_html=True)
        st.markdown(f"# {APP_TITLE}")
        st.markdown(
            "<div class='hero-copy'>A simple view of what aluminum can be locked at today, "
            "compared with a probability-based market outlook derived from the options market.</div>",
            unsafe_allow_html=True,
        )

    with top_right:
        st.write("")
        st.write("")
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
    summary = snap.summary

    if st.session_state.get("snapshot_target_delta") != target_delta:
        st.info("The outlook setting has changed. Refresh market data to recalculate the dashboard.")

    st.markdown(
        f"<span class='snapshot-pill'>Last refreshed {snap.refreshed_at.strftime('%b %d, %Y · %I:%M %p %Z')} · {snap.source_label}</span>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-label">What stands out</div>
            <div class="insight-text">{build_exec_insight(summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nearest = summary.iloc[0]
    farthest = summary.iloc[-1]
    avg_protection = summary["potential_hedge_protection_pct"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Near-Term Lock-In Price",
        f"${nearest['current_lock_in_price']:,.0f}/t",
        help="Price available to lock for the nearest procurement period.",
    )
    c2.metric(
        "Near-Term Market Outlook",
        f"${nearest['market_implied_price_scenario']:,.0f}/t",
        help="Option-derived market-implied price outlook for the nearest period.",
    )
    c3.metric(
        "Average Potential Hedge Protection",
        f"{avg_protection:.1%}",
        help="Average gap between market-implied outlook and current lock-in price across displayed periods.",
    )

    st.write("")
    st.markdown("<div class='section-kicker'>Primary View</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Lock-in price vs. market-implied outlook</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>The shaded gap represents the amount of price protection a hedge could provide if the higher-cost market scenario materializes.</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(make_price_chart(summary, st.session_state.snapshot_target_delta), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-kicker'>Decision Support</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Potential hedge protection by procurement period</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>Higher percentages indicate a larger gap between today's lock-in price and the market-implied outlook.</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(make_protection_chart(summary), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-kicker'>Detail</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Procurement decision table</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-subtitle'>A compact view of the same information for specific procurement periods.</div>",
        unsafe_allow_html=True,
    )

    display = format_summary(summary)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Lock-In Price": st.column_config.NumberColumn(format="$%.0f /t"),
            "Market-Implied Price Outlook": st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection": st.column_config.NumberColumn(format="$%.0f /t"),
            "Potential Hedge Protection %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.markdown(
        "<div class='small-note'><b>How to read this:</b> a wider gap does not guarantee that aluminum prices will rise. "
        "It indicates that the options market is pricing a higher-cost scenario far enough above today's lock-in price to make hedging protection more economically meaningful. "
        "This proof of concept uses option delta as a simplified probability proxy.</div>",
        unsafe_allow_html=True,
    )

    st.divider()
    with st.expander("Methodology & data requirements"):
        st.markdown(
            """
**Current Lock-In Price**  
The futures or forward price for the relevant procurement period.

**Market-Implied Price Outlook**  
For each expiry, the app selects the call strike whose delta is closest to the chosen target delta (default: 0.50).

**Potential Hedge Protection**  
`Market-Implied Price Outlook - Current Lock-In Price`

**Potential Hedge Protection %**  
`Potential Hedge Protection / Current Lock-In Price`

This is intentionally simplified for management communication and proof-of-concept use. A production implementation could incorporate a full implied distribution, regional premiums and basis, live market-data feeds, historical snapshots, and formal hedge-policy thresholds.
            """
        )


if __name__ == "__main__":
    main()
