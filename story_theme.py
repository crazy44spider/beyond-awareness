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
GOLD = "#A17C59"
BARK = "#A17C59"
SAND = "#D8BE99"
INK = "#22392E"
MUTED = "#617568"
GRID = "#E5EBE3"

STYLE = r"""
<style>
:root {
  --forest:#143E30; --jade:#237557; --sage:#93BFA4;
  --ivory:#F7F8F2; --cream:#FFFDF7; --gold:#A17C59; --bark:#A17C59;
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
    max-width:1200px; padding-top:1.15rem; padding-bottom:3.5rem;
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
.ba-kpi-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:9px 0 25px;}
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

/* ── Compact Spotify-inspired navigation, with no emoji/icon dependencies ── */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    width:198px !important;
    min-width:198px !important;
    max-width:198px !important;
    background:#121D18 !important;
    border-right:1px solid #2C3B31 !important;
}
[data-testid="stSidebarUserContent"] {
    padding:11px 11px 14px !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap:.1rem !important;
}
.ba-nav-brand {
    display:flex;align-items:center;gap:11px;
    padding:6px 4px 14px;
}
.ba-nav-monogram {
    display:flex;align-items:center;justify-content:center;
    width:33px;height:33px;flex-shrink:0;
    border-radius:10px;
    color:#DFF6E1;
    background:#24533B;
    border:1px solid #3C7051;
    font-family:Arial,sans-serif;
    font-size:.79rem;font-weight:800;letter-spacing:-.07em;
}
.ba-nav-title {
    color:#F5F7F1;
    font-size:.69rem;font-weight:800;
    line-height:1.21;letter-spacing:.055em;
}
.ba-nav-section {
    color:#839B8C !important;
    font-size:.63rem;
    letter-spacing:.16em;
    font-weight:760;
    margin:0 0 6px 10px;
}
.ba-nav-secondary {
    margin-top:10px;
    padding-top:9px;
    border-top:1px solid #2A3C31;
}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
    width:100% !important;
    min-height:35px !important;
    padding:6px 11px !important;
    border-radius:8px !important;
    border:1px solid transparent !important;
    background:transparent !important;
    color:#B4C3B9 !important;
    text-align:left !important;
    justify-content:flex-start !important;
    font-size:.79rem !important;
    font-weight:550 !important;
    box-shadow:none !important;
    letter-spacing:0 !important;
}
[data-testid="stSidebar"] .stButton > button p {color:inherit !important;}
[data-testid="stSidebar"] .stButton > button:hover {
    color:#FFFDF5 !important;
    background:#26382C !important;
    border-color:#26382C !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    color:#FFFFFF !important;
    background:#2C4837 !important;
    border-left:3px solid #88D4A0 !important;
    border-top:1px solid #365641 !important;
    border-right:1px solid #365641 !important;
    border-bottom:1px solid #365641 !important;
    font-weight:700 !important;
    padding-left:10px !important;
}
[data-testid="stSidebar"] .stButton > button:focus-visible {
    outline:2px solid #A7DEA9 !important;
    outline-offset:2px !important;
}

.ba-nav-separator {
    height:1px;
    background:#34483B;
    margin:9px 9px 8px;
}


/* The rail is a full-height navigation surface, not a stack of tiny buttons.
   Streamlit's nested button markup must also be aligned (not only the button). */
[data-testid="stSidebarUserContent"] {
  min-height:calc(100dvh - 4rem) !important;
  padding:20px 13px 22px !important;
}
[data-testid="stSidebarUserContent"] > div,
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"],
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]:has(.ba-nav-brand) {
  min-height:calc(100dvh - 7rem) !important;
}
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]:has(.ba-nav-brand) {
  display:flex !important;
  flex-direction:column !important;
  justify-content:space-between !important;
  gap:clamp(12px, 2vh, 26px) !important;
}
.ba-nav-brand {
  padding:4px 4px 0 !important;
  margin-bottom:clamp(20px, 3vh, 34px) !important;
  min-height:51px !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] {
  width:100% !important;
  margin:0 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
  display:flex !important;
  flex-direction:row !important;
  align-items:center !important;
  justify-content:flex-start !important;
  text-align:left !important;
  width:100% !important;
  min-height:clamp(44px, 6vh, 61px) !important;
  padding:12px 15px !important;
  line-height:1.25 !important;
  font-size:.87rem !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button > div,
[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stButton"] button p,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] > div,
[data-testid="stSidebar"] button[data-testid^="stBaseButton"] p {
  width:100% !important;
  text-align:left !important;
  justify-content:flex-start !important;
  margin:0 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
  border-left:3px solid #88D4A0 !important;
  padding-left:12px !important;
}
.ba-nav-separator {
  height:1px !important;
  flex:0 0 1px !important;
  margin:clamp(8px,1.5vh,18px) 8px !important;
}
@media(max-height:710px) {
  [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]:has(.ba-nav-brand) {
    min-height:0 !important;
    gap:9px !important;
  }
  [data-testid="stSidebar"] [data-testid="stButton"] button {
    min-height:42px !important;
    padding:9px 12px !important;
  }
}

/* ── Always-visible, compact data controls above page content ── */
.ba-data-toolbar-label {
    color:#6D8073;
    font-size:.62rem;
    font-weight:800;
    letter-spacing:.13em;
    line-height:1.4;
}
.ba-data-toolbar-status {
    margin-top:1px;
    color:#244634;
    font-size:.96rem;
    line-height:1.3;
    font-weight:760;
    white-space:normal;
}
.ba-data-toolbar-status span {
    font-weight:480;
    color:#718175;
    font-size:.82rem;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.ba-data-toolbar-label) {
    border-radius:12px !important;
    border:1px solid #E0E9DE !important;
    background:#FFFFFF !important;
    box-shadow:none !important;
}
[data-testid="stPopover"] button {
    width:100%;
    min-height:37px !important;
    padding:8px 11px !important;
    background:#F5F8F3 !important;
    color:#214934 !important;
    border:1px solid #D7E4D9 !important;
    border-radius:9px !important;
    font-size:.84rem;
    font-weight:650;
}
[data-testid="stPopover"] button:hover {
    background:#E8F2E8 !important;
    border-color:#A1C9AD !important;
}
[data-testid="stPopover"] button:focus-visible {
    outline:2px solid #75A98B !important;
    outline-offset:2px;
}
@media(max-width:860px) {
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] {
        width:192px !important;
        min-width:192px !important;
        max-width:192px !important;
    }
    [data-testid="stSidebarUserContent"] { padding:12px 10px !important; }
    .ba-data-toolbar-status {font-size:.86rem;}
}


/* Single source of truth for accessible forest/bark focus and selection. */
::selection,
[data-testid="stAppViewContainer"] ::selection {
  background:#C5DCC4 !important; color:#153C2C !important;
}
::-moz-selection {background:#C5DCC4 !important;color:#153C2C !important;}
input,textarea,select {accent-color:#287859 !important;caret-color:#287859 !important;}
input[type="radio"],input[type="checkbox"],input[type="range"] {
  accent-color:#287859 !important;
}
[data-baseweb="radio"] [aria-checked="true"],
[data-baseweb="checkbox"] [aria-checked="true"] {
  color:#287859 !important;
}
[data-baseweb="tab-highlight"] {background:#287859 !important;}
[data-testid="stTabs"] [aria-selected="true"] {
  color:#173D2C !important; background:#E9F2E7 !important;
  border-bottom:2px solid #287859 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap:4px !important;flex-wrap:wrap !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  padding:8px 12px !important;white-space:nowrap;
}
[data-testid="stSegmentedControl"] [aria-checked="true"],
[data-testid="stPills"] [aria-checked="true"] {
  background:#287859 !important;color:#FFFDF7 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color:#287859 !important;
  box-shadow:0 0 0 1px #287859 !important;
}
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDownloadButton"] button:hover,
[data-testid="stButton"] button:hover {
  border-color:#A17C59 !important;
}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
  color:#FFFFFF !important;
  background:#173D2C !important;
  border:1px solid #173D2C !important;
}
.stButton > button[kind="primary"] p,
.stDownloadButton > button[kind="primary"] p {color:#FFFFFF !important;}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
  color:#FFFFFF !important;background:#287859 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
  gap:.78rem !important;
}
[data-testid="stSidebar"] .stButton > button {
    text-align:left !important;justify-content:flex-start !important;
    font-weight:560 !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] {
  text-align:left !important;
  width:100% !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
    color:#F7FAF4 !important;
}
[data-testid="stSidebar"] .stButton > button:hover p {
    color:#F7FAF4 !important;
}

/* The metric's meaning is part of the headline, not a footnote. */
.ba-gap-result {
  display:flex; flex-wrap:wrap;
  align-items:center; gap:14px 28px;
  padding:24px 26px;
  background:#FFFFFF;
  border:1px solid #DDE7DC;
  border-left:5px solid #287859;
  border-radius:14px;
  margin:14px 0 12px;
}
.ba-gap-number {
  font:600 clamp(3.8rem,6.4vw,5.3rem)/1 Georgia,"Times New Roman",serif;
  color:#153D2B;
  letter-spacing:-.065em;
  font-variant-numeric:tabular-nums;
  flex:0 0 auto;
}
.ba-gap-definition {
  color:#254B36;
  font-weight:730;
  line-height:1.3;
  font-size:clamp(1rem,1.65vw,1.28rem);
  flex:1 1 270px;
  max-width:630px;
}
.ba-definition-note {
  border-radius:10px;
  background:#EBF3E9;
  color:#365846;
  font-size:.89rem;
  line-height:1.6;
  padding:14px 18px;
  margin:12px 0 18px;
}
.ba-definition-note b {color:#184532;}
@media(max-width:650px) {
 .ba-gap-result {padding:18px;gap:8px;}
 .ba-gap-number {font-size:3.65rem;}
}

/* Numbers-only reference screen: compact, legible evidence tables. */
.ba-data-explorer-head {
  border-bottom:1px solid #DBE6DA;
  padding-bottom:12px;
  margin-bottom:12px;
}
.ba-data-explorer-head h2 {
  font-size:1.12rem !important;font-weight:750;
  margin:0 0 4px !important;
}
.ba-data-explorer-head p {
  margin:0;color:#6D7E6E;font-size:.83rem;
}
[data-testid="stDataFrame"] {
  border:1px solid #DDE6DC !important;
  border-radius:12px !important;
  overflow:hidden;
}
@media(max-width:770px) {
  [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] {
    padding-top:.8rem !important;
  }
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
