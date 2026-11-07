import pandas as pd


def create_sample_data():
    """Create synthetic survey data for testing only."""

    return pd.DataFrame({
        "before_identify": [2, 3, 4, 1],
        "after_identify": [4, 4, 4, 3],
        "before_describe": [2, 2, 3, None],
        "after_describe": [4, 3, 5, 4],
        "before_when": [1, 3, 2, 4],
        "after_when": [3, 4, 4, 4],
        "willingness_to_call": [8, 5, None, 7],
        "county": ["A", "B", "A", "C"],
        "participant_type": ["Staff", "Student", "Staff", "Student"],
        "language": ["English", "English", "Spanish", "English"],
        "role_list": [
            ["Staff", "Volunteer"],
            ["Student"],
            ["Staff", "Educator"],
            ["Student", "Volunteer"]
        ]
    })