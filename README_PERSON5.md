# Person 5: Action Lab and Report Generator

This part of the project turns survey findings into ideas for improving the 988 training. It also makes a PDF report.

**Note:** The demo uses FAKE (synthetic) data. It is not real EveryMind results.

## How to run it

1. Install the libraries (one time only):

       python -m pip install streamlit reportlab pandas

2. Start the app:

       python -m streamlit run person5_demo.py

3. Your browser opens. Pick a finding, tick actions, and download the PDF.

## Using the real survey data

1. Start the app, then in the left sidebar pick **Real survey CSV**.
2. Upload the survey CSV. It is read in memory only and is not saved.
3. You will see real counts: call-intent coverage, very small groups, and survey design gaps.
4. Optional: also upload your teammates' findings (JSON) to combine everything.

The adapter only makes **descriptive** findings. Knowledge/call-intent gaps (Person 2) and comment themes (Person 3) must come from teammates.

To use it in code:

    from real_data_adapter import load_and_build
    findings, metrics, summary = load_and_build("survey.csv")

## How to test it

    python test_person5.py

You should see `22 tests, 0 failed` at the end. (The tests use a tiny fake spreadsheet, not the real CSV.)

## What each file does

| File | What it does |
|------|--------------|
| `person5_demo.py` | The Streamlit web page (the part you click on) |
| `intervention_planner.py` | The list of improvement ideas and the rules that match them to findings |
| `report_generator.py` | Builds the PDF report |
| `sample_findings.py` | Fake example findings for the demo |
| `real_data_adapter.py` | Reads the real survey CSV and makes real descriptive findings and numbers |
| `test_person5.py` | Automatic checks that everything works |

## For teammates: using my functions in your code

    from intervention_planner import recommend_interventions, build_action_plan
    from report_generator import generate_report

    pdf_bytes = generate_report(metrics, findings, ["myth_vs_reality"])

A finding is a dictionary with these keys: `id`, `source`, `type`, `title`, `description`,
`count`, `denominator`, `percentage`, `limitations`, `evidence`, `status`.

If a number is missing, use `None` (never 0).

Valid `type` values are listed in `FINDING_TYPE_MAP` inside `intervention_planner.py`.

## Rules

- Do NOT upload the real survey CSV or any participant comments to GitHub.
- Do not add claims about how 988 works unless EveryMind has verified them.