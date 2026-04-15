import requests
import os
from dotenv import load_dotenv
from dateutil import parser

# =========================
# ENV VARIABLES
# =========================
load_dotenv()
REED_API_KEY = os.getenv("REED_API_KEY")

def safe_parse_date(date_str):
    try:
        return parser.parse(date_str)
    except Exception:
        return None
    
def collect_reed():
    print("🚀 Reed ingestion")

    REED_API_KEY = os.getenv("REED_API_KEY")
    print(REED_API_KEY)
    url = "https://www.reed.co.uk/api/1.0/search"
    all_jobs = []

    for page in range(1, 6):
        params = {
            "resultsToTake": 50,
            "resultsToSkip": (page - 1) * 50
        }

        response = requests.get(
            url,
            params=params,
            auth=(REED_API_KEY, "")  # 👈 THIS is the key part
        )

        if response.status_code != 200:
            print("❌ Reed error:", response.text)
            break

        data = response.json().get("results", [])
        if not data:
            print('not data')
            break

        all_jobs.extend(data)

    return all_jobs

def filter_new_jobs(jobs, last_run):

    if not last_run:
        return jobs

    last_run_dt = parser.parse(last_run)

    new_jobs = []

    for job in jobs:
        job_date = job.get("datePosted") or job.get("date")

        if not job_date:
            continue

        job_dt = safe_parse_date(job_date)

        if job_dt and job_dt > last_run_dt:
            new_jobs.append(job)

    return new_jobs
# jobs = collect_reed()
# last_run = "2026-04-15T10:00:00"
# new_jobs = filter_new_jobs(jobs, last_run)
# print(jobs)
