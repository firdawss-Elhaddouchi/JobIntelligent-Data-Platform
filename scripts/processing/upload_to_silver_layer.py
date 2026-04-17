import json
import time
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3
from io import BytesIO
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.common.logging_config import setup_logger

# Processing pipeline
from scripts.processing.cleaner import clean_adzuna_data, clean_arbeitnow_data, clean_reed_data
from scripts.processing.standardizer import standardize_adzuna_data, standardize_arbeitnow_data, standardize_reed_data
from scripts.processing.transformer import transform_adzuna_data, transform_arbeitnow_data, transform_reed_data

# to run use this : python -m scripts.processing.upload_to_silver_layer

logger = setup_logger("silver_layer")


# =========================
# 1️⃣ LOAD ENV
# =========================
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"


# =========================
# 2️⃣ MINIO CLIENT
# =========================
def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
    )


# =========================
# 3️⃣ BUCKET CHECK
# =========================
def create_bucket_if_not_exists(s3, bucket_name):
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket exists: {bucket_name}")
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        logger.info(f"Bucket created: {bucket_name}")


# =========================
# 4️⃣ READ FROM BRONZE
# =========================
def read_from_bronze(s3, key):
    """Download and parse a JSON file from the bronze bucket."""
    logger.info(f"📥 Reading from bronze: {key}")
    response = s3.get_object(Bucket=BRONZE_BUCKET, Key=key)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data


# =========================
# 5️⃣ UPLOAD TO SILVER
# =========================
def upload_to_silver(s3, df, source_name, timestamp):
    """Upload a transformed DataFrame to the silver bucket as JSON."""
    silver_key = f"{source_name}/cleaning_timestamp={timestamp}/data.json"

    silver_data = df.to_json(orient="records", force_ascii=False, indent=2)

    s3.put_object(
        Bucket=SILVER_BUCKET,
        Key=silver_key,
        Body=BytesIO(silver_data.encode("utf-8")),
        ContentType="application/json",
    )

    logger.info(f"📤 Uploaded to silver: {SILVER_BUCKET}/{silver_key} ({len(df)} records)")


# =========================
# 6️⃣ PROCESSING PIPELINES (per source)
# =========================

def process_arbeitnow(s3, bronze_key, timestamp):
    
    return


def process_adzuna(s3, bronze_key, timestamp):
    """Full pipeline: Bronze → Clean → Standardize → Transform → Silver"""
    logger.info("=" * 50)
    logger.info("🔄 Processing Adzuna")

    # Read from Bronze
    raw_data = read_from_bronze(s3, bronze_key)

    # Clean
    df = clean_adzuna_data(raw_data)
    logger.info(f"   Cleaned: {len(df)} records")

    # # Standardize
    # df = standardize_adzuna_data(df)
    # logger.info(f"   Standardized: {len(df)} records")

    # # Transform
    # df = transform_adzuna_data(df)
    # logger.info(f"   Transformed: {len(df)} records")

    # Upload to Silver
    upload_to_silver(s3, df, "adzuna", timestamp)

    return df


def process_reed(s3, bronze_key, timestamp):

    return


# =========================
# 7️⃣ MAIN PIPELINE
# =========================
def run_pipeline():
    logger.info("🚀 Silver layer pipeline started")

    s3 = get_minio_client()
    create_bucket_if_not_exists(s3, SILVER_BUCKET)
    timestamp = int(time.time())

    # ---- Sources to process ----
    # Add or comment out sources as needed

    sources = {
        "adzuna": {
            "bronze_key": "adzuna/ingestion_timestamp=1776337261/data.json",
            "process_fn": process_adzuna,
        },
        # "arbeitnow": {
        #     "bronze_key": "arbeitnow/ingestion_timestamp=XXXXXXXXXX/data.json",
        #     "process_fn": process_arbeitnow,
        # },
        # "reed": {
        #     "bronze_key": "reed/ingestion_timestamp=XXXXXXXXXX/data.json",
        #     "process_fn": process_reed,
        # },
    }

    for source_name, config in sources.items():
        try:
            config["process_fn"](s3, config["bronze_key"], timestamp)
        except Exception as e:
            logger.exception(f"❌ Error processing {source_name}: {e}")

    logger.info("✅ Silver layer pipeline finished")


# =========================
# 8️⃣ ENTRY POINT
# =========================
if __name__ == "__main__":
    run_pipeline()
