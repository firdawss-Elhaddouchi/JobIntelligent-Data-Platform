# dags/dag_daily_ingestion.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# استيراد من scripts (Airflow يضيف /opt/airflow للـ PYTHONPATH)
import sys
sys.path.insert(0, '/opt/airflow')

from scripts.ingestion.adzuna_client import fetch_jobs as fetch_adzuna
from scripts.ingestion.reed_client import fetch_jobs as fetch_reed
from scripts.ingestion.arbeitnow_client import fetch_jobs as fetch_arbeitnow
from scripts.ingestion.minio_upload import upload_jobs

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def task_adzuna(**context):
    """مهمة Adzuna"""
    jobs = fetch_adzuna(max_pages=5)
    count = upload_jobs('adzuna', jobs)
    context['task_instance'].xcom_push(key='count', value=count)
    return f"Adzuna: {count} jobs"

def task_reed(**context):
    """مهمة Reed"""
    jobs = fetch_reed(max_iterations=5)
    count = upload_jobs('reed', jobs)
    context['task_instance'].xcom_push(key='count', value=count)
    return f"Reed: {count} jobs"

def task_arbeitnow(**context):
    """مهمة Arbeitnow"""
    jobs = fetch_arbeitnow(max_pages=5)
    count = upload_jobs('arbeitnow', jobs)
    context['task_instance'].xcom_push(key='count', value=count)
    return f"Arbeitnow: {count} jobs"

def task_notify(**context):
    """مهمة الإشعار"""
    ti = context['task_instance']
    
    sources = ['adzuna', 'reed', 'arbeitnow']
    total = 0
    
    print("📊 Daily Ingestion Summary:")
    for src in sources:
        count = ti.xcom_pull(task_ids=f'fetch_{src}', key='count') or 0
        total += count
        print(f"   {src.capitalize()}: {count} jobs")
    
    print(f"   Total: {total} jobs")
    return f"Total ingested: {total}"

with DAG(
    'daily_ingestion',
    default_args=default_args,
    description='Daily job ingestion from multiple sources',
    schedule_interval='0 2 * * *',  # 2:00 AM daily
    catchup=False,
    tags=['ingestion', 'bronze', 'daily'],
) as dag:
    
    # المهام
    t1 = PythonOperator(task_id='fetch_adzuna', python_callable=task_adzuna)
    t2 = PythonOperator(task_id='fetch_reed', python_callable=task_reed)
    t3 = PythonOperator(task_id='fetch_arbeitnow', python_callable=task_arbeitnow)
    t4 = PythonOperator(task_id='notify', python_callable=task_notify, trigger_rule='all_done')
    
    # التدفق
    [t1, t2, t3] >> t4