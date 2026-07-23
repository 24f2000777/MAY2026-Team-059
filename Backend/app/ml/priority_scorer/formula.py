import pandas as pd

# priority formula - since BMC data has no priority label, we build our own
# using severity + category risk + a few small boosts

severity_scores = {"Low": 20, "Medium": 45, "High": 70, "Critical": 90}

# rough risk tiers by category, higher = more urgent
high_risk = ["Health / Epidemic", "Drainage Overflow / Flooding", "Tree Fallen / Dangerous Tree"]
medium_high_risk = ["Water Supply Disruption", "Water Leakage / Pipe Burst", "Illegal Construction"]
medium_risk = ["Pothole / Road Damage", "Street Light Failure", "Public Toilet Condition", "Stray Animal Menace"]

monsoon_categories = ["Drainage Overflow / Flooding", "Water Supply Disruption", "Water Leakage / Pipe Burst", "Tree Fallen / Dangerous Tree"]


def calculate_priority(row):
    score = severity_scores[row["severity"]]

    category = row["complaint_category"]
    if category in high_risk:
        score += 10
    elif category in medium_high_risk:
        score += 6
    elif category in medium_risk:
        score += 3
    # else: lower risk category, no bonus

    # slum wards get a small boost - equity thing
    score += row["ward_slum_percentage"] * 0.08

    # monsoon only matters for weather related complaints
    if row["is_monsoon_season"] == 1 and category in monsoon_categories:
        score += 8

    # if this person keeps complaining and nothing's happened, bump priority a bit
    if row["repeat_complainant"] == 1:
        score += 3
    score += min(row["prior_complaints_count"], 5)

    if score > 100:
        score = 100
    if score < 0:
        score = 0

    return score


def calculate_priority_vectorized(df):
    # same formula as calculate_priority, just done column-wise with pandas
    # instead of row-by-row - way faster on large datasets (used by train.py)
    category = df["complaint_category"]

    score = df["severity"].map(severity_scores).astype(float)
    score += category.isin(high_risk) * 10
    score += category.isin(medium_high_risk) * 6
    score += category.isin(medium_risk) * 3
    score += df["ward_slum_percentage"] * 0.08

    is_monsoon_hit = (df["is_monsoon_season"] == 1) & category.isin(monsoon_categories)
    score += is_monsoon_hit * 8

    score += (df["repeat_complainant"] == 1) * 3
    score += df["prior_complaints_count"].clip(upper=5)

    return score.clip(lower=0, upper=100)


def check_distribution(scores):
    # bucket scores into 10-point bands and see how spread out they are
    bands = pd.cut(scores, bins=range(0, 101, 10))
    counts = bands.value_counts(normalize=True).sort_index()
    print("score distribution by band:")
    print(counts)

    biggest_band = counts.max()
    if biggest_band > 0.7:
        print(f"WARNING: {biggest_band:.0%} of scores fall in one band, formula might be too flat")
    else:
        print("distribution looks reasonably spread out")


def check_severity_consistency(df):
    # for each category, critical complaints should never score lower than low ones
    problems = 0
    for category, group in df.groupby("complaint_category"):
        critical_scores = group[group["severity"] == "Critical"]["priority_score"]
        low_scores = group[group["severity"] == "Low"]["priority_score"]
        if len(critical_scores) == 0 or len(low_scores) == 0:
            continue
        if critical_scores.min() <= low_scores.max():
            problems += 1
            print(f"WARNING: {category} - critical scores overlap with low scores")

    if problems == 0:
        print("severity consistency check passed, no contradictions")


def check_proxy_correlation(df):
    # these fields are NOT model inputs, just used here to sanity check the formula
    resolution_corr = df["priority_score"].corr(df["resolution_days"])
    print(f"correlation with resolution_days: {resolution_corr:.3f} (expect mild negative)")

    media_avg = df.groupby("media_attention")["priority_score"].mean()
    print(f"avg priority score by media_attention:\n{media_avg}")

    political_avg = df.groupby("politically_sensitive")["priority_score"].mean()
    print(f"avg priority score by politically_sensitive:\n{political_avg}")
