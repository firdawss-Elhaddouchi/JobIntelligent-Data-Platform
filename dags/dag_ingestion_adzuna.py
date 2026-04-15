import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Ajouter automatiquement la racine du projet au PATH pour trouver le dossier 'scripts'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.ingestion.adzuna_client import fetch_jobs as fetch_adzuna
from scripts.ingestion.minio_upload import upload_jobs

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 4, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def run_adzuna_ingestion(**context):
    print("🚀 Démarrage de l'ingestion Adzuna depuis le DAG individuel...")
    # 1. On récupère les offres
    jobs = fetch_adzuna(max_pages=5)
    
    # 2. S'il y a des données, on les envoie vers MinIO
    if jobs:
        count = upload_jobs('adzuna', jobs)
        print(f"✅ Succès: {count} offres Adzuna sauvegardées dans MinIO.")
    else:
        print("⚠️ Aucune donnée Adzuna récupérée, rien à sauvegarder.")

with DAG(
    'dag_ingestion_adzuna_bronze',
    default_args=default_args,
    description="Aspiration dédiée uniquement à l'API Adzuna vers MinIO Bronze",
    schedule_interval='@daily',
    catchup=False,
    tags=['ingestion', 'adzuna', 'bronze', 'standalone']
) as dag:

    task_ingest_adzuna = PythonOperator(
        task_id='run_adzuna_ingestion',
        python_callable=run_adzuna_ingestion,
        doc_md="""
            ### Task Description
            Cette tâche appelle `fetch_jobs` du client Adzuna pour récupérer les offres "data"
            et utilise `upload_jobs` pour les stocker en format JSON brut dans MinIO.
        """
    )
    
    task_ingest_adzuna