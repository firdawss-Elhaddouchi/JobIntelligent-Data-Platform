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

# Import Cleaning and Standardization utilities
from scripts.processing.cleaner import clean_adzuna_data, clean_arbeitnow_data, clean_reed_data
from scripts.processing.standardizer import standardize_data , fetch_rates_to_mad

# to run use this : python -m scripts.processing.upload_to_silver_layer

logger = setup_logger("silver_layer")


# =========================
# 1-  LOAD ENV
# =========================
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

BRONZE_BUCKET = "bronze"
SILVER_BUCKET = "silver"


# =========================
# 2-  MINIO CLIENT
# =========================
def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
    )

# ============================================================
# 3- UTILITY FUNCTIONS
# ============================================================
def get_latest_bronze_key(s3, source_name):
    """
    Scans the bronze bucket to find the most recent ingestion timestamp folder.
    Ensures the pipeline always processes the freshest raw data.
    """
    prefix = f"{source_name}/"
    try:
        # List objects with a delimiter to find 'folders' representing timestamps
        response = s3.list_objects_v2(Bucket=BRONZE_BUCKET, Prefix=prefix, Delimiter='/')
        
        if 'CommonPrefixes' not in response:
            return None
        
        # Extract folder paths and sort them alphabetically (works for timestamps)
        folders = [p['Prefix'] for p in response['CommonPrefixes']]
        latest_folder = sorted(folders)[-1] 
        
        return f"{latest_folder}data.json"
    except Exception as e:
        logger.error(f"Error finding latest bronze key for {source_name}: {e}")
        return None
    

# =========================
# 4-  BUCKET CHECK
# =========================
def create_bucket_if_not_exists(s3, bucket_name):
    """
    Checks if a bucket exists in MinIO; if not, creates it.
    Essential for first-time setup and system resilience.
    """
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket exists: {bucket_name}")
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        logger.info(f"Bucket created: {bucket_name}")


# =========================
# 5- READ FROM BRONZE
# =========================
def read_from_bronze(s3, key):
    """Download and parse a JSON file from the bronze bucket."""
    logger.info(f"[READ] Reading from bronze: {key}")
    response = s3.get_object(Bucket=BRONZE_BUCKET, Key=key)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data



# =========================
# 6- UPLOAD TO SILVER
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
# 7-  PROCESSING PIPELINES (per source)
# =========================

# def process_arbeitnow(s3, bronze_key, timestamp, rates_map):
#     """Full pipeline for Arbeitnow: Bronze → Clean → Standardize → Silver"""
#     logger.info("=" * 50)
#     logger.info("🔄 Processing Arbeitnow")

#     try:
#         # 1. Read Raw Data from Bronze (MinIO)
#         # Note: Arbeitnow data is usually a list of jobs or {"data": [...]}
#         raw_data = read_from_bronze(s3, bronze_key)
        
#         # In case the JSON has a 'data' envelope from the API
#         if isinstance(raw_data, dict) and "data" in raw_data:
#             raw_data = raw_data["data"]

#         # 2. Step: Clean
#         # Aligns columns to Canonical Schema and handles basic text cleaning
#         df = clean_arbeitnow_data(raw_data)
#         logger.info(f"   [Clean] Initial transformation complete: {len(df)} records")

#         # 3. Step: Standardize (Applying our Core Standardization Logic)
#         # Note: You need to make sure standardize_arbeitnow_data is imported 
#         # or call your standardizer script here.
#         df = standardize_data(df, 'Arbeitnow', rates_map) 
#         logger.info(f"   [Standardize] Currency, Dates, and IDs unified")

#         # 4. Upload to Silver Layer in Parquet Format
#         upload_to_silver(s3, df, "arbeitnow", timestamp)

#         return df

#     except Exception as e:
#         logger.error(f"❌ Failed to process Arbeitnow from {bronze_key}: {e}")
#         raise


# def process_adzuna(s3, bronze_key, timestamp, rates_map):
#     """Full pipeline: Bronze → Clean → Standardize → Transform → Silver"""
#     logger.info("=" * 50)
#     logger.info("🔄 Processing Adzuna")

#     # Read from Bronze
#     raw_data = read_from_bronze(s3, bronze_key)

#     # Clean
#     df = clean_adzuna_data(raw_data)
#     logger.info(f"   Cleaned: {len(df)} records")

#     # # Standardize
#     df = standardize_data(df, 'Adzuna', rates_map) 
#     logger.info(f"   Standardized: {len(df)} records")

#     # # Transform
#     # df = transform_adzuna_data(df)
#     # logger.info(f"   Transformed: {len(df)} records")

#     # Upload to Silver
#     upload_to_silver(s3, df, "adzuna", timestamp)

#     return df


# def process_reed(s3, bronze_key, timestamp, rates_map):
#     """Full pipeline: Bronze → Clean → Standardize → Transform → Silver"""
#     logger.info("=" * 50)
#     logger.info("🔄 Processing Adzuna")

#     # Read from Bronze
#     raw_data = read_from_bronze(s3, bronze_key)
#     # Clean
#     df = clean_reed_data(raw_data)
#     logger.info(f"   Cleaned: {len(df)} records")

#     df = standardize_data(df, 'Reed', rates_map) 
#     logger.info(f"   Standardized: {len(df)} records")


#     # Upload to Silver
#     upload_to_silver(s3, df, "reed", timestamp)

#     return df

def process_source(s3, source_name, bronze_key, timestamp, rates_map):
    """
    Full processing logic for a single source:
    Download (Bronze) -> Clean (Structural) -> Standardize (Values) -> Upload (Silver)
    """
    logger.info(f"🔄 Starting Pipeline for {source_name}...")
    
    # A. Ingestion: Read Raw Data
    raw_data = read_from_bronze(s3, bronze_key)
    
    # Unwrap 'data' envelope if present (common in Arbeitnow API)
    if source_name == "arbeitnow" and isinstance(raw_data, dict):
        raw_data = raw_data.get("data", [])

    # B. Cleaning Step: Map columns and basic text cleanup
    clean_map = {
        "adzuna": clean_adzuna_data,
        "reed": clean_reed_data,
        "arbeitnow": clean_arbeitnow_data
    }
    df = clean_map[source_name](raw_data)
    logger.info(f"   [1/2] Cleaning finished for {source_name}")
    
    # C. Standardization Step: MAD conversion, UTC dates, and ID Namespacing
    df = standardize_data(df, source_name, rates_map)
    logger.info(f"   [2/2] Standardization finished for {source_name}")
    
    # D. Persistence: Upload result as Parquet to Silver Layer
    upload_to_silver(s3, df, source_name, timestamp)

# # =========================
# # 7 MAIN PIPELINE
# # =========================
# def run_pipeline():
#     logger.info("🚀 Silver layer pipeline started")

#     s3 = get_minio_client()
#     create_bucket_if_not_exists(s3, SILVER_BUCKET)
#     timestamp = int(time.time())

#     rates_map = fetch_rates_to_mad()

#     # ---- Sources to process ----
#     # Add or comment out sources as needed

#     sources = {
#         # "adzuna": {
#         #     "bronze_key": "adzuna/ingestion_timestamp=1776337261/data.json",
#         #     "process_fn": process_adzuna,
#         # },
#         # "arbeitnow": {
#         #     "bronze_key": "arbeitnow/ingestion_timestamp=XXXXXXXXXX/data.json",
#         #     "process_fn": process_arbeitnow,
#         # },
#         "reed": {
#             "bronze_key": "reed/ingestion_timestamp=1776414536/data.json",
#             "process_fn": process_reed,
#         },
#     }
#     for source_name, config in sources.items():
#         try:
#             config["process_fn"](s3, config["bronze_key"], timestamp)
#         except Exception as e:
#             logger.exception(f"❌ Error processing {source_name}: {e}")

#     logger.info("✅ Silver layer pipeline finished")


# ============================================================
# 8. MASTER PIPELINE EXECUTION
# ============================================================

def run_pipeline():
    """
    Main entry point for the Silver Layer pipeline.
    Suitable for execution via Airflow PythonOperator.
    """
    logger.info("🚀 Silver Layer Transformation Pipeline Started")
    s3 = get_minio_client()
    
    # --- CRITICAL STEP: Ensure the destination exists before processing ---
    create_bucket_if_not_exists(s3, SILVER_BUCKET) #
    
    # Fetch exchange rates once for the entire batch to optimize performance
    rates_map = fetch_rates_to_mad() 
    
    # Unique timestamp for this processing run
    current_timestamp = int(time.time())

    # List of sources to be processed in this batch
    active_sources = ["reed", "arbeitnow", "adzuna"]

    for source in active_sources:
        try:
            # Dynamically find the latest data available in Bronze
            bronze_key = get_latest_bronze_key(s3, source)
            
            if bronze_key:
                process_source(s3, source, bronze_key, current_timestamp, rates_map)
            else:
                logger.warning(f"⚠️ No data found in Bronze for source: {source}")
                
        except Exception as e:
            logger.error(f"❌ Critical failure while processing {source}: {str(e)}")

# CLI Entry point
if __name__ == "__main__":
    run_pipeline()