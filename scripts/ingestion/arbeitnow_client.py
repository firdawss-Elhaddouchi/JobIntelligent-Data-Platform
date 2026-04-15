# scripts/ingestion/arbeitnow_client.py

import time
import requests
from datetime import datetime, timezone
from logging_config import setup_logger

logger = setup_logger("arbeitnow_client")


def collect_arbeitnow(last_run):
    logger.info("Arbeitnow ingestion started with incremental filtering")

    url = "https://www.arbeitnow.com/api/job-board-api"
    all_new_jobs = []
    page = 1
    stop_pagination = False

    while not stop_pagination:
        logger.info(f"Fetching Arbeitnow page {page}")
        
        try:
            r = requests.get(url, params={"page": page}, timeout=30)
            if r.status_code != 200:
                logger.error(f"Arbeitnow API error: {r.status_code}")
                break

            data = r.json().get("data", [])
            if not data:
                break

            for job in data:
                job_ts = job.get("created_at")
                if job_ts:
                    # Convert Unix Timestamp to Datetime object (UTC)
                    job_dt = datetime.fromtimestamp(job_ts, tz=timezone.utc)

                    # Filtering: If the date is older than the last operation, we stop.
                    if last_run and job_dt <= last_run:
                        stop_pagination = True
                        continue
                    
                    all_new_jobs.append(job)

            page += 1
            # To avoid putting pressure on the API
            time.sleep(0.5) 

        except Exception as e:
            logger.error(f"Error fetching Arbeitnow page {page}: {e}")
            break

    logger.info(f"Arbeitnow collected {len(all_new_jobs)} new jobs")
    return all_new_jobs