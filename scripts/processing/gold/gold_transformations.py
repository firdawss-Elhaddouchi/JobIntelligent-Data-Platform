"""
Gold Layer Transformations (Clean Version)
------------------------------------------
- Fact table (analytics)
- Dimension tables
- Aggregations (BI dashboards)
- ML feature table
"""

import pandas as pd


# ============================================================
# 0. SAFE HELPERS
# ============================================================

def compute_salary_avg(df):
    df = df.copy()
    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2
    return df


def ensure_columns(df, cols):
    """Guarantee missing columns exist (prevents crashes)"""
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df


# ============================================================
# 1. DIMENSION: LOCATION
# ============================================================

def build_dim_location(df):
    """
    Dimension table: unique locations
    """

    df = ensure_columns(df, ["city", "country", "postcode", "location_type"])

    df_loc = df[[
        "city",
        "country",
        "postcode",
        "location_type"
    ]].drop_duplicates()

    df_loc = df_loc.reset_index(drop=True)
    df_loc["location_id"] = df_loc.index + 1

    return df_loc[[
        "location_id",
        "city",
        "country",
        "postcode",
        "location_type"
    ]]


# ============================================================
# 2. FACT TABLE (MAIN ANALYTICS TABLE)
# ============================================================

def build_jobs_fact(df, dim_location):
    """
    Main fact table for analytics dashboards
    """

    df = df.copy()

    # Ensure required columns exist
    df = ensure_columns(df, [
        "job_id", "job_title", "company_name",
        "city", "country", "postcode", "location_type",
        "salary_min", "salary_max", "currency", "posted_date"
    ])

    # Salary avg
    df = compute_salary_avg(df)

    # Join with dimension
    df_fact = df.merge(
        dim_location,
        on=["city", "country", "postcode", "location_type"],
        how="left"
    )

    return df_fact[[
        "job_id",
        "job_title",
        "company_name",
        "location_id",
        "salary_min",
        "salary_max",
        "salary_avg",
        "currency",
        "posted_date"
    ]]


# ============================================================
# 3. DASHBOARD AGGREGATIONS
# ============================================================

def jobs_per_location(df):
    df = ensure_columns(df, ["city"])

    return (
        df.groupby("city")
        .size()
        .reset_index(name="job_count")
        .sort_values("job_count", ascending=False)
    )


def jobs_per_company(df):
    df = ensure_columns(df, ["company_name"])

    return (
        df.groupby("company_name")
        .size()
        .reset_index(name="job_count")
        .sort_values("job_count", ascending=False)
    )


def salary_trends(df):
    df = ensure_columns(df, ["salary_min", "salary_max", "posted_date"])

    df = df.dropna(subset=["salary_min", "salary_max"])

    df = compute_salary_avg(df)

    return (
        df.groupby("posted_date")["salary_avg"]
        .mean()
        .reset_index()
        .sort_values("posted_date")
    )


# ============================================================
# 4. SKILLS ANALYSIS
# ============================================================

def skills_demand(df):

    df = ensure_columns(df, ["job_description"])

    df = df.copy()
    df["job_description"] = df["job_description"].fillna("")

    skills = ["python", "sql", "aws", "spark", "docker"]

    results = []

    for skill in skills:
        count = df["job_description"].str.lower().str.contains(skill).sum()
        results.append({
            "skill": skill,
            "count": int(count)
        })

    return pd.DataFrame(results)


# ============================================================
# 5. ML FEATURE TABLE
# ============================================================

def job_features(df):

    df = ensure_columns(df, ["job_id", "job_description", "location", "salary_min", "salary_max"])

    df = df.copy()

    df["job_description"] = df["job_description"].fillna("")
    df["location"] = df["location"].fillna("")

    df["python"] = df["job_description"].str.contains("python", case=False).astype(int)
    df["sql"] = df["job_description"].str.contains("sql", case=False).astype(int)
    df["aws"] = df["job_description"].str.contains("aws", case=False).astype(int)

    df["remote"] = df["location"].str.contains("remote", case=False).astype(int)

    df = compute_salary_avg(df)

    return df[[
        "job_id",
        "python",
        "sql",
        "aws",
        "remote",
        "salary_avg"
    ]]