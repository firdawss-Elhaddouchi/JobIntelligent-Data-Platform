# scripts/ingestion/reed_client.py

import requests
from requests.auth import HTTPBasicAuth
from scripts.config import REED_API_KEY

def fetch_jobs(max_iterations: int = 5):
    """Fetching functions from The Reed API"""
    print("🚀 Fetching Reed jobs...")
    
    all_jobs = []
    skip = 0
    take = 100
    
    for i in range(max_iterations):
        url = f"https://www.reed.co.uk/api/1.0/search?keywords=data&location=london&skip={skip}&take={take}"
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(REED_API_KEY, ''),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get('results', [])
            if not jobs:
                break
                
            all_jobs.extend(jobs)
            skip += take
            print(f"  Batch {i+1}: {len(jobs)} jobs")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            break
    
    print(f"✅ Total Reed: {len(all_jobs)} jobs")
    return all_jobs
