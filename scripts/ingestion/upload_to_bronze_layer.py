import requests
import json
import time
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import boto3
from io import BytesIO
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.ingestion import reed_client
from scripts.ingestion import adzuna_client
from scripts.ingestion.arbeitnow_client import collect_arbeitnow
from scripts.ingestion import arbeitnow_client
from scripts.ingestion import arbeitnow_client
from scripts.common import logging_config
logger = logging_config.setup_logger("upload to bronze layer")
# to run use this : python -m scripts.ingestion.upload_to_bronze_layer


# =========================
# 2️⃣ LOAD ENV
# =========================
load_dotenv()

REED_API_KEY = os.getenv("REED_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")

BUCKET = "bronze"
METADATA_KEY = "metadata/last_run.json"

DATA_KEYWORDS = [
"data", "données", "analyst", "engineer", "science",
"machine learning", "ai", "intelligence artificialielle",
"bi", "business intelligence", "big data", "etl", "python"
]
# =========================
# 3️⃣ MINIO CLIENT
# =========================
def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD
    )

# =========================
# 4️⃣ BUCKET CHECK
# =========================
def create_bucket_if_not_exists(s3, bucket_name):
    try:
        s3.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket exists: {bucket_name}")
    except ClientError:
        s3.create_bucket(Bucket=bucket_name)
        logger.info(f"Bucket created: {bucket_name}")

# =========================
# 5️⃣ UPLOAD TO MINIO
# =========================
def upload_to_minio(s3, key, data):
    # json_bytes = json.dumps(data).encode("utf-8")
    json_bytes = json.dumps(data, indent=4).encode("utf-8")

    create_bucket_if_not_exists(s3, BUCKET)

    logger.info(f"Uploading ->{key}")

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=BytesIO(json_bytes),
        ContentType="application/json"
    )

# =========================
# 6️⃣ LAST RUN MANAGEMENT
# =========================
def get_last_run(s3):
    try:
        response = s3.get_object(Bucket=BUCKET, Key=METADATA_KEY)
        data = json.loads(response["Body"].read().decode("utf-8"))

        last_run = datetime.fromisoformat(data["last_run"])

        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)

        logger.info(f"Loaded last_run: {last_run.isoformat()}")
        return last_run

    except Exception:
        fallback = datetime.now(timezone.utc) - timedelta(hours=24)
        logger.warning(f"No last_run found -> fallback: {fallback.isoformat()}")
        return fallback

def save_last_run(s3, timestamp):
    data = {"last_run": timestamp.isoformat()}

    s3.put_object(
        Bucket=BUCKET,
        Key=METADATA_KEY,
        Body=json.dumps(data).encode("utf-8"),
        ContentType="application/json"
    )

    logger.info(f"Saved last_run: {timestamp.isoformat()}")




# =========================
# 7️⃣ DATA SOURCES
# =========================
def collect_arbeitnow(last_run):
    logger.info("Arbeitnow ingestion started")

    all_jobs = arbeitnow_client.collect_arbeitnow()
    # all_new_jobs = arbeitnow_client.filter_new_jobs(all_jobs, last_run)

    logger.info(f"Arbeitnow filtered {len(all_jobs)} new jobs")
    return all_jobs

def collect_adzuna(last_run):
    logger.info("Adzuna ingestion started")

    all_jobs = adzuna_client.collect_adzuna()
    # all_new_jobs = adzuna_client.filter_new_jobs(all_jobs, last_run)

    logger.info(f"Adzuna filtered {len(all_jobs)} new jobs")
    return all_jobs

def collect_reed(last_run):
    logger.info("Reed ingestion started")

    all_jobs = reed_client.collect_reed()
    # all_new_jobs = reed_client.filter_new_jobs(all_jobs, last_run)

    logger.info(f"Reed filtered {len(all_jobs)} new jobs")
    return all_jobs

# =========================
# 8️⃣ MAIN PIPELINE
# =========================
def run_pipeline():
    logger.info("Pipeline started")

    s3 = get_minio_client()
    timestamp = int(time.time())

    last_run = get_last_run(s3)
    now = datetime.now(timezone.utc)
    print(last_run)
    sources = {
        "adzuna": lambda: collect_adzuna(last_run),
        # "arbeitnow": lambda: collect_arbeitnow(last_run),
        # "reed": lambda: collect_reed(last_run)
        
    }

    for source_name, func in sources.items():
        logger.info(f"Processing source: {source_name}")

        try:
            data = func()

            bronze_data = {
                "source": source_name,
                "collected_at": now.isoformat(),
                "total": len(data),
                "data": data
            }

            prefix = f"{source_name}/ingestion_timestamp={timestamp}"

            upload_to_minio(s3, f"{prefix}/data.json", bronze_data)

            logger.info(f"{source_name} uploaded ({len(data)} records)")

        except Exception as e:
            logger.exception(f"Error in {source_name}: {e}")

    # ✅ Save last_run AFTER success
    save_last_run(s3, now)

    logger.info("Pipeline finished")


# =========================
# 9️⃣ ENTRY POINT
# =========================
if __name__ == "__main__":
    run_pipeline()