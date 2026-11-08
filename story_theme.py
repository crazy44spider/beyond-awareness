"""Forest-green visual language for the story-first Beyond Awareness experience.

Presentation-only. No statistics, analysis, exports, or workbook access.
"""
from __future__ import annotations

from html import escape

import streamlit as st

FOREST = "#143E30"
JADE = "#237557"
SAGE = "#93BFA4"
MINT = "#E6F1E8"
IVORY = "#F7F8F2"
CREAM = "#FFFDF7"
GOLD = "#C89E61"
INK = "#22392E"
MUTED = "#617568"
GRID = "#E5EBE3"

STYLE = r"""
<style>
:root {
  --forest:#143E30; --jade:#237557; --sage:#93BFA4;
  --ivory:#F7F8F2; --cream:#FFFDF7; --gold:#C89E61;
  --ink:#22392E; --muted:#617568; --line:#E0E9DE;
}
html, body, [data-testid="stAppViewContainer"] {
    font-family: "Aptos", "Inter", "Segoe UI", sans-serif !important;
    color:var(--ink);
}
[data-testid="stAppViewContainer"] {
    background:var(--ivory) !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
    max-width:1100px; padding-top:2.0rem; padding-bottom:5rem;
}
[data-testid="stHeader"] {background:transparent !important;}
[data-testid="stMain"] {color:var(--ink);}
h1,h2,h3,h4 {color:var(--forest) !important; letter-spacing:-.025em;}
h1 {font-size:clamp(2rem,3.5vw,3rem) !important; font-weight:700 !important;}
h2 {font-size:1.48rem !important;font-weight:700 !important;}
h3 {font-size:1.12rem !important;font-weight:680 !important;}
[data-testid="stCaptionContainer"] p {color:var(--muted) !important; font-size:.86rem;}
[data-testid="stMarkdownContainer"] p {line-height:1.5;}
[data-testid="stHeadingWithActionElements"] a,
[data-testid="stHeaderActionElements"] {display:none !important;}

/* Navigation deliberately occupies a separate surface from the content. */
[data-testid="stSidebar"] {
   background:linear-gradient(170deg,#174633 0%,#11392C 78%,#102E24 100%) !important;
   border-right:1px solid #194B39;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  color:#F1F5EC !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding:9px 12px; border:1px solid transparent;border-radius:10px;
  margin:0 0 3px;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:rgba(255,255,255,.10);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:#2F674D;border-color:#5B9575;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {font-weight:560;}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  border:1px solid rgba(255,255,255,.24);background:rgba(255,255,255,.06);
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {color:#FAFBF7 !important;}
[data-testid="stSidebar"] [data-baseweb="select"] {background:white;border-radius:8px;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#163A2C !important;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.18);}

/* Native controls: avoid misleading I-beam pointer on simple choices. */
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stExpander"] summary,
[role="radiogroup"] label,
.stButton button, .stDownloadButton button {cursor:pointer !important;}
[data-testid="stSelectbox"] [data-baseweb="select"] input {
  cursor:pointer !important;caret-color:transparent !important;
}
button:focus-visible, [role="radio"]:focus-visible,
[role="combobox"]:focus-visible, [data-testid="stExpander"] summary:focus-visible {
  outline:3px solid #E0BD7D !important;outline-offset:2px;
}
[data-testid="stMetric"] {
   background:white;border:1px solid var(--line);border-radius:13px;
   padding:15px 17px;box-shadow:none;min-height:90px;
}
[data-testid="stMetricLabel"] p {font-size:.83rem;color:var(--muted) !important;}
[data-testid="stMetricValue"] {font-weight:680;color:var(--forest) !important;}
[data-testid="stPlotlyChart"] {
   background:white;border:1px solid var(--line);
   border-radius:15px;overflow:hidden;
}
[data-testid="stExpander"] {
    border:1px solid var(--line);border-radius:12px;background:white;
    box-shadow:none;
}
[data-testid="stExpander"] summary p {font-weight:590;color:var(--forest) !important;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;flex-wrap:wrap;}
[data-testid="stTabs"] [data-baseweb="tab"] {
    padding:8px 12px;border-radius:9px 9px 0 0;
    color:var(--muted);font-weight:580;background:transparent;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color:var(--forest) !important;background:#E5F0E7 !important;
}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"] {
    background:var(--forest);color:white;border:1px solid var(--forest);
}
.stButton>button,.stDownloadButton>button {
    border-radius:10px;font-weight:620;min-height:40px;
}
.stButton>button:hover,.stDownloadButton>button:hover {
    border-color:var(--jade);color:var(--jade);
}
.stButton>button[kind="primary"]:hover {
    background:var(--jade);color:white;
}
[data-testid="stDataFrame"],[data-testid="stTable"] {
    border:1px solid var(--line);border-radius:10px;overflow:hidden;
}
[data-testid="stAlert"] {border-radius:10px;}

/* Deliberately different surfaces for distinct page purposes. */
.ba-eyebrow {font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;
   color:var(--jade);font-weight:800;margin-bottom:9px;}
.ba-heading {font-family:Georgia,"Times New Roman",serif;font-size:clamp(2.0rem,3.6vw,3.5rem);
   font-weight:600;line-height:1.13;letter-spacing:-.046em;color:var(--forest);
   margin:0 0 12px;}
.ba-subhead {font-size:1rem;color:var(--muted);max-width:680px;line-height:1.55;
   margin:0 0 24px;}
.ba-hero {border-radius:23px;padding:27px 31px;overflow:hidden;position:relative;
   background:linear-gradient(117deg,#194A36 0%,#184130 72%,#2C654A 100%);
   margin:0 0 20px;}
.ba-hero:after {content:"";position:absolute;width:280px;height:280px;right:-126px;top:-125px;
   border:1px solid rgba(255,255,255,.23);border-radius:50%;
   box-shadow:0 0 0 30px rgba(255,255,255,.025),0 0 0 65px rgba(255,255,255,.02);}
.ba-hero .ba-eyebrow{color:#B9DABF;}
.ba-hero .ba-heading{color:#FFFFFF !important;font-size:clamp(2.0rem,3.9vw,3.35rem);}
.ba-hero .ba-subhead{color:#D7E8DA;margin-bottom:0;max-width:610px;}
.ba-hero>*{position:relative;z-index:1;}
.ba-kpi-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:9px 0 25px;}
.ba-kpi{border:1px solid var(--line);border-radius:14px;background:white;padding:17px 18px;min-width:0;}
.ba-kpi .label{font-size:.77rem;color:var(--muted);font-weight:680;letter-spacing:.02em;}
.ba-kpi .value{font-family:Georgia,serif;color:var(--forest);font-size:1.8rem;
    font-weight:600;margin:9px 0 5px;}
.ba-kpi .hint{font-size:.74rem;color:var(--muted);line-height:1.38;}
.ba-story{background:#E8F2E8;border-left:4px solid #277655;border-radius:0 12px 12px 0;
   padding:17px 22px;margin:12px 0 22px;}
.ba-story .label{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;
  font-weight:750;color:#38785A;margin-bottom:6px;}
.ba-story .headline{font-size:1.08rem;line-height:1.3;font-weight:720;color:var(--forest);}
.ba-story p{margin:5px 0 0;font-size:.9rem;color:#466456;}
.ba-guide {border:1px solid var(--line);background:#FFFFFF;border-radius:15px;padding:19px 20px;
   margin-bottom:12px;}
.ba-guide small {font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;
   color:#41765A;font-weight:800;}
.ba-guide h3{font-size:1.12rem !important;margin:8px 0 !important;}
.ba-guide p{font-size:.87rem;color:var(--muted);margin:5px 0;}
.ba-mini-note{font-size:.76rem;color:var(--muted);margin-top:7px;}
.ba-badge{display:inline-flex;align-items:center;border-radius:999px;background:#E8F1E8;
  color:#1F6144;font-weight:750;font-size:.73rem; padding:6px 11px;}
.ba-badge--gold{background:#F8EEDB;color:#81602E;}
.ba-badge--soft{background:#EDF0EA;color:#607365;}
.ba-flowstep{display:flex;gap:15px;align-items:flex-start;
   border-bottom:1px solid var(--line);padding:14px 0;}
.ba-flow-num{width:31px;height:31px;border-radius:50%;border:1px solid #9FBEAB;
    background:#E7F2E9;flex-shrink:0;text-align:center;line-height:30px;
    font-weight:750;color:#265A3C;}
.ba-flowstep h3{margin:2px 0 3px !important;}
.ba-flowstep p{margin:0;font-size:.86rem;color:var(--muted);}
.ba-paper {background:#FFFDF8;border:1px solid #DDDCCF;
  box-shadow:0 12px 37px rgba(42,55,42,.08);border-radius:7px;
  padding:33px;max-width:680px;margin:0 auto 22px;}
.ba-paper .line{border-top:1px solid #DBE2D7;margin:17px 0;}
.ba-paper .paper-label{font-size:.7rem;letter-spacing:.13em;color:#647968;
   text-transform:uppercase;font-weight:800;}
.ba-paper h2{font-family:Georgia,serif;line-height:1.2;font-size:1.95rem !important;}
.ba-paper p{font-size:.9rem;color:#56695D;}
.ba-coverage{display:flex;justify-content:space-between;gap:12px;align-items:center;
    border-bottom:1px solid var(--line);padding:13px 2px;}
.ba-coverage strong{font-size:.91rem;color:var(--forest);font-weight:600;}
.ba-quiet {color:var(--muted);font-size:.82rem;}
.ba-footnote{color:#6B7D70;font-size:.77rem;margin:12px 0;}
@media(max-width:760px) {
 .ba-kpi-strip{grid-template-columns:1fr;}
 .ba-hero{padding:23px 19px;}
 .ba-paper{padding:20px;}
 [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"]{padding-top:1.2rem;}
}
@media(prefers-reduced-motion:reduce) {
  *{scroll-behavior:auto !important;transition:none !important;}
}
</style>
"""


def apply_theme() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


def esc(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def heading(kicker: str, title: str, description: str = "", *, dark: bool = False) -> None:
    cls = "ba-hero" if dark else "ba-page-top"
    st.markdown(
        f'<div class="{cls}"><div class="ba-eyebrow">{esc(kicker)}</div>'
        f'<div class="ba-heading">{esc(title)}</div>'
        f'<p class="ba-subhead">{esc(description)}</p></div>',
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple[str, str, str]]) -> None:
    cards = []
    for label, value, hint in items[:3]:
        cards.append(
            f'<div class="ba-kpi"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div><div class="hint">{esc(hint)}</div></div>'
        )
    st.markdown('<div class="ba-kpi-strip">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def takeaway(title: str, description: str, *, label: str = "Key takeaway") -> None:
    st.markdown(
        f'<div class="ba-story"><div class="label">{esc(label)}</div>'
        f'<div class="headline">{esc(title)}</div><p>{esc(description)}</p></div>',
        unsafe_allow_html=True,
    )


def guide_card(index: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="ba-guide"><small>{esc(index)}</small>'
        f'<h3>{esc(title)}</h3><p>{esc(description)}</p></div>',
        unsafe_allow_html=True,
    )


def flow_step(number: int, title: str, detail: str) -> None:
    st.markdown(
        f'<div class="ba-flowstep"><div class="ba-flow-num">{number}</div><div>'
        f'<h3>{esc(title)}</h3><p>{esc(detail)}</p></div></div>',
        unsafe_allow_html=True,
    )


def pill(text: str, *, color: str = "green") -> str:
    variant = "ba-badge--gold" if color == "gold" else "ba-badge--soft" if color == "soft" else ""
    return f'<span class="ba-badge {variant}">{esc(text)}</span>'
