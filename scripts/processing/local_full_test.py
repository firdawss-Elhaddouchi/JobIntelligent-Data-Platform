# how to run this script : python -m scripts.processing.local_full_test

import os
import json
import time
import sys
import pandas as pd

# 1. Setup Project Paths
project_root = os.path.abspath(os.getcwd())
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Ingestion Scripts
from scripts.ingestion.reed_client import collect_reed
from scripts.ingestion.adzuna_client import collect_adzuna
from scripts.ingestion.arbeitnow_client import collect_arbeitnow

# Import Cleaning and Standardization
from scripts.processing.cleaner import clean_adzuna_data, clean_arbeitnow_data, clean_reed_data
from scripts.processing.standardizer import standardize_data, fetch_rates_to_mad

# 2. Local Directory Configuration
BRONZE_LOCAL = os.path.join("test", "data", "bronze")
SILVER_LOCAL = os.path.join("test", "data", "silver")

def prepare_dirs(source):
    os.makedirs(os.path.join(BRONZE_LOCAL, source), exist_ok=True)
    os.makedirs(os.path.join(SILVER_LOCAL, source), exist_ok=True)

# 3. Master Execution Logic
def run_all_sources_test():
    print("🚀 Starting Global Local Test for ALL sources...")
    
    # Pre-fetch rates once
    rates_map = fetch_rates_to_mad()
    
    sources_config = {
        "reed": {"fetch_fn": collect_reed, "clean_fn": clean_reed_data},
        "adzuna": {"fetch_fn": collect_adzuna, "clean_fn": clean_adzuna_data},
        "arbeitnow": {"fetch_fn": collect_arbeitnow, "clean_fn": clean_arbeitnow_data}
    }

    for source, fns in sources_config.items():
        print(f"\n--- Processing Source: {source.upper()} ---")
        try:
            prepare_dirs(source)

            # Step A: Ingestion (API -> Bronze)
            print(f"📡 [1/3] Fetching {source} data...")
            raw_data = fns["fetch_fn"]()
            
            bronze_file = os.path.join(BRONZE_LOCAL, source, "data.json")
            with open(bronze_file, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=4)
            
            # Step B: Cleaning & Standardization
            print(f"🧹 [2/3] Cleaning and Standardizing...")
            
            input_data = raw_data
            if isinstance(raw_data, dict):
                if source == "arbeitnow":
                    input_data = raw_data.get("data", [])
                elif source in ["adzuna", "reed"]:
                    input_data = raw_data.get("results", [])

            df_cleaned = fns["clean_fn"](input_data)
            df_silver = standardize_data(df_cleaned, source, rates_map)

            # Step C: Saving locally
            print(f"💾 [3/3] Saving JSON file for manual inspection...")
            source_timestamp = int(time.time())
            output_dir = os.path.join(SILVER_LOCAL, source, f"cleaning_timestamp={source_timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, "data_silver.json")
            
            if not df_silver.empty:
                # 🔥 CRITICAL FIX: Use date_format='iso' to avoid numeric timestamps and Overflow errors
                df_silver.to_json(
                    output_file, 
                    orient="records", 
                    indent=4, 
                    force_ascii=False, 
                    date_format='iso' # This converts 17769... to "2026-04-24"
                )
                print(f"✅ Source {source} completed: {len(df_silver)} records.")
            else:
                print(f"⚠️ Warning: Source {source} returned 0 records after cleaning.")
                
        except Exception as e:
            print(f"❌ Error processing {source}: {str(e)}")

if __name__ == "__main__":
    run_all_sources_test()