"""
Gold Layer Transformations (UPDATED STAR SCHEMA)
------------------------------------------------
Now supports full dimensional model:
- dim_location
- dim_date
- dim_company
- dim_contract_type

Fact + Aggregations + ML features
"""

import pandas as pd
import numpy as np
import re
import ast
from sqlalchemy import text
import os
from scripts.processing.silver.standardizer import normalize_location_pro


# ============================================================
# 0. SAFE HELPERS
# ============================================================

def compute_salary_avg(df):
    df = df.copy()
    if "salary_min" in df.columns and "salary_max" in df.columns:
        df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2
    else:
        df["salary_avg"] = None
    return df


def ensure_columns(df, cols):
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df

def clean_datetime(col):
    # col = pd.to_datetime(col, errors="coerce", utc=True)
    # return col.dt.tz_convert(None)

    # Convert to datetime, coerce errors to NaT, and strip timezone for Postgres compatibility
    return pd.to_datetime(col, errors="coerce", utc=True).dt.tz_convert(None)


POSTGRES_URI = os.getenv("DATABASE_URL", "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow")

def map_dtype(dt):
    if pd.api.types.is_integer_dtype(dt): return "INT"
    if pd.api.types.is_float_dtype(dt): return "FLOAT"
    if pd.api.types.is_bool_dtype(dt): return "BOOLEAN"
    return "TEXT"

def safe_replace(df, table_name, engine, schema="gold"):
    if df.empty:
        print(f"[SKIP] {table_name} empty")
        return

    df = df.where(pd.notnull(df), None)
    
    cols_def = ", ".join([f"{c} {map_dtype(df[c].dtype)}" for c in df.columns])
    
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS {schema}.{table_name} ({cols_def})"))
        conn.execute(text(f"TRUNCATE TABLE {schema}.{table_name} CASCADE;"))
        data = df.to_dict(orient="records")
        if data:
            for row in data:
                for k, v in row.items():
                    if pd.isna(v): row[k] = None
            cols_str = ", ".join(df.columns)
            vals_str = ", ".join([f":{c}" for c in df.columns])
            query = f"INSERT INTO {schema}.{table_name} ({cols_str}) VALUES ({vals_str})"
            conn.execute(text(query), data)
            
    print(f"[REPLACE] {table_name} refreshed ({len(df)} rows)")


def safe_append(df, table_name, engine, schema="gold", unique_cols=None):
    if df.empty:
        print(f"[SKIP] {table_name} empty")
        return

    df = df.where(pd.notnull(df), None)
    cols_def = ", ".join([f"{c} {map_dtype(df[c].dtype)}" for c in df.columns])

    if not unique_cols:
        with engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {schema}.{table_name} ({cols_def})"))
            data = df.to_dict(orient="records")
            if data:
                for row in data:
                    for k, v in row.items():
                        if pd.isna(v): row[k] = None
            cols_str = ", ".join(df.columns)
            vals_str = ", ".join([f":{c}" for c in df.columns])
            query = f"INSERT INTO {schema}.{table_name} ({cols_str}) VALUES ({vals_str})"
            conn.execute(text(query), data)
        print(f"[APPEND] {table_name} appended ({len(df)} rows)")
        return

    staging_table = f"temp_stg_{table_name}"
    cols_to_drop = [c for c in df.columns if c.endswith('_id')]
    df_for_stg = df.drop(columns=cols_to_drop)
    df_for_stg = ensure_columns(df_for_stg, unique_cols)

    columns_list = ", ".join(df_for_stg.columns)
    unique_condition = " AND ".join([f"target.{c} = staging.{c}" for c in unique_cols])
    
    upsert_query = f"""
    INSERT INTO {schema}.{table_name} ({columns_list})
    SELECT staging.{columns_list.replace(', ', ', staging.')} 
    FROM {schema}.{staging_table} AS staging
    WHERE NOT EXISTS (
        SELECT 1 FROM {schema}.{table_name} AS target
        WHERE {unique_condition}
    );
    """

    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS {schema}.{table_name} ({cols_def})"))
        conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{staging_table}"))
        conn.execute(text(f"CREATE TABLE {schema}.{staging_table} AS SELECT * FROM {schema}.{table_name} LIMIT 0"))
        
        data = df_for_stg.to_dict(orient="records")
        if data:
            for row in data:
                for k, v in row.items():
                    if pd.isna(v): row[k] = None
            cols_str = ", ".join(df_for_stg.columns)
            vals_str = ", ".join([f":{c}" for c in df_for_stg.columns])
            query = f"INSERT INTO {schema}.{staging_table} ({cols_str}) VALUES ({vals_str})"
            conn.execute(text(query), data)
            
        conn.execute(text(upsert_query))
        conn.execute(text(f"DROP TABLE {schema}.{staging_table}"))
        print(f"[LOAD] {table_name} processed via SQL Engine (Auto-ID maintained).")

# ============================================================
# 1. DIMENSION: LOCATION (UNCHANGED but aligned)
# ============================================================

def build_dim_location(df):
    loc_df = df[["location"]].drop_duplicates().copy()

    norm = normalize_location_pro(loc_df, "location")
    loc_df = pd.concat([loc_df, norm], axis=1)

    loc_df = loc_df.drop_duplicates(subset=["location"])
    # loc_df["location_id"] = range(1, len(loc_df) + 1)

    return loc_df[[
        # "location_id",
        "location",
        "city",
        "country"
        ]]


# ============================================================
# 2. DIMENSION: DATE (NEW)
# ============================================================
    
def build_dim_date(df):
    df = df.copy()

    df["posted_date"] = clean_datetime(df["posted_date"])

    # ✅ remove time → keep only date
    df["posted_date"] = df["posted_date"].dt.date

    dim = df[["posted_date"]].dropna().drop_duplicates()

    dim["day"] = pd.to_datetime(dim["posted_date"]).dt.day
    dim["month"] = pd.to_datetime(dim["posted_date"]).dt.month
    dim["month_name"] = pd.to_datetime(dim["posted_date"]).dt.month_name()
    dim["quarter"] = pd.to_datetime(dim["posted_date"]).dt.quarter
    dim["year"] = pd.to_datetime(dim["posted_date"]).dt.year
    dim["day_of_week"] = pd.to_datetime(dim["posted_date"]).dt.day_name()
    dim = dim.rename(columns={'posted_date': 'date'})

    # dim["date_id"] = range(1, len(dim) + 1)
    return dim
# ============================================================
# 3. DIMENSION: COMPANY (NEW)
# ============================================================

def build_dim_company(df):
    df = ensure_columns(df, ["company_name"])

    dim = df[["company_name"]].drop_duplicates()
    # dim["company_id"] = range(1, len(dim) + 1)

    return dim[[ "company_name"]]


# ============================================================
# 4. DIMENSION: CONTRACT TYPE (NEW)
# ============================================================

def build_dim_contract_type(df):
    df = ensure_columns(df, ["contract_type_std"])

    dim = df[["contract_type_std"]].dropna().drop_duplicates()
    # dim["contract_type_id"] = range(1, len(dim) + 1)

    return dim.rename(columns={"contract_type_std": "contract_type"})[
        [ "contract_type"]
    ]


# ============================================================
# 6. AGGREGATIONS (UPDATED LOGIC ALIGNMENT)
# ============================================================

def jobs_per_country(df):
    df = ensure_columns(df, ["country"])

    return (
        df.groupby([ "country"])
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
    df = ensure_columns(df, ["contract_type_std"])

    return (
        df.groupby("contract_type_std")
        .size()
        .reset_index(name="job_count")
        .sort_values("job_count", ascending=False)
    )


def salary_trends(df):
    df = df.copy()
    df = compute_salary_avg(df)

    # df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df["posted_date"] = clean_datetime(df["posted_date"])
    return (
        df.groupby("posted_date")["salary_avg"]
        .mean()
        .reset_index()
        .sort_values("posted_date")
    )


# ============================================================
# 7. SKILLS + ML FEATURES (NLP EXTRACTION)
# ============================================================

def job_features(df):
    df = df.copy()
    import re

    df["job_description"] = df["job_description"].fillna("")
    df["location"] = df["location"].fillna("")

    # Comprehensive IT ontology for real-world NLP extraction
    TECH_SKILLS = [
        "python", "sql", "r", "sas", "excel", "power bi", "tableau", "looker", "qlik", "alteryx", "matlab",
        "aws", "azure", "gcp", "hadoop", "spark", "pyspark", "kafka", "snowflake", "bigquery", "redshift", "databricks",
        "docker", "kubernetes", "airflow", "dbt", "terraform", "jenkins", "gitlab", "ansible", "linux", "git",
        "java", "scala", "c\+\+", "c#", "go", "rust", "javascript", "typescript", "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring", "php", "html", "css",
        "pandas", "numpy", "scikit-learn", "tensorflow", "keras", "pytorch", "huggingface", "nlp", "computer vision",
        "postgresql", "mysql", "mongodb", "cassandra", "redis", "elasticsearch", "neo4j", "oracle"
    ]

    def extract_skills(text):
        if not text:
            return ""
        text_lower = str(text).lower()
        found_skills = []
        for skill in TECH_SKILLS:
            # Word boundary matching to avoid partial matches (e.g., 'go' inside 'good')
            # Using custom boundary for tech names with special chars like C++
            escaped_skill = skill # already escaped c\+\+ in the list but others are safe
            pattern = r'(?<![a-zA-Z0-9_])' + escaped_skill + r'(?![a-zA-Z0-9_])'
            if re.search(pattern, text_lower):
                clean_skill = skill.replace('\+', '+').title() if len(skill) > 3 else skill.replace('\+', '+').upper()
                found_skills.append(clean_skill)
        return ", ".join(found_skills)

    # Apply the Regex NLP extraction to the job descriptions
    df["extracted_skills"] = df["job_description"].apply(extract_skills)

    # ============================================================
    # ADVANCED BERT SEMANTIC EXTRACTION (NER)
    # Extracting meaning from context, not just word-by-word
    # ============================================================
    def extract_semantic_entities(text_series):
        try:
            from transformers import pipeline
            import os
            
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
            
            total = len(text_series)
            processed = 0
            
            def extract(text):
                nonlocal processed
                processed += 1
                if processed % 50 == 0:
                    print(f"  [BERT] Traitement en cours... {processed}/{total} offres analysées.")
                    
                if not text: return ""
                text = str(text)[:1500] 
                entities = ner_pipeline(text)
                extracted = [ent['word'] for ent in entities if ent['entity_group'] in ['ORG', 'MISC']]
                cleaned = list(set([str(w).strip().replace("##", "") for w in extracted if len(str(w)) > 2]))
                return ", ".join(cleaned)
                
            return text_series.apply(extract)
        except Exception as e:
            print(f"[WARNING] Advanced BERT extraction failed: {e}")
            return text_series.apply(lambda x: "")

    print("[INFO] Running Advanced BERT Semantic Extraction... This may take a moment.")
    df["semantic_entities"] = extract_semantic_entities(df["job_description"])

    df["remote"] = df["location"].str.contains("remote", case=False).astype(int)
    df = compute_salary_avg(df)

    return df[[
        "job_id",
        "extracted_skills",
        "semantic_entities",
        "remote",
        "salary_avg"
    ]]