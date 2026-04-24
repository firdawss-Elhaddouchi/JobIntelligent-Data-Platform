"""
Gold Layer Transformations
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
# 1. FACT TABLE (Main dataset for analytics)
# ============================================================

def build_jobs_fact(df):
    """
    Constructs the main fact table containing core job data.
    This serves as the central dataset for most business intelligence queries.
    """
    df = df.copy()

    # Calculate average salary if min and max are present
    if "salary_min" in df.columns and "salary_max" in df.columns:
        df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2
    else:
        df["salary_avg"] = None

    # Define the core columns to keep for the fact table
    columns_to_keep = [
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
    ]
    
    # Return only the columns that actually exist in the DataFrame
    return df[[col for col in columns_to_keep if col in df.columns]]


# ============================================================
# 2. GENERAL BUSINESS AGGREGATIONS (Dashboards)
# ============================================================

def jobs_per_location(df):
    """
    Aggregates the total number of job postings per geographic location.
    Useful for geographic distribution heatmaps.
    """
    return (
        df.groupby("location")
        .size()
        .reset_index(name="job_count")
    )


def jobs_per_company(df):
    """
    Aggregates the total number of job postings per company.
    Useful for identifying top hiring organizations.
    """
    return (
        df.groupby("company_name")
        .size()
        .reset_index(name="job_count")
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

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return (
        df.groupby("posted_date")["salary_avg"]
        .mean()
        .reset_index()
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
        results.append({"skill": skill, "count": count})

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

    # Recompute average salary for feature matrix
    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return df[[
        "job_id",
        "python",
        "sql",
        "aws",
        "remote",
        "salary_avg"
    ]]