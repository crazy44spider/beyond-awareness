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

def willingness_summary(df):
    """
    Summarize participants' willingness to call 988.
    Missing answers are not counted as zero.
    """

    column = "willingness_to_call"

    if column not in df.columns:
        raise ValueError(f"Missing required column: {column}")

    scores = pd.to_numeric(df[column], errors="coerce")

    # Keep only valid scores between 0 and 10
    scores = scores.where(scores.between(0, 10))

    total = len(df)
    answered = int(scores.notna().sum())
    missing = total - answered

    return {
        "total_responses": total,
        "answered": answered,
        "missing": missing,
        "response_rate": (answered / total * 100) if total else np.nan,
        "mean_willingness": scores.mean(),
        "median_willingness": scores.median(),
        "score_distribution": scores.value_counts().reindex(
            range(11), fill_value=0
        ).sort_index().to_dict()
    }

def knowledge_vs_willingness(df, threshold=5):
    """
    Compare knowledge of when to use 988 with willingness to call.

    High knowledge: ratings of 4 or 5.
    Lower willingness: scores from 0 through threshold.
    """

    required = ["after_when", "willingness_to_call"]

    for column in required:
        if column not in df.columns:
            raise ValueError(f"Missing required column: {column}")

    # Convert both columns into numeric values
    knowledge = _numeric(df["after_when"])
    willingness = pd.to_numeric(
        df["willingness_to_call"], errors="coerce"
    )

    # Keep willingness scores between 0 and 10
    willingness = willingness.where(willingness.between(0, 10))

    # Keep only participants who answered both questions
    paired = pd.DataFrame({
        "knowledge": knowledge,
        "willingness": willingness
    }).dropna()

    n = len(paired)

    # Count participants in each knowledge/willingness combination
    heatmap = pd.crosstab(
        paired["knowledge"],
        paired["willingness"]
    ).reindex(
        index=range(1, 6),
        columns=range(11),
        fill_value=0
    )

    # Average willingness for each knowledge rating
    by_knowledge = paired.groupby("knowledge")["willingness"].agg(
        ["count", "mean", "median"]
    ).reindex(range(1, 6))

    # Identify high knowledge and lower willingness
    gap = paired[
        (paired["knowledge"] >= 4) &
        (paired["willingness"] <= threshold)
    ]

    # Calculate Spearman correlation if both variables vary
    correlation = np.nan

    if n >= 2 and paired["knowledge"].nunique() > 1 and paired["willingness"].nunique() > 1:
        correlation = paired["knowledge"].corr(
            paired["willingness"],
            method="spearman"
        )

    return {
        "complete_case_n": n,
        "excluded_n": len(df) - n,
        "heatmap": heatmap,
        "by_knowledge": by_knowledge,
        "gap_count": len(gap),
        "gap_percentage": (len(gap) / n * 100) if n else np.nan,
        "spearman_correlation": correlation
    }

def subgroup_summary(df, group_col):
    """
    Compare knowledge and willingness across different groups.

    Supports county, participant type, language, and multiple roles.
    """

    required = [
        "before_identify", "after_identify",
        "before_describe", "after_describe",
        "before_when", "after_when",
        "willingness_to_call", group_col
    ]

    for column in required:
        if column not in df.columns:
            raise ValueError(f"Missing required column: {column}")

    data = df.copy()

    # Handle participants who selected multiple roles
    if group_col == "role_list":
        def split_roles(value):
            if isinstance(value, list):
                return value
            if pd.isna(value):
                return []
            return [
                role.strip()
                for role in str(value).replace(";", ",").split(",")
                if role.strip()
            ]

        data[group_col] = data[group_col].apply(split_roles)
        data = data.explode(group_col)

    # Clean category labels
    data[group_col] = (
    data[group_col]
    .astype("string")
    .str.strip()
    .str.casefold()
    )

    data = data.dropna(subset=[group_col])
    data = data[data[group_col] != ""]

    results = []

    for group, group_data in data.groupby(group_col):

        # Count valid willingness responses
        willingness = pd.to_numeric(
            group_data["willingness_to_call"],
            errors="coerce"
        ).where(
            lambda x: x.between(0, 10)
        )

        # Calculate paired knowledge differences
        differences = []
        knowledge_respondents = pd.Series(
            False, index=group_data.index
        )

        for columns in KNOWLEDGE_PAIRS.values():
            before = _numeric(group_data[columns["before"]])
            after = _numeric(group_data[columns["after"]])

            valid = before.between(1, 5) & after.between(1, 5)

            knowledge_respondents = knowledge_respondents | valid

            if valid.any():
                differences.extend(
                (after[valid] - before[valid]).tolist()
                )
        n = len(group_data)
        answered = int(willingness.notna().sum())

        results.append({
            "group": group,
            "total_n": n,
            "knowledge_pairs_n": len(differences),
            "knowledge_respondents_n": int(knowledge_respondents.sum()),
            "average_knowledge_change": (
                np.mean(differences) if differences else np.nan
            ),
            "willingness_answered_n": answered,
            "willingness_response_rate": (
                answered / n * 100 if n else np.nan
            ),
            "median_willingness": willingness.median() if answered > 0 else np.nan,
            "sample_warning": (
                "Small sample: descriptive only" if n < 20 else ""
            )
        })

    return pd.DataFrame(results)

def detect_findings(df):
    """
    Identify descriptive patterns in knowledge and willingness data.

    Findings include supporting evidence and limitations.
    They do not establish causation.
    """

    findings = []

    # 1. Examine knowledge changes
    knowledge = knowledge_summary(df)

    for _, row in knowledge.iterrows():
        if row["paired_n"] == 0:
            continue

        if row["mean_difference"] > 0:
            findings.append({
                "type": "knowledge",
                "title": f"Knowledge increased: {row['label']}",
                "evidence": (
                    f"Mean difference: {row['mean_difference']:.2f}; "
                    f"{row['increased']} of {row['paired_n']} "
                    "participants reported an increase."
                ),
                "limitation": (
                    "Ratings are retrospective self-reports, not "
                    "prospective pre/post measurements. This does "
                    "not establish that training caused the change."
                )
            })

    # 2. Examine willingness response coverage
    willingness = willingness_summary(df)

    findings.append({
        "type": "coverage",
        "title": "Willingness-to-call response coverage",
        "evidence": (
            f"{willingness['answered']} of "
            f"{willingness['total_responses']} participants answered "
            f"({willingness['response_rate']:.1f}%)."
            if willingness["total_responses"] else
            "There are no survey responses to analyze."
        ),
        "limitation": (
            "Missing answers cannot be interpreted as unwillingness "
            "to call 988."
        )
    })

    # 3. Examine knowledge and willingness together
    comparison = knowledge_vs_willingness(df)

    if comparison["complete_case_n"] > 0:
        findings.append({
            "type": "knowledge_willingness",
            "title": "Knowledge and willingness comparison",
            "evidence": (
                f"{comparison['gap_count']} of "
                f"{comparison['complete_case_n']} complete cases "
                f"({comparison['gap_percentage']:.1f}%) had "
                "knowledge ratings of 4–5 and willingness scores of 0–5."
            ),
            "limitation": (
                "This is a descriptive pattern, not evidence of a "
                "cause or a confirmed cultural or trust barrier. "
                "Only participants answering both questions are included."
            )
        })

    # 4. Examine correlation when it can be calculated
    correlation = comparison["spearman_correlation"]

    if pd.notna(correlation):
        findings.append({
            "type": "correlation",
            "title": "Knowledge and willingness association",
            "evidence": (
                f"Spearman correlation: {correlation:.2f} "
                f"(n={comparison['complete_case_n']})."
            ),
            "limitation": (
                "Correlation describes association, not causation. "
                "It uses complete cases only and may not represent "
                "all participants."
            )
        })

    return findings