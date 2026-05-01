import json
import time
import os
import sys
from dotenv import load_dotenv
import boto3
from io import BytesIO
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.common.logging_config import setup_logger

# Import Cleaning and Standardization utilities
from scripts.processing.silver.cleaner import clean_adzuna_data, clean_arbeitnow_data, clean_reed_data
from scripts.processing.silver.standardizer import standardize_data, fetch_rates_to_mad
# to run use this : python -m scripts.processing.silver.upload_to_silver_layer

logger = setup_logger("silver_layer")


# =========================
# 1-  LOAD ENV
# =========================
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
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
    try:
        response = s3.get_object(Bucket=BRONZE_BUCKET, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        return data
    except Exception as e:
        logger.error(f"❌ Failed to read or parse JSON from Bronze: {str(e)}")
        raise
    
def upload_to_silver(s3, df, source_name, timestamp):
    """
    Converts the cleaned DataFrame to Parquet format and uploads it to the Silver bucket.
    Parquet is used here to preserve data types (schema) and provide efficient storage.
    """

    if df.empty:
        logger.warning(f"[Silver] Empty DataFrame for {source_name}, skipping upload.")
        return

    # 1. Construct the partitioned S3 key with .parquet extension
    silver_key = f"{source_name}/cleaning_timestamp={timestamp}/data.parquet"

    logger.info(f"[Silver] Preparing Parquet serialization for {source_name} -> {silver_key}")

    try:
        # 2. Serialize DataFrame to Parquet in-memory using BytesIO
        # 'pyarrow' engine is used for better performance and stability
        buffer = BytesIO()
        df.to_parquet(buffer, index=False, engine='pyarrow')
        
        # Reset buffer pointer to the beginning before uploading
        buffer.seek(0)

        # 3. Stream the buffer to MinIO (S3)
        s3.put_object(
            Bucket=SILVER_BUCKET,
            Key=silver_key,
            Body=buffer,
            ContentType="application/x-parquet"
        )

        logger.info(
            f"[Silver] Successfully uploaded Parquet: {SILVER_BUCKET}/{silver_key} "
            f"({len(df)} records, {buffer.getbuffer().nbytes} bytes)"
        )
    except Exception as e:
        logger.error(f"[Silver] Failed to upload {source_name} to Silver Layer: {str(e)}")
        raise

# =========================
# 7-  PROCESSING PIPELINES (per source)
# =========================

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