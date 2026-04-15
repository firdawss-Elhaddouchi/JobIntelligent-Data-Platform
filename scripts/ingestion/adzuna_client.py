import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

def fetch_jobs(max_pages: int = 5):
    """ Fetching data jobs from the Adzuna API and saving to data/bronze """
    print("🚀 Fetching Adzuna data jobs...")
    
    if not APP_ID or not APP_KEY:
        print("❌ Error: ADZUNA_APP_ID or ADZUNA_APP_KEY is missing from the environment. Please check your .env file.")
        return []

    all_jobs = []
    
    for page in range(1, max_pages + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/fr/search/{page}"
        params = {
            'app_id': APP_ID,
            'app_key': APP_KEY,
            'what': 'data',
            'where': 'France',
            'results_per_page': 50
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get('results', [])
            if not jobs:
                break
                
            all_jobs.extend(jobs)
            print(f"  Page {page}: {len(jobs)} jobs")
            
        except Exception as e:
            print(f"  ❌ Error on page {page}: {e}")
            break
    
    print(f"✅ Total Adzuna data jobs fetched: {len(all_jobs)}")
    
    if all_jobs:
        # Save path in data/bronze/
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "bronze")
        os.makedirs(output_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"adzuna_jobs_{date_str}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=4)
            
        print(f"💾 Data successfully saved to: {output_file}")
    else:
        print("⚠️ No data to save.")
        
    return all_jobs

if __name__ == "__main__":
    fetch_jobs()