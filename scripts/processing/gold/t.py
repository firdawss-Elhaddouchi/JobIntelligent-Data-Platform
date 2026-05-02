import time
import pandas as pd
import boto3
from sqlalchemy import create_engine
from io import BytesIO
import os
from dotenv import load_dotenv

load_dotenv()

from scripts.processing.gold.gold_transformations import (
    build_jobs_fact,
    build_dim_location,
    jobs_per_country,
    jobs_per_company,
    salary_trends,
    skills_demand,
    job_features
)



# =========================
# CONFIG
# =========================
MINIO_ENDPOINT = "http://localhost:9000"
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"

SILVER_BUCKET = "silver"

# POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"
POSTGRES_URI = os.getenv("POSTGRES_URI")


# =========================
# CLIENTS
# =========================
def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

def get_engine():
    return create_engine(POSTGRES_URI)


# =========================
# SILVER READER
# =========================
def read_parquet(s3, key):
    obj = s3.get_object(Bucket=SILVER_BUCKET, Key=key)
    return pd.read_parquet(BytesIO(obj["Body"].read()))


# =========================
# LOAD TO POSTGRES
# =========================
def load(df, table, engine):
    if df.empty:
        print(f"[SKIP] {table}")
        return

    df.to_sql(
        table,
        engine,
        schema="gold",
        if_exists="append",
        index=False
    )

    print(f"[OK] Loaded {table} -> {len(df)} rows")


# =========================
# PIPELINE
# =========================
def run_gold_pipeline():

    print("🚀 Gold ETL starting...")

    s3 = get_s3()
    engine = get_engine()

    sources = ["reed", "adzuna", "arbeitnow"]
    all_data = []

    # 1. Load Silver
    for src in sources:
        key = get_latest_silver_key(s3, src)

        try:
            df = read_parquet(s3, key)
            df["source"] = src
            all_data.append(df)
        except Exception as e:
            print(f"[WARN] {src} failed: {e}")

    df_all = pd.concat(all_data, ignore_index=True)

    # 2. Transform
    dim_location = build_dim_location(df_all)
    fact = build_jobs_fact(df_all, dim_location)

    loc = jobs_per_country(df_all)
    comp = jobs_per_company(df_all)
    sal = salary_trends(df_all)
    skills = skills_demand(df_all)
    features = job_features(df_all)

    # 3. Load (Gold = PostgreSQL ONLY)
    load(dim_location, "dim_location", engine)
    load(fact, "jobs_fact", engine)
    load(loc, "jobs_per_location", engine)
    load(comp, "jobs_per_company", engine)
    load(sal, "salary_trends", engine)
    load(skills, "skills_demand", engine)
    load(features, "job_features", engine)

    print("✅ Gold pipeline done")


if __name__ == "__main__":
    run_gold_pipeline()