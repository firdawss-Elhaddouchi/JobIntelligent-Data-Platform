import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Automatically add the project root to the PATH to locate the 'scripts' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# New imports from our simplified adzuna_client
from scripts.ingestion.adzuna_client import collect_adzuna, filter_new_jobs
from scripts.ingestion.minio_upload import upload_jobs

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 4, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def run_adzuna_ingestion(**context):
    print("🚀 Starting incremental Adzuna data ingestion...")
    
    # 1. Retrieve the last run date managed by Airflow (data_interval_start)
    # The argument is automatically passed via **context in Airflow
    data_interval_start = context.get('data_interval_start')
    
    # Convert to ISO format to be used in our filter_new_jobs function
    last_run_str = data_interval_start.isoformat() if data_interval_start else None
    print(f"ℹ️ DAG considers last_run = {last_run_str}")
    
    # 2. Use the max_days_old parameter to avoid overloading the API.
    # For a @daily interval, taking the last 2 days provides a safety margin.
    jobs = collect_adzuna(max_days_old=2)
    
    # 3. Precise filtering to remove duplicates posted on the same day
    new_jobs = filter_new_jobs(jobs, last_run=last_run_str)
    
    # 4. If there are NEW records, upload them to MinIO
    if new_jobs:
        count = upload_jobs('adzuna', new_jobs)
        print(f"✅ Success: {count} NEW Adzuna jobs saved to MinIO.")
    else:
        print("⚠️ No new Adzuna data collected today, nothing to save.")

with DAG(
    'dag_ingestion_adzuna_bronze',
    default_args=default_args,
    description="Dedicated ingestion from Adzuna API to MinIO Bronze",
    schedule_interval='@daily',
    catchup=False,
    tags=['ingestion', 'adzuna', 'bronze', 'standalone']
) as dag:

    task_ingest_adzuna = PythonOperator(
        task_id='run_adzuna_ingestion',
        python_callable=run_adzuna_ingestion,
        doc_md="""
            ### Task Description
            This task calls `collect_adzuna` (only for the last 2 days), 
            then strictly filters the jobs with `filter_new_jobs` using Airflow's 
            `data_interval_start`, and stores only the new records in MinIO Bronze.
        """
    )
    
    task_ingest_adzuna