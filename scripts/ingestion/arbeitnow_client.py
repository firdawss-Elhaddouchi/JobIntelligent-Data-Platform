import time
import requests
from datetime import datetime, timezone
from ..common.logging_config import setup_logger


logger = setup_logger("arbeitnow_client")

# =========================
# 1️⃣ COLLECT DATA (RAW)
# =========================
def collect_arbeitnow(max_pages=5):
    """
    Fetches raw jobs from Arbeitnow without any date filtering.
    """
    logger.info("Arbeitnow ingestion started (Collecting Raw Data)")

    url = "https://www.arbeitnow.com/api/job-board-api"
    all_jobs = []

    for page in range(1, max_pages + 1):
        logger.info(f"Fetching Arbeitnow page {page}")
        
        try:
            r = requests.get(url, params={"page": page}, timeout=30)
            if r.status_code != 200:
                logger.error(f"Arbeitnow API error: {r.status_code}")
                break

            data = r.json().get("data", [])
            if not data:
                logger.info("No more data found, stopping pagination")
                break

            all_jobs.extend(data)
            time.sleep(0.5) # Avoid API pressure

        except Exception as e:
            logger.error(f"Error fetching Arbeitnow page {page}: {e}")
            break

    logger.info(f"Arbeitnow collected {len(all_jobs)} total jobs")
    return all_jobs

# =========================
# 2️⃣ FILTER DATA (LOGIC)
# =========================
def filter_new_jobs(jobs, last_run):
    """
    Filters a list of jobs based on the last_run timestamp.
    """
    if not last_run:
        logger.info("No last_run provided, returning all jobs")
        return jobs

    new_jobs = []
    
    # Ensure last_run is in UTC if it's a datetime object
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)

    for job in jobs:
        job_ts = job.get("created_at")
        if job_ts:
            # Arbeitnow uses Unix Timestamp
            job_dt = datetime.fromtimestamp(job_ts, tz=timezone.utc)

            if job_dt > last_run:
                new_jobs.append(job)

    logger.info(f"Arbeitnow filtered {len(new_jobs)} new jobs out of {len(jobs)}")
    return new_jobs