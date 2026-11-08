import pandas as pd

from survey_designer import DATA_PATH, analyze_survey

# Read the original survey's COLUMN HEADERS only.
# No real participant responses are copied.
headers = pd.read_excel(DATA_PATH, nrows=0).columns

# Create six entirely fictional responses.
fake = pd.DataFrame(index=range(6), columns=headers)

# Everybody answers the willingness-to-call question.
fake.iloc[:, 17] = [8, 9, 7, 8, 10, 9]

# Fictional improvement comments.
fake.iloc[:, 19] = [
    "Please include more roleplay activities.",
    "More examples would be helpful.",
    "Could we have a longer training?",
    "The presentation was great.",
    "Please show more videos.",
    "More information about 988 would help."
]

# Save a real Excel file for testing uploads later.
fake.to_excel("person4/fake_upload.xlsx", index=False)

# Analyze it using YOUR function.
report = analyze_survey(fake)

print("===== FAKE SURVEY FINDINGS =====")

for finding in report["findings"]:
    print("-", finding["title"])

print("\n===== RECOMMENDED QUESTIONS =====")
print(report["recommendations"]["question_id"].tolist())