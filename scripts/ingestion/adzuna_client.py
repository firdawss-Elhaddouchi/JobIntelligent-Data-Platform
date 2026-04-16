import requests
import os
import logging
import sys
import time
from dotenv import load_dotenv
from dateutil import parser
# from ..common.logging_config import setup_logger
import sys , os
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
                company = job.get("company", {})
                company_name = company.get("display_name") if isinstance(company, dict) else None
                
                location = job.get("location", {})
                location_name = location.get("display_name") if isinstance(location, dict) else job.get("location")

                formatted_job = {
                    "job_id": job.get("id"),
                    "job_title": job.get("title"),
                    "company_name": company_name,
                    "job_description": job.get("description"),
                    "tags": job.get("category", {}).get("label") if isinstance(job.get("category"), dict) else None,
                    "location": location_name,
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "posted_date": job.get("created"),
                    "expires_date": job.get("expires_date"),
                    "contract_type": job.get("contract_time") or job.get("contract_type"),
                    "currency": job.get("currency"),
                    "remote": job.get("remote"),
                    "job_url": job.get("redirect_url") or job.get("URL"),
                    "source_site": "Adzuna"
                }
                all_jobs.append(formatted_job)

            time.sleep(1) # Simple pacing

        except Exception as e:
            logger.exception(f"Error while fetching Adzuna data: {e}")
            break

    logger.info(f"Adzuna collected {len(all_jobs)} jobs")
    return all_jobs

def filter_new_jobs(jobs, last_run):
    if not last_run:
        return jobs

    last_run_dt = parser.parse(last_run)
    new_jobs = []

    for job in jobs:
        # The date is now stored in the 'posted_date' field after mapping
        job_date = job.get("posted_date")

        if not job_date:
            continue

        job_dt = safe_parse_date(job_date)

        if job_dt and job_dt > last_run_dt:
            new_jobs.append(job)

    logger.info(f"Adzuna filtered {len(new_jobs)} new jobs")
    return new_jobs