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