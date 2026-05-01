"""
Gold Layer Pipeline (Hybrid Star Schema)
========================================

This script builds the Gold layer of the data pipeline.

Responsibilities:
- Load cleaned Silver data from MinIO
- Build dimension tables (location, date, company, contract type)
- Compute aggregations and analytical features
- Load data into PostgreSQL (dimensions, staging, fact table)

Design:
- Hybrid Star Schema
- Fact table is built using SQL joins from a staging table
- Incremental loading with conflict handling

Author: Data Engineering Pipeline
"""

import pandas as pd
from io import BytesIO
import boto3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
import os

from scripts.common.logging_config import setup_logger
from scripts.common.utilies import get_minio_client,get_postgres_engine

from scripts.processing.gold.gold_transformations import (
    build_dim_location,
    build_dim_date,
    build_dim_company,
    build_dim_contract_type,
    jobs_per_country,
    jobs_per_company,
    jobs_per_contract_type,
    safe_append,
    safe_replace,
    compute_salary_avg,
    # salary_trends,
    job_features
)

# =========================
# CONFIGURATION
# =========================

logger = setup_logger("gold_pipeline")
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

SILVER_BUCKET = "silver"
POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"



# =========================
# SILVER READER
# =========================

def get_today_silver_key(s3, source_name):
    """
    Retrieve today's Silver layer file key for a given source.

    Args:
        s3 (boto3.client): MinIO S3 client
        source_name (str): Data source name (e.g., 'adzuna')

    Returns:
        str | None: S3 key if exists, otherwise None
    """
    today_str = datetime.today().strftime("%Y-%m-%d")
    key = f"{source_name}/cleaning_date={today_str}/data.parquet"

    try:
        response = s3.list_objects_v2(
            Bucket=SILVER_BUCKET,
            Prefix=key
        )

        if 'Contents' in response and len(response['Contents']) > 0:
            logger.info(f"Found Silver data for {source_name}: {key}")
            return key

        logger.warning(f"No Silver data found for {source_name} today")
        return None

    except Exception as e:
        logger.error(f"Error retrieving Silver key for {source_name}: {e}")
        return None


def read_silver_data(s3, key):
    """
    Read a parquet file from MinIO and return as DataFrame.

    Args:
        s3 (boto3.client): MinIO client
        key (str): S3 object key

    Returns:
        pd.DataFrame: Loaded data
    """
    logger.info(f"Reading Silver data: {key}")
    response = s3.get_object(Bucket=SILVER_BUCKET, Key=key)
    buffer = BytesIO(response["Body"].read())
    return pd.read_parquet(buffer)


# =========================
# MAIN PIPELINE
# =========================

def run_gold_pipeline():
    """
    Execute the full Gold layer pipeline.

    Steps:
    1. Load Silver data
    2. Build dimension tables
    3. Compute aggregations
    4. Load into PostgreSQL (dimensions, staging, fact)
    """
    logger.info("Starting Gold pipeline")

    s3 = get_minio_client()
    engine = get_postgres_engine()

    sources = ["reed", "adzuna", "arbeitnow"]
    all_dfs = []

    # -------------------------
    # LOAD SILVER
    # -------------------------
    logger.info("Loading Silver data...")

    for source in sources:
        key = get_today_silver_key(s3, source)

        if not key:
            continue

        df = read_silver_data(s3, key)
        df["source"] = source
        all_dfs.append(df)
        print(df[['posted_date','expires_date']])


    if not all_dfs:
        logger.warning("No data found in Silver layer. Pipeline stopped.")
        return

    df_all = pd.concat(all_dfs, ignore_index=True)
   
    logger.info(f"Loaded {len(df_all)} rows from Silver")

    # -------------------------
    # DIMENSIONS
    # -------------------------
    logger.info("Building dimension tables...")

    dim_location = build_dim_location(df_all)
    dim_date = build_dim_date(df_all)
    dim_company = build_dim_company(df_all)
    dim_contract = build_dim_contract_type(df_all)

    # -------------------------
    # AGGREGATIONS
    # -------------------------
    logger.info("Computing aggregations...")

    loc = jobs_per_country(df_all)
    comp = jobs_per_company(df_all)
    contract = jobs_per_contract_type(df_all)
    # sal = salary_trends(df_all)
    features = job_features(df_all)

    # -------------------------
    # LOAD DIMENSIONS
    # -------------------------
    logger.info("Loading dimensions into PostgreSQL...")

    safe_append(dim_location, "dim_location", engine, unique_cols=["location"])
    safe_append(dim_date, "dim_date", engine, unique_cols=["date"])
    safe_append(dim_company, "dim_company", engine, unique_cols=["company_name"])
    safe_append(dim_contract, "dim_contract_type", engine, unique_cols=["contract_type"])

    # -------------------------
    # STAGING
    # -------------------------
    logger.info("Preparing staging table...")

    df = compute_salary_avg(df_all)
    print("#########################")
    print(df['is_remote'])
    print("#########################")
    df_staging = df[[
        "job_id", "job_title", "company_name", "location",
        "posted_date","expires_date", "contract_type",
        "salary_min", "salary_max", "salary_avg","is_remote",
        "currency", "job_url", "source"
    ]].copy()
    print("#########################")

    df_staging.to_sql(
        "jobs_staging",
        engine,
        schema="gold",
        if_exists="append",
        index=False
    )


    logger.info(f"Inserted {len(df_staging)} rows into staging")

    # -------------------------
    # FACT TABLE
    # -------------------------
    logger.info("Building fact table...")

    sql = """
    INSERT INTO gold.jobs_fact (
        job_id, job_title,
        company_id, location_id, posted_date_id,expires_date_id, contract_type_id,
        salary_min, salary_max, salary_avg,
        currency,is_remote, job_url, source
    )
    SELECT
        s.job_id,
        s.job_title,
        c.company_id,
        l.location_id,
        d1.date_id,
        d2.date_id,
        ct.contract_type_id,
        s.salary_min,
        s.salary_max,
        s.salary_avg,
        s.currency,
        s.is_remote,
        s.job_url,
        s.source
    FROM gold.jobs_staging s
    LEFT JOIN gold.dim_company c ON s.company_name = c.company_name
    LEFT JOIN gold.dim_location l ON s.location = l.location
    LEFT JOIN gold.dim_date d1 ON s.posted_date::DATE = d1.date::DATE
    LEFT JOIN gold.dim_date d2 ON TO_TIMESTAMP(s.expires_date::DOUBLE PRECISION)::DATE = d2.date::DATE
    LEFT JOIN gold.dim_contract_type ct ON s.contract_type = ct.contract_type
    WHERE s.job_id IS NOT NULL
    ON CONFLICT (job_id) DO NOTHING;
    """

    with engine.begin() as conn:
        conn.execute(text(sql))

    # -------------------------
    # SAVE AGGREGATIONS
    # -------------------------
    logger.info("Saving aggregations...")

    safe_replace(loc, "jobs_per_country", engine)
    safe_replace(comp, "jobs_per_company", engine)
    safe_replace(contract, "jobs_per_contract_type", engine)
    # safe_replace(sal, "salary_trends", engine)
    safe_replace(features, "job_features", engine)

    logger.info(" Gold pipeline completed successfully")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_gold_pipeline()