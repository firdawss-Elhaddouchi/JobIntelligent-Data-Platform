import requests
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv
import boto3
from io import BytesIO
import reed_client
# =========================
# ENV VARIABLES
# =========================


REED_API_KEY = os.getenv("REED_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
LAST_RUN = "2026-04-15T10:00:00"
# =========================
# MINIO CONFIG
# =========================
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="password123",
)

BUCKET = "bronze"

# =========================
# COMMON FUNCTION
# =========================

def create_bucket_if_not_exists(s3, bucket_name):
    existing_buckets = s3.list_buckets()["Buckets"]

    if not any(b["Name"] == bucket_name for b in existing_buckets):
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Bucket created: {bucket_name}")
    else:
        print(f"ℹ️ Bucket already exists: {bucket_name}")

def upload_to_minio(key, data):
    json_bytes = json.dumps(data).encode("utf-8")
    create_bucket_if_not_exists(s3, BUCKET)
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=BytesIO(json_bytes),
        ContentType="application/json"
    )


# =========================
# ADZUNA
# =========================
def collect_adzuna():
    print("🚀 Adzuna ingestion")

    COUNTRY = "gb"
    MAX_PAGES = 5
    all_jobs = []

    for page in range(1, MAX_PAGES + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{page}"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 50
        }

        r = requests.get(url, params=params)

        if r.status_code != 200:
            print("❌ Adzuna error")
            continue

        data = r.json().get("results", [])
        if not data:
            break

        all_jobs.extend(data)
        time.sleep(1)

    return all_jobs

# =========================
# ARBEITNOW
# =========================
def collect_arbeitnow():
    print("🚀 Arbeitnow ingestion")

    url = "https://www.arbeitnow.com/api/job-board-api"
    all_jobs = []
    page = 1

    while True:
        r = requests.get(url, params={"page": page})

        if r.status_code != 200:
            break

        data = r.json().get("data", [])
        if not data:
            break

        all_jobs.extend(data)
        page += 1

    return all_jobs

# =========================
# REED
# =========================
import requests

def collect_reed():
    print("🚀 Reed ingestion")
    all_jobs = reed_client.collect_reed()
    all_new_jobs = reed_client.filter_new_jobs(all_jobs,LAST_RUN)
    return all_new_jobs

# =========================
# MAIN PIPELINE
# =========================
def run_pipeline():

    timestamp = int(time.time())

    sources = {
        # "adzuna": collect_adzuna,
        # "arbeitnow": collect_arbeitnow,
        "reed": collect_reed
    }

    for source_name, func in sources.items():

        print(f"\n📦 Processing {source_name}")

        try:
            data = func()

            bronze_data = {
                "source": source_name,
                "collected_at": datetime.now().isoformat(),
                "total": len(data),
                "data": data
            }

            prefix = f"{source_name}/ingestion_timestamp={timestamp}"
            print('ok')
            upload_to_minio(f"{prefix}/data.json", bronze_data)
           
            # upload_to_minio(f"{prefix}/failed_requests.raw", [])

            print(f"✅ {source_name} uploaded to MinIO")

        except Exception as e:
            print(f"❌ Error in {source_name}: {e}")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_pipeline()
# scripts/ingestion/minio_upload.py

import json
import boto3
from datetime import datetime
from scripts.config import MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, BRONZE_BUCKET

def get_minio_client():
    """إنشاء عميل MinIO"""
    return boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD
    )

def ensure_bucket():
    """إنشاء Bucket إذا لم يكن موجوداً"""
    s3 = get_minio_client()
    try:
        s3.create_bucket(Bucket=BRONZE_BUCKET)
        print(f"✅ Created bucket: {BRONZE_BUCKET}")
    except s3.exceptions.BucketAlreadyExists:
        pass
    return s3

def upload_jobs(source: str, jobs: list, date_str: str = None):
    """
    رفع الوظائف إلى Bronze bucket بهيكل:
    bronze/YYYY-MM-DD/source_YYYYMMDD.json
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    s3 = ensure_bucket()
    
    # إضافة metadata
    enriched = []
    for job in jobs:
        job['_metadata'] = {
            'ingested_at': datetime.now().isoformat(),
            'source': source,
            'date': date_str
        }
        enriched.append(job)
    
    # رفع إلى مجلد التاريخ
    folder = f"{date_str}/"
    filename = f"{source}_{date_str.replace('-', '')}.json"
    date_key = f"{folder}{filename}"
    
    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=date_key,
        Body=json.dumps(enriched, indent=2, ensure_ascii=False),
        ContentType='application/json'
    )
    print(f"📤 Uploaded to bronze/{date_key}")
    
    # تحديث latest
    latest_key = f"latest/{source}_latest.json"
    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=latest_key,
        Body=json.dumps(enriched, indent=2, ensure_ascii=False),
        ContentType='application/json'
    )
    print(f"🔄 Updated bronze/{latest_key}")
    
    return len(jobs)
