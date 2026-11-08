# Story-first forest-green redesign — review guide

This branch is based on \`redesign-friendly-light-ui-nov7\`. **It does not change \`main\`.** It uses the existing survey cleaning, Person 2 gap calculations, Person 3 keyword coding, Person 4 survey question bank, and Person 5 intervention/report engines.

## The new narrative

| Page | Question it answers | Primary visual or interaction |
|---|---|---|
| Overview | What did we learn, and where next? | Dark-green editorial hero and three navigation destinations |
| Training Outcomes | Which knowledge areas improved in self-report? | One horizontal before/current dumbbell chart (same-respondent pairing) |
| Gap Detector | Do we have enough evidence about willingness to use 988? | Answer-coverage progress bar + clearly defined complete-case pattern |
| Participant Voices | What did commenters value or request? | Donut of theme *mentions*, adjacent clickable theme buttons and private masked examples |
| Survey Designer | What should next surveys ask? | Five-dimension coverage strip + 3 recommended questions + custom CSV builder |
| Intervention Planner | Which changes might help? | Top-three action roadmap + selection and evaluation |
| Reports | What can EveryMind take away? | Document-style preview + real PDF and JSON downloads |
| Detailed Analysis | Where are all the exact statistics and original controls? | Knowledge distributions, training ratings, groups, missingness, quality, original overview, and full Action Lab |

## Safety and interpretation

- A theme can match more than one comment, and one comment can match several themes. Donut proportions are **theme mentions across the displayed categories**, **not percentages of people**.
- Original Person 3 coding is rule-based, not manually validated. The private-review checkbox is **off by default** and masks common emails/phones/links in addition to Person 3's named-person redaction. This masking is not reliable anonymization; don't publish any comments or screenshots of them without approval.
- The original ID-indexed Spanish translations are **not applied to arbitrary new uploads**. Coding of comments in Spanish is incomplete until aligned to verified source text.
- Before/current knowledge is a **retrospective** comparison, not a controlled pre/post evaluation or evidence of causal training impact.
- Blank willingness-to-call responses are not evidence of reluctance.
- The Action Lab currently recommends from validated numeric/design-derived findings; it does **not** claim unvalidated keyword matches prove participant barriers. Its original comprehensive interface remains in Detailed Analysis.
- Source workbook remains local/private; do not commit respondent-level survey data.

## Preview on a local Mac

\`\`\`bash
git status
git fetch origin
git switch --track origin/story-first-forest-ui-nov8
python -m pip install -r requirements.txt
python -m compileall -q app.py story_theme.py story_pages.py feedback_analyzer.py team_integration.py
python -m unittest -v test_story_pages.py test_feedback_integration.py test_team_integration.py
python test_person5.py
python -m streamlit run app.py
\`\`\`

If the branch already exists locally, use \`git switch story-first-forest-ui-nov8\`. Don't discard uncommitted changes to switch branches. Streamlit must be restarted to read the new \`.streamlit/config.toml\` theme.

With the approved local \`survey_data.xlsx\` in the project root, the app should show the real workbook by default (1,299 responses for the original file). Select **Synthetic test data** only deliberately in the sidebar. Other uploads need the same 20-column EveryMind schema, though columns may be renamed using Person 1's canonical names.

## Before approving

1. **Data source:** Check real workbook selection and row count, and switch back and forth to Synthetic test data without stale action/PDF state.
2. **Overview:** Confirm only one main insight and three clear navigation options; no repeated “3 of 3” card.
3. **Outcomes:** Chart labels are visible without scrolling; on mobile/narrow screens check that all three labels remain readable.
4. **Gap Detector:** Check answer/missing denominators and complete-case wording; compare with Detailed Analysis raw figures.
5. **Voices:** Choose both feedback categories, click individual theme buttons, confirm the donut and count update. Only open private examples on an approved private machine.
6. **Survey Designer:** Verify five dimensions, three top suggestions, browse all ten, and export selected CSV.
7. **Planner:** Select actions, see the numbered roadmap, navigate to Reports, and verify selected titles appear in the PDF.
8. **Reports:** Download a valid PDF and JSON; check real/synthetic labeling and no raw comments.
9. **Detailed Analysis:** Visit all original chart/report tabs, comparison options, and data-quality audit.
10. **Accessibility:** Test keyboard tab navigation, focus rings, narrow window layout, pointer on dropdowns, and color contrast.

All native HTML created by our presentation helpers escapes dynamic strings. App code is a draft and should be tested in its actual Streamlit/browser environment before merging.
