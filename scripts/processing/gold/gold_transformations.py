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
from sqlalchemy import text
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


def safe_replace(df, table_name, engine, schema="gold"):
    if df.empty:
        print(f"[SKIP] {table_name} empty")
        return

    with engine.begin() as conn:
        df.to_sql(table_name, conn, schema=schema, if_exists="replace", index=False)
    print(f"[REPLACE] {table_name} refreshed ({len(df)} rows)")


def safe_append(df, table_name, engine, schema="gold", unique_cols=None):
    if df.empty:
        print(f"[SKIP] {table_name} empty")
        return

    # 1. Upload new data to a temporary staging table
    staging_table = f"temp_stg_{table_name}"
    # Remove 'date_id' or 'location_id' if they exist in the DF so they don't interfere
    cols_to_drop = [c for c in df.columns if c.endswith('_id')]
    df_for_stg = df.drop(columns=cols_to_drop)
    
    # 2. Get list of columns (excluding the auto-increment ID)
    columns_list = ", ".join(df_for_stg.columns)
    unique_condition = " AND ".join([f"target.{col} = staging.{col}" for col in unique_cols])
    
    # 3. Build the SQL with explicit columns
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
        df_for_stg.to_sql(staging_table, conn, schema=schema, if_exists="replace", index=False)
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
# 7. SKILLS + ML FEATURES (UNCHANGED)
# ============================================================

def job_features(df):
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