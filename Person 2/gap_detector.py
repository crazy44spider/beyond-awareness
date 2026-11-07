import pandas as pd
import numpy as np

# Before-and-current survey question pairs
KNOWLEDGE_PAIRS = {
    "identify_challenges": {
        "before": "before_identify",
        "after": "after_identify",
        "label": "Identifying challenges"
    },
    "describe_988": {
        "before": "before_describe",
        "after": "after_describe",
        "label": "Describing 988"
    },
    "when_to_use_988": {
        "before": "before_when",
        "after": "after_when",
        "label": "Knowing when to use 988"
    }
}

# Standard agreement-scale responses
AGREEMENT = {
    "strongly disagree": 1,
    "disagree": 2,
    "neither agree nor disagree": 3,
    "agree": 4,
    "strongly agree": 5
}

def _numeric(series):
    """
    Convert survey responses into numeric values.
    Handles both written answers and numbers.
    Missing or unrecognized answers remain missing.
    """
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    cleaned = series.astype("string").str.strip().str.lower()

    return pd.to_numeric(
        cleaned.map(AGREEMENT),
        errors="coerce"
    )

def knowledge_summary(df):
    """
    Compare recalled-before and current knowledge ratings
    for each of the three survey topics.

    Only participants with both ratings are included.
    """

    results = []

    for topic, columns in KNOWLEDGE_PAIRS.items():
        before_col = columns["before"]
        after_col = columns["after"]

        # Check that both columns exist
        if before_col not in df.columns or after_col not in df.columns:
            raise ValueError(
                f"Missing required columns: {before_col} or {after_col}"
            )

        # Convert responses into numbers
        before = _numeric(df[before_col])
        after = _numeric(df[after_col])

        # Keep only participants with both answers
        paired = pd.DataFrame({
            "before": before,
            "after": after
        }).dropna()

        # Calculate within-person differences
        differences = paired["after"] - paired["before"]

        n = len(paired)

        results.append({
            "topic": topic,
            "label": columns["label"],
            "paired_n": n,
            "recalled_before_mean": paired["before"].mean(),
            "current_mean": paired["after"].mean(),
            "mean_difference": differences.mean(),
            "median_difference": differences.median(),
            "increased": int((differences > 0).sum()),
            "unchanged": int((differences == 0).sum()),
            "decreased": int((differences < 0).sum()),
            "percent_increased": (differences.gt(0).mean() * 100) if n else np.nan,
            "percent_unchanged": (differences.eq(0).mean() * 100) if n else np.nan,
            "percent_decreased": (differences.lt(0).mean() * 100) if n else np.nan,
            "missing_pairs": len(df) - n
        })

    return pd.DataFrame(results)