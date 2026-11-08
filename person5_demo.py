"""
person5_demo.py  (Person 5)
===========================
Standalone Streamlit "Action Lab".

Run it with:
    streamlit run person5_demo.py

What it does:
    1. Pick a finding (synthetic demo findings by default, or upload your own JSON).
    2. See recommendation cards (max 3 first; "Explore more" shows the rest).
    3. Tick checkboxes to select actions.
    4. Compare up to 3 actions side by side.
    5. Use the Inclusive Action Lens (five accessibility dimensions).
    6. Preview the action plan and download the PDF.

It only uses: intervention_planner.py, report_generator.py, sample_findings.py.
It does NOT edit or need the shared app.py.
"""

import json

import pandas as pd
import streamlit as st

from intervention_planner import (CATALOG_ORDER, DIMENSION_NAMES, build_action_plan, evidence_text,
                                  get_dimension_info, get_intervention, recommend_interventions)
from report_generator import generate_report
from sample_findings import get_synthetic_findings, get_synthetic_metrics

DEMO_BANNER = "SYNTHETIC DEMONSTRATION - NOT EVERYMIND RESULTS"

st.set_page_config(page_title="Beyond Awareness - Action Lab", page_icon=":compass:", layout="wide")

# ---------------------------------------------------------------------------
# Page style (brand colors from the brief)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    h1, h2, h3 { color: #4B2E83; }
    .demo-banner { background:#4B2E83; color:white; padding:12px; border-radius:6px;
                   text-align:center; font-weight:700; margin-bottom:10px; }
    .lens-box { background:#EDE7F6; padding:10px 14px; border-radius:6px; border-left:5px solid #148A83; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state: we remember the chosen actions here (list of intervention ids)
# ---------------------------------------------------------------------------
if "selected_ids" not in st.session_state:
    st.session_state["selected_ids"] = []


def toggle_action(action_id):
    """Called when a checkbox changes. Adds or removes the action from the chosen list."""
    selected = list(st.session_state["selected_ids"])
    if st.session_state.get("chk_" + action_id):
        if action_id not in selected:
            selected.append(action_id)
    elif action_id in selected:
        selected.remove(action_id)
    st.session_state["selected_ids"] = selected


def clear_selection():
    """Called by the 'Clear selection' button."""
    st.session_state["selected_ids"] = []
    for key in list(st.session_state.keys()):
        if key.startswith("chk_"):
            st.session_state[key] = False


# ---------------------------------------------------------------------------
# Sidebar: choose where the findings come from
# ---------------------------------------------------------------------------
st.sidebar.header("Data source")
source_choice = st.sidebar.radio("Findings to use", ["Synthetic demo findings", "Upload findings JSON"])

findings = get_synthetic_findings()
metrics = get_synthetic_metrics()

if source_choice == "Upload findings JSON":
    st.sidebar.caption(
        "Upload a .json file: either a list of findings, or an object like "
        '{"findings": [...], "metrics": {...}}. Use the same fields as sample_findings.py.'
    )
    uploaded = st.sidebar.file_uploader("Findings JSON", type=["json"])
    if uploaded is not None:
        try:
            loaded = json.load(uploaded)
            if isinstance(loaded, list):
                findings, metrics = loaded, {}
            elif isinstance(loaded, dict):
                findings, metrics = loaded.get("findings", []), loaded.get("metrics", {})
            else:
                raise ValueError("JSON must be a list or an object.")
        except Exception as error:  # show a friendly message instead of crashing
            st.sidebar.error("Could not read that file: %s" % error)
            findings, metrics = [], {}
    else:
        st.sidebar.info("No file uploaded yet. Showing no findings.")
        findings, metrics = [], {}

# Is any of the data synthetic? (then we show the warning everywhere)
is_demo = (str(metrics.get("status", "")).lower() == "synthetic" if isinstance(metrics, dict) else False) or any(
    isinstance(f, dict) and str(f.get("status", "")).lower() == "synthetic" for f in findings)

# Run the matching rules once per page load.
recs = recommend_interventions(findings)
by_finding = recs["by_finding"]
finding_ids = list(by_finding.keys())

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Beyond Awareness - Action Lab")
st.caption("Turn survey findings into training improvements and a plan for checking whether they work.")
if is_demo:
    st.markdown('<div class="demo-banner">%s</div>' % DEMO_BANNER, unsafe_allow_html=True)

if not finding_ids:
    st.info("There are no findings to show yet. Choose the synthetic demo or upload a findings JSON file.")
    st.stop()


def render_card(intervention_id, finding_note=""):
    """Draw one recommendation card with a select checkbox."""
    item = get_intervention(intervention_id)
    with st.expander(item["title"], expanded=True):
        key = "chk_" + intervention_id
        if key not in st.session_state:                      # set the starting value once
            st.session_state[key] = intervention_id in st.session_state["selected_ids"]
        st.checkbox("Select this action", key=key, on_change=toggle_action, args=(intervention_id,))

        st.markdown("**Why suggested:** " + item["why"])
        if finding_note:
            st.warning(finding_note)
        st.markdown("**Implementation steps:**")
        for number, step in enumerate(item["steps"], start=1):
            st.markdown("%d. %s" % (number, step))
        col1, col2, col3 = st.columns(3)
        col1.markdown("**Suggested owner:** " + item["owner"])
        col2.markdown("**Effort (planning estimate):** " + item["effort"])
        col3.markdown("**Check-in timing:** " + item["checkin"])
        st.markdown("**Success metric:** " + item["metric"])
        st.markdown("**Unanswered questions:**")
        for q in item["unanswered"]:
            st.markdown("- " + q)
        st.info("**What would change our mind?** " + item["change_mind"])


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["1. Findings and actions", "2. Compare actions", "3. Inclusive Action Lens", "4. Action plan and PDF"])

# ===== TAB 1: pick a finding, see cards =====
with tab1:
    chosen_id = st.selectbox(
        "Choose a finding", finding_ids,
        format_func=lambda fid: "%s  (%s)" % (by_finding[fid]["finding"]["title"], by_finding[fid]["finding"]["source"]))
    entry = by_finding[chosen_id]
    finding = entry["finding"]

    # Evidence box
    st.subheader("Evidence")
    count, denom, pct = finding["count"], finding["denominator"], finding["percentage"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Responses (count / denominator)",
              "%s / %s" % (count, denom) if count is not None and denom is not None else "Not available")
    c2.metric("Percentage", "%.1f%%" % pct if pct is not None else "Not available")
    c3.metric("Evidence status", finding["status"].capitalize())
    st.write(finding["description"] or "No description.")
    st.caption("Limitations: " + ("; ".join(finding["limitations"]) if finding["limitations"] else "None listed"))

    st.subheader("Suggested actions")
    if entry["status"] == "needs_review":
        st.warning(entry["message"])
    else:
        initial = entry["intervention_ids"][:3]
        for position, action_id in enumerate(initial):
            note = ""
            for rec in recs["recommendations"]:
                if rec["id"] == action_id:
                    for t in rec["triggered_by"]:
                        if t["id"] == chosen_id:
                            note = t["note"]
            if position == 0:
                st.caption("First recommendation")
            render_card(action_id, note)

        if st.checkbox("Explore more actions", key="explore_more"):
            st.markdown("**More options from the catalog** (not matched by the rules; use judgment)")
            for action_id in CATALOG_ORDER:
                if action_id not in initial:
                    render_card(action_id)

    st.divider()
    st.write("**Selected so far:** " + (", ".join(get_intervention(i)["title"] for i in st.session_state["selected_ids"])
                                        if st.session_state["selected_ids"] else "nothing yet"))
    st.button("Clear selection", on_click=clear_selection)

# ===== TAB 2: side-by-side comparison =====
with tab2:
    st.subheader("Intervention Comparison Mode")
    st.caption("Compare up to three actions. Effort is a planning estimate, never a proven impact score.")
    options = [r["id"] for r in recs["recommendations"]]
    if not options:
        st.info("No recommendations are available to compare yet.")
    else:
        default = [i for i in st.session_state["selected_ids"] if i in options][:3] or options[:2]
        picked = st.multiselect("Actions to compare (max 3)", options, default=default,
                                format_func=lambda i: get_intervention(i)["title"])
        if len(picked) > 3:
            st.warning("Please choose at most 3. Showing the first 3.")
            picked = picked[:3]
        if not picked:
            st.info("Choose at least one action to compare.")
        else:
            table = {}
            for action_id in picked:
                it = get_intervention(action_id)
                table[it["title"]] = [
                    it["outcome"],
                    "\n".join("%d. %s" % (n, s) for n, s in enumerate(it["steps"], start=1)),
                    it["effort"] + " (planning estimate)",
                    it["trigger_text"],
                    it["metric"],
                    it["change_mind"],
                ]
            df = pd.DataFrame(table, index=["Intended outcome", "Concrete steps", "Estimated effort",
                                            "Evidence trigger", "What to measure",
                                            "What would change the recommendation"])
            st.table(df)

# ===== TAB 3: Inclusive Action Lens =====
with tab3:
    st.subheader("Inclusive Action Lens")
    st.caption("Diversity here means the BARRIERS we consider, not claims about who the participants are. "
               "The survey did not measure race, gender, income, immigration status, trauma, stigma, trust, "
               "or preferred contact method.")
    dimension = st.radio("Choose a dimension", DIMENSION_NAMES, horizontal=True)
    info = get_dimension_info(dimension)

    st.markdown("**1. What the current survey can establish**")
    st.write(info["established"])
    st.markdown("**2. What remains unknown**")
    st.write(info["unknown"])
    st.markdown("**3. Candidate training changes**")
    for choice in info["design_choices"]:
        st.markdown("- " + choice)
    st.markdown("Related actions: " + ", ".join(get_intervention(i)["title"] for i in info["intervention_ids"]))
    st.markdown("**4. Optional future survey questions**")
    for question in info["future_questions"]:
        st.markdown("- " + question)
    st.markdown('<div class="lens-box"><b>Responsible interpretation:</b> %s</div>' % info["interpretation"],
                unsafe_allow_html=True)

# ===== TAB 4: action plan + PDF =====
with tab4:
    st.subheader("Action-plan preview")
    selected = st.session_state["selected_ids"]
    plan = build_action_plan(findings, selected)

    if not plan:
        st.info("No actions selected yet. Go to tab 1 and tick at least one action to enable the PDF download.")
    else:
        for action in plan:
            st.markdown("#### " + action["title"])
            preview = pd.DataFrame({
                "Current evidence": [action["current_evidence"]],
                "Proposed change": [action["proposed_change"]],
                "Future measurement": [action["future_measurement"]],
                "Decision rule": [action["decision_rule"]],
            })
            st.table(preview)

    # Build the PDF only when something is selected.
    pdf_bytes = b""
    if plan:
        try:
            pdf_bytes = generate_report(metrics, findings, selected)
        except Exception as error:  # never crash the page
            st.error("Could not build the PDF: %s" % error)
    st.download_button(
        "Download Improvement Brief",
        data=pdf_bytes,
        file_name="beyond_awareness_improvement_brief.pdf",
        mime="application/pdf",
        disabled=not pdf_bytes,
        help=None if pdf_bytes else "Select at least one action first.",
    )
    if not pdf_bytes:
        st.caption("The download button is disabled until you select at least one action.")