"""
Gold Layer Transformations
------------------------------------------
- Fact table (analytics)
- Dimension tables
- Aggregations (BI dashboards)
- ML feature table
--------------------------
This module contains ALL business logic to transform Silver data
into analytics-ready and ML-ready datasets (Gold layer).

It is organized into four main sections:
1. Fact Table Generation (Main dataset for reporting)
2. General Business Aggregations (Location, Company, Contract)
3. Salary & Market Trends (Salaries, Seniority)
4. Skills Analysis & ML Features (NLP, Feature extraction)
"""

import pandas as pd
import numpy as np

# ============================================================
# 0. SAFE HELPERS
# ============================================================

def compute_salary_avg(df):
    df = df.copy()
    # Calculate average salary if min and max are present
    if "salary_min" in df.columns and "salary_max" in df.columns:
        df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2
    else:
        df["salary_avg"] = None
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

# def build_dim_location(df):
#     """
#     Dimension table: unique locations
#     """

#     df = ensure_columns(df, ["city", "country", "postcode", "location_type"])

#     df_loc = df[[
#         "city",
#         "country",
#         "postcode",
#         "location_type"
#     ]].drop_duplicates()

#     df_loc = df_loc.reset_index(drop=True)
#     df_loc["location_id"] = df_loc.index + 1

#     return df_loc[[
#         "location_id",
#         "city",
#         "country",
#         "postcode",
#         "location_type"
#     ]]

from scripts.processing.gold.location_normalizer_pro import normalize_location_pro

def build_dim_location(df):

    loc_df = df[["location"]].drop_duplicates().copy()

    norm = normalize_location_pro(loc_df, "location")

    loc_df = pd.concat([loc_df, norm], axis=1)

    loc_df = loc_df.drop_duplicates(subset=["location"])

    loc_df["location_id"] = range(1, len(loc_df) + 1)

    return loc_df[[
        "location_id",
        "location",
        "city",
        "country",
        "is_remote"
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


def jobs_per_contract_type(df):
    """
    Aggregates job postings based on the standardized contract type 
    (e.g., Full-Time, Contractor, Internship).
    """
    if "contract_type_std" not in df.columns:
        return pd.DataFrame()
        
    return (
        df.groupby("contract_type_std")
        .size()
        .reset_index(name="job_count")
        .sort_values(by="job_count", ascending=False)
    )


def remote_work_trends(df):
    """
    Determines if a job is remote based on location or description keywords,
    and aggregates the distribution of remote vs. on-site jobs.
    """
    df = df.copy()
    
    # Identify if the job is remote via location or description keywords
    df["is_remote"] = (
        df["location"].fillna("").str.contains("remote|télétravail|anywhere", case=False) |
        df["job_description"].fillna("").str.contains("remote|télétravail", case=False)
    )
    
    return (
        df.groupby("is_remote")
        .size()
        .reset_index(name="job_count")
    )


# ============================================================
# 3. SALARY & MARKET TRENDS
# ============================================================

def salary_trends(df):
    """
    Calculates the average salary trend over time based on the posting date.
    Helps visualize market rate fluctuations.
    """
    df = df.copy()

    # Drop rows without salary data
    df = df.dropna(subset=["salary_min", "salary_max"])

    df = compute_salary_avg(df)

    return (
        df.groupby("posted_date")["salary_avg"]
        .mean()
        .reset_index()
        .sort_values("posted_date")
    )


def seniority_analysis(df):
    """
    Infers the required seniority level from the job title and 
    calculates average salaries and job counts per seniority level.
    """
    df = df.copy()
    
    # Classification using keywords in the job title
    conditions = [
        df['job_title'].str.contains('junior|jr|entry|stagiaire|intern', case=False, na=False),
        df['job_title'].str.contains('senior|sr|lead|principal|expert', case=False, na=False),
        df['job_title'].str.contains('manager|director|head|chef|responsable', case=False, na=False)
    ]
    choices = ['Junior', 'Senior/Lead', 'Manager/Director']
    df['seniority'] = np.select(conditions, choices, default='Mid-Level')
    
    # Compute average salary per level (uses standardized MAD salary if available)
    salary_col = 'salary_avg_mad' if 'salary_avg_mad' in df.columns else 'salary_avg'
    
    if salary_col not in df.columns:
        df['salary_avg'] = (df.get('salary_min', 0) + df.get('salary_max', 0)) / 2
        salary_col = 'salary_avg'
        
    return (
        df.groupby('seniority')
        .agg(
            job_count=('job_id', 'count'),
            avg_salary=(salary_col, 'mean')
        )
        .reset_index()
    )


# ============================================================
# 4. SKILLS ANALYSIS (NLP) & ML FEATURES
# ============================================================

def skills_demand(df):
    """
    Legacy method: Simple keyword matching for a small predefined list of technical skills.
    Consider using `skills_demand_expanded` for more comprehensive analysis.
    """
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


def skills_demand_expanded(df):
    """
    Advanced NLP: Scans job descriptions for a categorized, expanded dictionary of 
    technical skills and tools using regular expressions to avoid false positives.
    """
    df = df.copy()
    df["job_description"] = df["job_description"].fillna("").str.lower()
    
    skills_dict = {
        "Data & ML": ["python", "r", "machine learning", "pandas", "scikit-learn"],
        "Database": ["sql", "mongodb", "postgresql", "mysql", "nosql"],
        "Cloud & DevOps": ["aws", "azure", "gcp", "docker", "kubernetes", "ci/cd"],
        "Big Data": ["spark", "hadoop", "kafka", "databricks", "airflow"],
        "BI & Viz": ["power bi", "tableau", "looker", "metabase"]
    }
    
    results = []
    for category, skills in skills_dict.items():
        for skill in skills:
            # Use regex boundaries \b to match exact words and avoid partial matches (e.g., 'r' in 'word')
            count = df["job_description"].str.contains(rf'\b{skill}\b', regex=True).sum()
            if count > 0:
                results.append({"category": category, "skill": skill, "count": count})
                
    return pd.DataFrame(results).sort_values(by="count", ascending=False)


def job_features(df):
    """
    Generates a structured ML feature table for a downstream recommendation system.
    Extracts binary flags for key skills and remote work status.
    """
    df = df.copy()

    df["job_description"] = df["job_description"].fillna("")
    df["location"] = df["location"].fillna("")

    # Extract binary features
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