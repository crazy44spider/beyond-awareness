# Beyond Awareness — Friendly UI redesign

This branch is **visual/UI work only** on top of the team's integration draft (`draft-integrate-team-modules-nov7`).

## Design principles
- Light lavender/cream instead of the dark default; mint and peach for gentle differentiation.
- Start with **responses, observed knowledge patterns, answer coverage, and actionable unknowns**.
- Show technical scores, paired counts, distributions, Spearman correlation, group comparisons and data-quality reports only on request.
- Never imply missing call-intent responses mean unwillingness, or that retrospective ratings prove training caused an improvement.
- Keep survey-design concerns separate from verified participant concerns.
- All pages retain original calculations, exports, navigation destinations and filters.

## Files changed
- `.streamlit/config.toml`: Streamlit light theme (restart the server to apply).
- `ui_styles.py`: shared styling and insight-card components. Selectboxes show a **pointer**, not an I-beam; single-choice caret hidden; multi-select search still works.
- `app.py`: friendlier navigation; optional filter drawer and JSON export; all routes preserved.
- `dashboard.py`: simplified Overview, with **all five original deep-dive tabs** inside `Explore detailed analysis`.
- `team_integration.py`: human-readable Gap Detector; Action Lab has recommendation, comparison, inclusive action lens and plan tabs.
- `person4/survey_designer.py`: question cards and progressive disclosure; all 10 questions and CSV export unchanged.

## Preview without touching main
From the repository root:

```bash
git fetch origin
git switch --track origin/redesign-friendly-light-ui-nov7
python -m pip install -r requirements.txt
python -m compileall -q app.py dashboard.py ui_styles.py team_integration.py person4/survey_designer.py
python -m unittest test_team_integration.py
python test_person5.py
python -m streamlit run app.py
```

If already on a local copy of this branch, use `git switch redesign-friendly-light-ui-nov7` instead of creating another tracking branch.

## Manual review checklist
1. Open Overview in Synthetic demo. Verify pastel cards, one readable knowledge chart, and a visible synthetic-data warning.
2. Expand `Explore detailed analysis`: confirm knowledge, training experience, representation, answer coverage, and group comparisons still work.
3. Expand `Refine responses` in the sidebar; try all county/role/language/date filters and the paired-n threshold.
4. Open Gap Detector; expand `Detailed evidence` for the original stats, willingness distribution, and correlation.
5. Open Survey Designer; confirm all five dimensions, proposed question preview, and CSV download.
6. Open Action Lab; compare interventions, inspect all five inclusive lenses, select actions, and see the action plan.
7. Open Reports; generate the PDF and download the aggregate JSON in its optional section.
8. Switch sources. Confirm prior action selections and generated PDFs are not reused.
9. Open the app in a narrow browser window; verify cards stack and labels remain readable.
10. Test on approved private/local survey files only. Do not publish raw respondent comments or tiny identifiable subgroups.

## Scope and limitations
- `feedback_analyzer.py` and Person 3's live-upload integration are **not modified**. Participant Voices may still say `Feature in progress` until a reusable import-safe analyzer is added.
- This branch was created for review; **do not merge it ahead of the integration branch**. The design PR should target the integration branch first. After the integration PR merges into `main`, retarget the design PR to `main`.
- Visual CSS depends on some Streamlit internal markup; check on the team's installed version and adjust selectors if Streamlit changes them.
- No automated browser visual regression was run here. Run the commands above before approving the PR.
