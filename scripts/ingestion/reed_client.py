import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from ..common.logging_config import setup_logger

logger = setup_logger("reed_client")

# =========================
# ENV VARIABLES
# =========================
load_dotenv()
REED_API_KEY = os.getenv("REED_API_KEY")


# =========================
# SAFE DATE PARSER
# =========================
def safe_parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except Exception as e:
        logger.warning(f"Failed to parse date: {date_str} | error: {e}")
        return None


# =========================
# COLLECT REED DATA
# =========================
def collect_reed():
    logger.info(" Starting Reed ingestion")

    if not REED_API_KEY:
        logger.error("REED_API_KEY is missing in environment variables")
        raise ValueError("Missing REED_API_KEY")

    url = "https://www.reed.co.uk/api/1.0/search"
    all_jobs = []

    for page in range(1, 6):
        try:
            params = {
                "resultsToTake": 50,
                "resultsToSkip": (page - 1) * 50
            }

            response = requests.get(
                url,
                params=params,
                auth=(REED_API_KEY, ""),
                timeout=10  # 🔥 important
            )

            response.raise_for_status()  # raises HTTPError automatically

            try:
                data = response.json().get("results", [])
            except Exception as e:
                logger.error(f"Invalid JSON response on page {page}: {e}")
                break

            if not data:
                logger.info(f"No data on page {page}, stopping pagination")
                break

            all_jobs.extend(data)
            logger.info(f"Page {page} collected: {len(data)} jobs")

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on page {page}, retry later")
            continue

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on page {page}: {e}")
            break

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on page {page}: {e}")
            break

        except Exception as e:
            logger.exception(f"Unexpected error on page {page}: {e}")
            break

    logger.info(f"Total jobs collected: {len(all_jobs)}")
    return all_jobs


# =========================
# FILTER NEW JOBS
# =========================
def filter_new_jobs(jobs, last_run):

    if not last_run:
        return jobs

    new_jobs = []

    for job in jobs:
        try:
            job_date = job.get("datePosted") or job.get("date")

            if not job_date:
                continue

            job_dt = safe_parse_date(job_date)

            if job_dt and job_dt > last_run:
                new_jobs.append({
                    "jobId":job["jobId"],
                    "employerName":job["employerName"],
                    "jobTitle":job["jobTitle"],
                    "jobDescription":job["jobDescription"],
                    "locationName":job["locationName"],
                    "minimumSalary":job["minimumSalary"],
                    "maximumSalary":job["maximumSalary"],
                    "date":job["date"],
                    "expirationDate":job["expirationDate"],
                    "jobUrl":job["jobUrl"],
                    "currency":job["currency"],
                })

        except Exception as e:
            logger.warning(f"Skipping job due to error: {e}")
            continue

    logger.info(f"Filtered new jobs: {len(new_jobs)} / {len(jobs)}")
    return new_jobs