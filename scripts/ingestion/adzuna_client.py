import requests
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

COUNTRY = "gb"
SEARCH_KEYWORD = "data engineer"
RESULTS_PER_PAGE = 50
MAX_PAGES = 5

def collect_adzuna_jobs():
    if not APP_ID or not APP_KEY:
        print("Erreur: ADZUNA_APP_ID ou ADZUNA_APP_KEY non défini dans .env")
        return

    # Chemin de sauvegarde dans data/bronze/
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "bronze")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"adzuna_{date_str}.json")

    base_url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search"
    
    all_jobs = []
    page = 1
    
    print("=== Début de la collecte Adzuna ===")
    
    while page <= MAX_PAGES:
        print(f"Lecture de la page {page}...")
        
        url = f"{base_url}/{page}"
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "app_id": APP_ID,
            "app_key": APP_KEY,
            "what": SEARCH_KEYWORD,
            "results_per_page": RESULTS_PER_PAGE
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
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
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(bronze_data, f, ensure_ascii=False, indent=4)
            
        print(f"Fichier JSON créé avec succès : {output_file}")
    else:
        print("Aucune offre récupérée, aucun fichier créé.")

if __name__ == "__main__":
    collect_adzuna_jobs()
