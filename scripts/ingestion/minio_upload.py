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