"""
Gold Layer Transformations
--------------------------
This file contains ALL business logic to transform Silver data
into analytics-ready and ML-ready datasets (Gold layer).
"""

import pandas as pd


# ============================================================
# 1. FACT TABLE (Main dataset for analytics)
# ============================================================
def build_jobs_fact(df):
    df = df.copy()

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return df[[
        "job_id",
        "job_title",
        "company_name",
        "location",
        "posted_date",
        "salary_min",
        "salary_max",
        "salary_avg",
        "currency",
        "job_url"
    ]]


# ============================================================
# 2. AGGREGATIONS FOR DASHBOARD
# ============================================================
def jobs_per_location(df):
    return (
        df.groupby("location")
        .size()
        .reset_index(name="job_count")
    )


def jobs_per_company(df):
    return (
        df.groupby("company_name")
        .size()
        .reset_index(name="job_count")
    )
def salary_trends(df):
    df = df.copy()

    df = df.dropna(subset=["salary_min", "salary_max"])

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return (
        df.groupby("posted_date")["salary_avg"]
        .mean()
        .reset_index()
    )

# ============================================================
# 3. SKILLS ANALYSIS (simple NLP)
# ============================================================
def skills_demand(df):

    df = df.copy()
    df["job_description"] = df["job_description"].fillna("")

    skills = ["python", "sql", "aws", "spark", "docker"]

    results = []

    for skill in skills:
        count = df["job_description"].str.lower().str.contains(skill).sum()
        results.append({"skill": skill, "count": count})

    return pd.DataFrame(results)

# ============================================================
# 4. ML FEATURE TABLE (for recommendation system)
# ============================================================
def job_features(df):

    df = df.copy()

    df["job_description"] = df["job_description"].fillna("")
    df["location"] = df["location"].fillna("")

    df["python"] = df["job_description"].str.contains("python", case=False).astype(int)
    df["sql"] = df["job_description"].str.contains("sql", case=False).astype(int)
    df["aws"] = df["job_description"].str.contains("aws", case=False).astype(int)

    df["remote"] = df["location"].str.contains("remote", case=False).astype(int)

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return df[[
        "job_id",
        "python",
        "sql",
        "aws",
        "remote",
        "salary_avg"
    ]]