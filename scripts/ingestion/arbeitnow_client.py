# scripts/ingestion/arbeitnow_client.py

import requests

def fetch_jobs(max_pages: int = 5):
    """Fetching functions from the Arbeitnow API (open)"""
    print("🚀 Fetching Arbeitnow jobs...")
    
    all_jobs = []
    
    for page in range(1, max_pages + 1):
        url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get('data', [])
            if not jobs:
                break
                
            all_jobs.extend(jobs)
            print(f"  Page {page}: {len(jobs)} jobs")
            
        except Exception as e:
            print(f"  ❌ Error page {page}: {e}")
            break
    
    print(f"✅ Total Arbeitnow: {len(all_jobs)} jobs")
    return all_jobs