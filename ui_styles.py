"""Shared visual system for the EveryMind / Beyond Awareness Streamlit app.

Visual-only helpers: no survey processing, statistics, or export logic.
Plain text supplied by the app is HTML-escaped before being displayed.
"""
from __future__ import annotations

from html import escape

import streamlit as st


PALETTE = {
    "ink": "#203C2C",
    "muted": "#6C7D6E",
    "forest": "#173D2C",
    "bark": "#A78058",
    "pale": "#ECF3E9",
    "jade": "#287859",
    "peach": "#F7EEE0",
    "blue": "#F1F5EE",
    "mint": "#E6F1E8",
}


def inject_styles():
    """Consistent gentle light theme across all pages and native widgets."""
    st.markdown(
        """
<style>
/* ── Page foundation ─────────────────────────────── */
:root { --ba-ink:#203C2C; --ba-muted:#6C7D6E; --ba-forest:#173D2C; }
html, body, [data-testid="stAppViewContainer"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
[data-testid="stAppViewContainer"] {
    color: #203C2C;
    background:
      radial-gradient(ellipse at 83% 0%, rgba(197,218,191,.30), transparent 36%),
      linear-gradient(160deg,#F9FAF5 0%,#F5F7EF 52%,#FFFDF7 100%);
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
    max-width: 1200px;
    padding-top: 2.1rem;
    padding-bottom: 4rem;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { background: #9A7653; }
h1, h2, h3, h4 { letter-spacing: -.035em; color:#203C2C !important; }
h1 { font-weight: 780 !important; font-size: clamp(2rem, 3.4vw, 3rem) !important; }
h2 { font-size: 1.55rem !important; font-weight: 750 !important; }
h3 { font-size: 1.16rem !important; font-weight: 720 !important; }
p { line-height: 1.52; }
[data-testid="stCaptionContainer"] p { color:#677C6C; }

/* Streamlit heading permalink icons distract from the presentation. */
[data-testid="stHeadingWithActionElements"] a,
[data-testid="stHeaderActionElements"],
a[data-testid="stHeaderActionElements"] { display:none !important; }
/* ── Sidebar navigation ───────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(174deg,#18392B 0%,#142E24 56%,#111F19 100%);
    border-right: 1px solid #304E3B;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #F2F6EF !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-weight: 590;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
    border-radius: 13px;
    padding: 9px 11px;
    margin: 1px 0;
    border: 1px solid transparent;
    transition: background .15s ease, border .15s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(255,255,255,.12);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(145,190,158,.19);
    border-color: rgba(196,220,190,.23);
}
[data-testid="stSidebar"] [data-baseweb="select"] {
    color:#203C2C !important;
    background:#FFFFFF;
    border-radius: 11px;
}
[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #203C2C !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,.09);
    border-color: rgba(205,227,204,.18);
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color:#F2F6EF !important;
}

/* ── Calm cards and charts ─────────────────────────── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border:1px solid #E0E8DC;
    border-radius:18px;
    padding: 18px 19px;
    box-shadow: 0 9px 28px rgba(21,54,38,.045);
    min-height: 123px;
}
[data-testid="stMetricLabel"] p {color:#647C6A !important;font-weight:600;}
[data-testid="stMetricValue"] {color:#153D2B !important;}
[data-testid="stVerticalBlockBorderWrapper"] > div[style*="border"] {
    border-color:#E0E8DC !important;
    border-radius:18px !important;
}
[data-testid="stExpander"] {
    border:1px solid #E2EADf;
    border-radius:15px;
    background: #FFFFFF;
    box-shadow: 0 3px 14px rgba(21,54,38,.03);
    overflow:hidden;
}
[data-testid="stExpander"] summary {
    cursor:pointer !important;
    padding-top:4px;
    padding-bottom:4px;
}
[data-testid="stExpander"] summary p {font-weight:650;color:#254634;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;flex-wrap:wrap;}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background:#E6EFE3;
    border-radius:12px 12px 0 0;
    padding:9px 13px;
    font-weight:650;
    color:#677C69;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background:#FFFFFF !important;
    color:#173D2C !important;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border:1px solid #DDE8DB;
    border-radius:12px;
    overflow:hidden;
}
[data-testid="stAlert"] {border-radius:14px;}
[data-testid="stPlotlyChart"] {
    background:#FFFFFF;
    border:1px solid #DFEADF;
    border-radius:18px;
    padding:10px 10px 3px;
    box-shadow:0 6px 20px rgba(21,54,38,.035);
}

/* ── Buttons, input affordance, accessibility ─────── */
.stButton > button[kind="primary"],
.stDownloadButton > button {
    background:#173D2C;
    border:1px solid #173D2C;
    color:#FFFFFF;
    border-radius:12px;
    font-weight:650;
}
.stButton > button, .stDownloadButton > button {
    border-radius:12px;
    font-weight:640;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color:#A78058;
    color:#FFFFFF;
    background:#287859;
}
[data-baseweb="select"], [data-baseweb="select"] * {
    cursor:pointer !important;
}
/* Single-choice dropdowns are searchable, not freely editable:
   use pointer rather than I-beam and hide the input caret.
   Multi-selects keep their text-search caret for accessibility. */
[data-testid="stSelectbox"] [data-baseweb="select"] input {
    cursor:pointer !important;
    caret-color:transparent !important;
}
[data-baseweb="popover"] button,
button[aria-haspopup="listbox"] {cursor:pointer !important;}
button:focus-visible, [role="radio"]:focus-visible,
[role="combobox"]:focus-visible, [data-testid="stExpander"] summary:focus-visible {
    outline:3px solid #C6A87D !important;
    outline-offset:2px;
}

/* ── Custom insight pieces ─────────────────────────── */
.ba-kicker {
    color:#6C573F !important;
    text-transform:uppercase;
    letter-spacing:.145em;
    font-size:.73rem;
    font-weight:800;
    margin:0 0 .5rem;
}
.ba-page-subtitle {font-size:1.07rem;color:#647568;margin:.2rem 0 1.45rem;}
.ba-stat {
    min-height:160px;
    border-radius:20px;
    padding:20px 20px 18px;
    border:1px solid rgba(65,110,76,.10);
}
.ba-stat--lilac {background:#F0F3E7;}
.ba-stat--mint {background:#E9F3EA;}
.ba-stat--peach {background:#F6EADB;}
.ba-stat--blue {background:#F1F5EE;}
.ba-stat-icon {font-size:1.55rem;line-height:1;display:block;margin-bottom:13px;}
.ba-stat-label {color:#6C7C6E;font-size:.85rem;font-weight:650;}
.ba-stat-value {color:#173D2C;font-size:2.05rem;font-weight:800;letter-spacing:-.055em;line-height:1.1;margin:.3rem 0 .35rem;}
.ba-stat-detail {color:#6C7C6E;font-size:.79rem;line-height:1.4;}
.ba-focus {
    background:#FFFFFF;
    border:1px solid #DEE8DC;
    border-radius:20px;
    padding:22px 24px;
    box-shadow:0 8px 28px rgba(21,54,38,.04);
    margin:.4rem 0;
}
.ba-focus-label {color:#7D6548;font-size:.74rem;font-weight:780;text-transform:uppercase;letter-spacing:.11em;}
.ba-focus-title {font-size:1.36rem;color:#1B422F;font-weight:770;letter-spacing:-.03em;margin:.55rem 0;}
.ba-focus-text {font-size:.95rem;color:#697969;line-height:1.5;}
.ba-chip {
    display:inline-block;
    border-radius:999px;
    padding:7px 12px;
    background:#EDF2E7;
    color:#24553C;
    font-size:.77rem;
    font-weight:680;
    margin-bottom:12px;
}
.ba-source-line {color:#708174;font-size:.83rem;margin-bottom:1.3rem;}
.ba-section-lead {color:#65786A;font-size:.94rem;margin:-.25rem 0 1.2rem;}

@media (max-width:720px) {
    .ba-stat {min-height:135px;padding:16px;}
    .ba-stat-value {font-size:1.7rem;}
    [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
        padding-top:1.2rem;
    }
}
@media (prefers-reduced-motion:reduce) {
    *, *::before, *::after {transition:none !important;}
}
</style>
        """,
        unsafe_allow_html=True,
    )


def intro(kicker: str, title: str, subtitle: str) -> None:
    """Accessible page introduction with consistent hierarchy."""
    st.markdown(
        f'<div class="ba-kicker">{escape(kicker)}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(
        f'<p class="ba-page-subtitle">{escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def stat_cards(cards: list[dict]) -> None:
    """Render 1–4 plain-English summary cards; values are display strings."""
    colors = {"lilac", "mint", "peach", "blue"}
    if not cards:
        return
    columns = st.columns(len(cards), gap="medium")
    for column, card in zip(columns, cards):
        tone = card.get("tone", "lilac")
        if tone not in colors:
            tone = "lilac"
        with column:
            st.markdown(
                '<div class="ba-stat ba-stat--%s">' % tone
                + '<span class="ba-stat-icon" aria-hidden="true">%s</span>' % escape(str(card.get("icon", "✦")))
                + '<div class="ba-stat-label">%s</div>' % escape(str(card.get("label", "")))
                + '<div class="ba-stat-value">%s</div>' % escape(str(card.get("value", "")))
                + '<div class="ba-stat-detail">%s</div></div>' % escape(str(card.get("detail", ""))),
                unsafe_allow_html=True,
            )


def focus_card(kicker: str, title: str, text: str) -> None:
    """Small non-interactive editorial insight card."""
    st.markdown(
        '<div class="ba-focus">'
        f'<div class="ba-focus-label">{escape(kicker)}</div>'
        f'<div class="ba-focus-title">{escape(title)}</div>'
        f'<div class="ba-focus-text">{escape(text)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
