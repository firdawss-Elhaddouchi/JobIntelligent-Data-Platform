import boto3
from sqlalchemy import create_engine
import os
from botocore.exceptions import ClientError

from scripts.common.logging_config import setup_logger

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

SILVER_BUCKET = "silver"
POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"

logger = setup_logger("utilies")
# =========================
# CLIENTS
# =========================

def get_minio_client():
    """
    Create and return a MinIO (S3-compatible) client.

    Returns:
        boto3.client: Configured S3 client for MinIO.
    """
    logger.info("Initializing MinIO client")
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )


def get_postgres_engine():
    """
    Create and return a SQLAlchemy engine for PostgreSQL.

    Returns:
        Engine: SQLAlchemy engine connected to PostgreSQL.
    """
    logger.info("Initializing PostgreSQL engine")
    return create_engine(POSTGRES_URI)

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
