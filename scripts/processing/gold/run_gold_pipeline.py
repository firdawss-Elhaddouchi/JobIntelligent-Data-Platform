"""
Gold Layer Pipeline
-------------------
Reads cleaned data from Silver (MinIO),
applies transformations,
and writes results to Gold bucket.
"""

import time
import pandas as pd
from io import BytesIO
import boto3
from botocore.exceptions import ClientError


from scripts.processing.gold.gold_transformations import (
    build_jobs_fact,
    jobs_per_location,
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
GOLD_BUCKET = "gold"


# =========================
# MINIO CLIENT
# =========================
def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )


# =========================
# GET LATEST SILVER DATA
# =========================
def get_latest_silver_key(s3, source_name):

    prefix = f"{source_name}/"

    response = s3.list_objects_v2(
        Bucket=SILVER_BUCKET,
        Prefix=prefix,
        Delimiter="/"
    )

    if "CommonPrefixes" not in response:
        return None

    folders = [p["Prefix"] for p in response["CommonPrefixes"]]
    latest_folder = sorted(folders)[-1]
    print(latest_folder)
    return f"{latest_folder}data.parquet"


# =========================
# READ SILVER
# =========================
def read_silver_data(s3, key):

    response = s3.get_object(Bucket="silver", Key=key)

    import pandas as pd
    from io import BytesIO

    buffer = BytesIO(response["Body"].read())

    df = pd.read_parquet(buffer)

    return df


# =========================
# UPLOAD GOLD
# =========================

def create_bucket_if_not_exists(s3, bucket_name):
    """
    Checks if a bucket exists in MinIO; if not, creates it.
    Essential for first-time setup and system resilience.
    """
    try:
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        # logger.info(f"Bucket created: {bucket_name}")

def upload_gold(s3, df, table_name, timestamp):

    if df.empty:
        print(f"[Gold] {table_name} is empty, skipping")
        return

    key = f"{table_name}/timestamp={timestamp}/data.json"

    json_str = df.to_json(orient="records", force_ascii=False)
    buffer = BytesIO(json_str.encode("utf-8"))

    s3.put_object(
        Bucket=GOLD_BUCKET,
        Key=key,
        Body=buffer,
        ContentType="application/json"
    )

    print(f"[Gold] Uploaded {table_name} ({len(df)} rows)")


# =========================
# MAIN PIPELINE
# =========================
def run_gold_pipeline():

    print("🚀 Starting Gold pipeline...")

    s3 = get_minio_client()
    timestamp = int(time.time())

    sources = ["reed", "adzuna", "arbeitnow"]

    all_dfs = []

    # 1. Load all sources from Silver
    for source in sources:

        key = get_latest_silver_key(s3, source)

        if not key:
            print(f"No data for {source}")
            continue

        df = read_silver_data(s3, key)

        df["source"] = source

        all_dfs.append(df)

    if not all_dfs:
        print("No data found in Silver")
        return

    # 2. Merge all sources
    df_all = pd.concat(all_dfs, ignore_index=True)

    # 3. Remove duplicates
    df_all = df_all.drop_duplicates(subset=["job_id"])

    # 4. Build Gold tables
    fact = build_jobs_fact(df_all)
    loc = jobs_per_location(df_all)
    comp = jobs_per_company(df_all)
    sal = salary_trends(df_all)
    skills = skills_demand(df_all)
    features = job_features(df_all)

    # 5. Upload to Gold
    create_bucket_if_not_exists(s3,GOLD_BUCKET)
    upload_gold(s3, fact, "jobs_fact", timestamp)
    upload_gold(s3, loc, "jobs_per_location", timestamp)
    upload_gold(s3, comp, "jobs_per_company", timestamp)
    upload_gold(s3, sal, "salary_trends", timestamp)
    upload_gold(s3, skills, "skills_demand", timestamp)
    upload_gold(s3, features, "job_features", timestamp)

    print("✅ Gold pipeline completed")


# CLI
if __name__ == "__main__":
    run_gold_pipeline()