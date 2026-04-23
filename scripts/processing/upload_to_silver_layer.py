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
# from scripts.processing.standardizer import standardize_adzuna_data, standardize_arbeitnow_data, standardize_reed_data
# from scripts.processing.transformer import transform_adzuna_data, transform_arbeitnow_data, transform_reed_data

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
    logger.info(f"[READ] Reading from bronze: {key}")
    response = s3.get_object(Bucket=BRONZE_BUCKET, Key=key)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data


# =========================
# 5️⃣ UPLOAD TO SILVER
# =========================
from io import BytesIO

def upload_to_silver(s3, df, source_name, timestamp):
    """
    Upload a transformed DataFrame to the Silver layer in JSON format.

    Args:
        s3: boto3 client
        df (pd.DataFrame): cleaned dataframe
        source_name (str): data source (reed, adzuna, etc.)
        timestamp (str|int): ingestion/cleaning timestamp
    """

    if df.empty:
        logger.warning(f"[Silver] Empty DataFrame for {source_name}, skipping upload")
        return

    # =========================
    # Define key (partitioned)
    # =========================
    silver_key = f"{source_name}/cleaning_timestamp={timestamp}/data.json"

    logger.info(f"[Silver] Preparing JSON upload -> {silver_key}")

    # =========================
    # Convert DataFrame → JSON in memory
    # =========================
    import pandas as pd
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    json_str = json.dumps(records, ensure_ascii=False, indent=4)
    buffer = BytesIO(json_str.encode("utf-8"))

    # =========================
    # Upload to MinIO
    # =========================
    s3.put_object(
        Bucket=SILVER_BUCKET,
        Key=silver_key,
        Body=buffer,
        ContentType="application/json"
    )

    logger.info(
        f"[Silver] Uploaded JSON: {SILVER_BUCKET}/{silver_key} "
        f"({len(df)} records, {buffer.getbuffer().nbytes} bytes)"
    )

# def upload_to_silver(s3, df, source_name, timestamp):
#     """
#     Upload a transformed DataFrame to the Silver layer in Parquet format.

#     Args:
#         s3: boto3 client
#         df (pd.DataFrame): cleaned dataframe
#         source_name (str): data source (reed, adzuna, etc.)
#         timestamp (str|int): ingestion/cleaning timestamp
#     """

#     if df.empty:
#         logger.warning(f"[Silver] Empty DataFrame for {source_name}, skipping upload")
#         return

#     # =========================
#     # Define key (partitioned)
#     # =========================
#     silver_key = f"{source_name}/cleaning_timestamp={timestamp}/data.parquet"

#     logger.info(f"[Silver] Preparing Parquet upload -> {silver_key}")

#     # =========================
#     # Convert DataFrame → Parquet in memory
#     # =========================
#     buffer = BytesIO()
#     df.to_parquet(buffer, index=False, engine="pyarrow")
#     buffer.seek(0)

#     # =========================
#     # Upload to MinIO
#     # =========================
#     s3.put_object(
#         Bucket=SILVER_BUCKET,
#         Key=silver_key,
#         Body=buffer,
#         ContentType="application/octet-stream"
#     )

#     logger.info(
#         f"[Silver] Uploaded Parquet: {SILVER_BUCKET}/{silver_key} "
#         f"({len(df)} records, {buffer.getbuffer().nbytes} bytes)"
#     )

# =========================
# 6️⃣ PROCESSING PIPELINES (per source)
# =========================

def process_arbeitnow(s3, bronze_key, timestamp):
    
    return


def process_adzuna(s3, bronze_key, timestamp):
    """Full pipeline: Bronze → Clean → Standardize → Transform → Silver"""
    logger.info("=" * 50)
    logger.info("[START] Processing Adzuna")

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
    """Full pipeline: Bronze → Clean → Standardize → Transform → Silver"""
    logger.info("=" * 50)
    logger.info("[START] Processing Reed")

    # Read from Bronze
    raw_data = read_from_bronze(s3, bronze_key)
    print('1111111')
    # Clean
    df = clean_reed_data(raw_data)
    print(df)
    logger.info(f"   Cleaned: {len(df)} records")

    # Upload to Silver
    upload_to_silver(s3, df, "reed", timestamp)

    return df


# =========================
# 7️⃣ MAIN PIPELINE
# =========================
def get_latest_bronze_key(s3, source_name):
    """Finds the most recent JSON file for a source in the bronze bucket."""
    try:
        response = s3.list_objects_v2(Bucket=BRONZE_BUCKET, Prefix=f"{source_name}/")
        if 'Contents' not in response:
            return None
        
        valid_objects = [obj for obj in response['Contents'] if obj['Key'].endswith('.json')]
        if not valid_objects:
            return None
            
        valid_objects.sort(key=lambda obj: obj['LastModified'], reverse=True)
        return valid_objects[0]['Key']
    except Exception as e:
        logger.error(f"Error listing objects for {source_name}: {e}")
        return None


def run_pipeline():
    logger.info("[START] Silver layer pipeline started")

    s3 = get_minio_client()
    create_bucket_if_not_exists(s3, SILVER_BUCKET)
    timestamp = int(time.time())

    # ---- Sources to process ----
    # Add or comment out sources as needed
    # bronze_key is left empty to be fetched dynamically

    sources = {
        "adzuna": {
            "process_fn": process_adzuna,
        },
        # "arbeitnow": {
        #     "process_fn": process_arbeitnow,
        # },
        # "reed": {
        #     "process_fn": process_reed,
        # },
    }
    for source_name, config in sources.items():
        try:
            bronze_key = get_latest_bronze_key(s3, source_name)
            if not bronze_key:
                logger.warning(f"[SKIP] No bronze file found for {source_name}")
                continue
                
            logger.info(f"Using dynamic bronze key for {source_name}: {bronze_key}")
            config["process_fn"](s3, bronze_key, timestamp)
        except Exception as e:
            logger.exception(f"[ERROR] Error processing {source_name}: {e}")

    logger.info("[DONE] Silver layer pipeline finished")


# =========================
# 8️⃣ ENTRY POINT
# =========================
if __name__ == "__main__":
    run_pipeline()
