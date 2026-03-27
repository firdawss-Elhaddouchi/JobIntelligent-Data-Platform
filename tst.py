import requests
import json
import time
from datetime import datetime

APP_ID = "e5976890"
APP_KEY = "fc8991de718748b4e89045351ad63fd3"

COUNTRY = "gb"
SEARCH_KEYWORD = "data engineer"
RESULTS_PER_PAGE = 50
MAX_PAGES = 20
OUTPUT_FILE = "adzuna_bronze_jobs.json"

base_url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search"

all_jobs = []
page = 1

print("=== Début de la collecte Adzuna ===")

while page <= MAX_PAGES:
    print(f"Lecture de la page {page}...")

    url = f"{base_url}/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": SEARCH_KEYWORD,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type": "application/json"
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        print("Code HTTP :", response.status_code)

        if response.status_code != 200:
            print("Erreur API :", response.text)
            break

        data = response.json()
        jobs = data.get("results", [])

        if len(jobs) == 0:
            print("Plus de résultats.")
            break

        all_jobs.extend(jobs)
        print(f"Offres ajoutées : {len(jobs)} | Total : {len(all_jobs)}")

        page += 1
        time.sleep(1)

    except Exception as e:
        print("Erreur :", e)
        break

bronze_data = {
    "source": "Adzuna API",
    "country": COUNTRY,
    "search_keyword": SEARCH_KEYWORD,
    "collected_at": datetime.now().isoformat(),
    "total_jobs": len(all_jobs),
    "jobs": all_jobs
}

if all_jobs:
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(bronze_data, f, ensure_ascii=False, indent=4)

    print(f"Fichier JSON créé avec succès : {OUTPUT_FILE}")
else:
    print("Aucune offre récupérée, aucun fichier créé.")