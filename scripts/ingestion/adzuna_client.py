import requests
import os
import logging
import sys
import time
from dotenv import load_dotenv
from dateutil import parser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.common.logging_config import setup_logger

# =========================
# 1️⃣ LOGGER CONFIG
# =========================
logger = setup_logger("adzuna_client")

# =========================
# 2️⃣ ENV VARIABLES
# =========================
load_dotenv()
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

def safe_parse_date(date_str):
    try:
        return parser.parse(date_str)
    except Exception as e:
        logger.debug(f"Failed to parse date: {date_str} - {e}")
        return None

def collect_adzuna(max_days_old=None):
    logger.info("Adzuna ingestion started")
    
    url = "https://api.adzuna.com/v1/api/jobs/fr/search/"
    all_jobs = []

    # MAX POUR L'ENTRAINEMENT (10 000+ jobs potentiels si disponibles)
    for page in range(1, 201):
        params = {
            'app_id': ADZUNA_APP_ID,
            'app_key': ADZUNA_APP_KEY,
            'what': 'data',
            'where': 'France',
            'results_per_page': 50
        }
        
        # If you want to filter directly via the API
        if max_days_old is not None:
            params['max_days_old'] = max_days_old

        logger.info(f"Fetching Adzuna page {page}")

        try:
            response = requests.get(f"{url}{page}", params=params)

            if response.status_code != 200:
                logger.error(f"Adzuna API error: {response.text}")
                break

            data = response.json().get("results", [])
            if not data:
                logger.info("No data found, stopping pagination")
                break

            for job in data:
                # 1. On garde UNIQUEMENT les colonnes dont on a besoin
                # 2. On garde les NOMS ORIGINAUX (id, title, etc) pour le cleaner
                # 3. On ne crée pas de colonnes de valeurs nulles
                
                keys_to_keep = [
                    "id", "title", "description", "salary_min", "salary_max",
                    "created", "contract_time", "contract_type", "redirect_url"
                    # "URL"    → Adzuna utilise redirect_url, pas URL (jamais retourné)
                    # "remote" → Non retourné par l'API Adzuna (cleaner gère le défaut False)
                ]

                bronze_job = {}
                
                # Récupération des clés simples
                for key in keys_to_keep:
                    if key in job:
                        bronze_job[key] = job[key]

                # Récupération des dictionnaires (que cleaner.py va aplatir)
                if "company" in job:
                    bronze_job["company"] = job["company"]
                if "location" in job:
                    bronze_job["location"] = job["location"]
                if "category" in job:
                    bronze_job["category"] = job["category"]

                all_jobs.append(bronze_job)

            time.sleep(1) # Simple pacing

        except Exception as e:
            logger.exception(f"Error while fetching Adzuna data: {e}")
            break

    logger.info(f"Adzuna collected {len(all_jobs)} jobs")
    return all_jobs

def filter_new_jobs(jobs, last_run):
    if not last_run:
        return jobs

    import datetime
    if isinstance(last_run, str):
        last_run_dt = parser.parse(last_run)
    else:
        last_run_dt = last_run
        
    if last_run_dt.tzinfo is None:
        last_run_dt = last_run_dt.replace(tzinfo=datetime.timezone.utc)
        
    new_jobs = []

    for job in jobs:
        # In the raw filtered data, the creation date is still 'created'
        job_date = job.get("created")

        if not job_date:
            continue

        job_dt = safe_parse_date(job_date)

        if job_dt:
            if job_dt.tzinfo is None:
                job_dt = job_dt.replace(tzinfo=datetime.timezone.utc)
            if job_dt > last_run_dt:
                new_jobs.append(job)

    logger.info(f"Adzuna filtered {len(new_jobs)} new jobs")
    return new_jobs