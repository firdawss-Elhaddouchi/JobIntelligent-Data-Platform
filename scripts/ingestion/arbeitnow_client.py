import time
import requests
import json
from datetime import datetime, timezone
import sys , os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.common.logging_config import setup_logger


logger = setup_logger("arbeitnow_client")

# =========================
# 0️⃣ Keywords for the Specialization
# =========================
DATA_KEYWORDS = [
"data", "données", "analyst", "engineer", "science",
"machine learning", "ai", "intelligence artificialielle",
"bi", "business intelligence", "big data", "etl", "python"
]

def is_data_job(job):
    """
        Check if the job is data-related based on the title or tags.
    """
    title = job.get("title", "").lower()
    # Merge tags into a single text for searching within it
    tags = " ".join(job.get("tags", [])).lower()
    
    # If you find any keyword in the title or tags, we consider it a data function
    return any(keyword in title or keyword in tags for keyword in DATA_KEYWORDS)
# =========================
# 1️⃣ COLLECT DATA (RAW)
# =========================
def collect_arbeitnow(max_pages=10):
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

            data_jobs = [job for job in data if is_data_job(job)]
            all_jobs.extend(data_jobs)
            logger.info(f" Page {page}: Found {len(data_jobs)} data-related jobs out of {len(data)}")
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


# =========================
# 3️⃣ TEST BLOCK (Main Execution)
# =========================
if __name__ == "__main__":
    # Quick test to save results in the test folder
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

    test_dir = os.path.join(project_root, "test")

    if not os.path.exists(test_dir): os.makedirs(test_dir)

    try:

        # Pull down the first 3 pages to see how many data functions we find

        data_results = collect_arbeitnow(max_pages=200)

        file_path = os.path.join(test_dir, f"arbeitnow_data_only_{int(time.time())}.json")

        with open(file_path, 'w', encoding='utf-8') as f:

            json.dump(data_results, f, ensure_ascii=False, indent=4) 


        logger.info(f" Saved {len(data_results)} filtered jobs to {file_path}") 
    except Exception as e: 
        logger.error(f" Test failed: {e}")