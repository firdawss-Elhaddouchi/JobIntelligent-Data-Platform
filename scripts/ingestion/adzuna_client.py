import requests
import os
import logging
import sys
import time
from dotenv import load_dotenv
from dateutil import parser

# =========================
# 1️⃣ LOGGER CONFIG
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("adzuna_client")

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

    for page in range(1, 6):
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

            all_jobs.extend(data)
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
        # In Adzuna, the date is stored in the 'created' field
        job_date = job.get("created")

        if not job_date:
            continue

        job_dt = safe_parse_date(job_date)

        if job_dt and job_dt > last_run_dt:
            new_jobs.append(job)

    logger.info(f"Adzuna filtered {len(new_jobs)} new jobs")
    return new_jobs

# if __name__ == "__main__":
#     logger.info("--- Testing Adzuna Client ---")
    
#     # Test 1: Collect jobs from the last day
#     logger.info("1. Collecting jobs (API parameter: max_days_old=1)...")
#     jobs = collect_adzuna(max_days_old=1)
#     logger.info(f"Total jobs collected: {len(jobs)}")
    
#     # Test 2: Apply the filter logic
#     # Set a date from a few days ago just to test the filter
#     from datetime import datetime, timedelta
#     last_run_date = (datetime.now() - timedelta(days=2)).isoformat() + "Z"
    
#     logger.info(f"2. Filtering jobs created strictly after: {last_run_date}...")
#     new_jobs = filter_new_jobs(jobs, last_run=last_run_date)
#     logger.info(f"New jobs after filtering: {len(new_jobs)}")
    
#     if new_jobs:
#         logger.info("Sample of the first job found:")
#         first_job = new_jobs[0]
#         logger.info(f" - Title: {first_job.get('title')}")
#         logger.info(f" - Company: {first_job.get('company', {}).get('display_name')}")
#         logger.info(f" - Date: {first_job.get('created')}")