from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Ajouter le dossier 'scripts' au path pour qu'Airflow puisse importer le client
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from scripts.ingestion.adzuna_client import collect_all_adzuna

# Configuration par défaut du DAG
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dag_ingestion_adzuna_bronze',
    default_args=default_args,
    description='Aspiration internationale Adzuna vers MinIO Bronze',
    schedule_interval='@daily',  # S'exécute chaque jour
    catchup=False,               # Ne pas rattraper les jours passés
    tags=['ingestion', 'adzuna', 'bronze']
) as dag:

    task_ingest_adzuna = PythonOperator(
        task_id='run_adzuna_ingestion',
        python_callable=collect_all_adzuna,
        doc_md="""
            ### Task Description
            Cette tâche appelle le script `adzuna_client.py` pour récupérer les offres
            de 20 pays différents et les stocker en format JSON brut dans MinIO.
        """
    )

    task_ingest_adzuna