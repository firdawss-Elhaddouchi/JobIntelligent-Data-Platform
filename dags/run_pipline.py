from airflow import DAG # type: ignore
from airflow.operators.python import PythonOperator # type: ignore
from datetime import datetime, timedelta
import sys
import os

# Ensure the 'scripts' directory is in the Python path for module discovery
# This allows Airflow to locate your custom ingestion and processing logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importing the core logic from your uploaded modules
from scripts.ingestion.upload_to_bronze_layer import run_pipeline as run_bronze
from scripts.processing.silver.upload_to_silver_layer import run_pipeline as run_silver
from scripts.processing.gold.run_gold_pipeline import run_gold_pipeline as run_gold

# ============================================================
# 1. DEFAULT ARGUMENTS
# ============================================================
# These settings apply to all tasks in the DAG
default_args = {
    'owner': 'ensah_data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 1),
    'email_on_failure': False,
    'execution_timeout': timedelta(hours=1),                        # Prevents running missed past intervals
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ============================================================
# 2. DAG DEFINITION
# ============================================================
with DAG(
    'job_market_medallion_pipeline',
    default_args=default_args,
    description='End-to-end Medallion architecture for job market data analysis',
    schedule_interval='0 23 * * *',  # Runs every day at 23:00 (11 PM)
    catchup=False,
    tags=['scraping', 'minio', 'medallion', 'parquet']
) as dag:

    # --- TASK 1: BRONZE LAYER (Ingestion) ---
    # Responsibility: Extract raw JSON data from external APIs (Adzuna, Reed, etc.)
    # and land it in MinIO without any modifications.
    ingest_to_bronze = PythonOperator(
        task_id='ingest_to_bronze',
        python_callable=run_bronze
    )

    # --- TASK 2: SILVER LAYER (Processing & Standardization) ---
    # Responsibility: 
    # 1. Load raw JSON from Bronze.
    # 2. Clean structure and handle missing values.
    # 3. Standardize currencies to MAD and dates to UTC.
    # 4. Save as Parquet for optimized storage and schema preservation.
    transform_to_silver = PythonOperator(
        task_id='transform_to_silver',
        python_callable=run_silver
    )

    # --- TASK 3: GOLD LAYER (Analytics & ML Features) ---
    # Responsibility:
    # 1. Perform Business Intelligence aggregations (Salary trends, Skills demand).
    # 2. Extract NLP features for downstream Machine Learning models.
    # 3. Create a final Jobs Fact table for dashboarding.
    generate_gold_tables = PythonOperator(
        task_id='generate_gold_tables',
        python_callable=run_gold
    )

    # ============================================================
    # 3. PIPELINE DEPENDENCIES
    # ============================================================
    # Sequential execution to ensure data consistency across layers
    ingest_to_bronze >> transform_to_silver >> generate_gold_tables