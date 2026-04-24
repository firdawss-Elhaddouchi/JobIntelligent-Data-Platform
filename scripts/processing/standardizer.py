import pandas as pd
import numpy as np
import requests
import logging

# ============================================================
# 0. LOGGER SETUP
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger("StandardizationCore")

# ============================================================
# 1. CURRENCY & EXCHANGE RATE UTILITIES
# ============================================================

def fetch_rates_to_mad():
    """
    Fetches global exchange rates relative to USD and calculates conversion to MAD.
    """
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        rates = data['rates']
        mad_rate_to_usd = rates.get('MAD', 10.1) # Fallback to 10.1 if MAD is missing
        
        # Calculate conversion factor: (1 / Foreign_Rate_to_USD) * MAD_to_USD
        conversion_map = {curr: (1/rate) * mad_rate_to_usd for curr, rate in rates.items()}
        logger.info("Live exchange rates successfully fetched and mapped to MAD.")
        return conversion_map
    except Exception as e:
        logger.warning(f"Failed to fetch live rates: {e}. Using static fallbacks.")
        return {'GBP': 12.5, 'EUR': 10.8, 'USD': 10.1, 'MAD': 1.0}

# ============================================================
# 2. CORE STANDARDIZATION FUNCTIONS
# ============================================================

def standardize_salaries(df, source_name, rates_map):
    """
    Standardizes currency and converts salaries to MAD with strict Null Handling.
    """
    df = df.copy()
    
    if 'currency' in df.columns:
        # Step A: Standardize Nulls in Currency
        null_variants = ['UNKNOWN', 'none', 'None', 'null', 'nan', '', ' ']
        df['currency'] = df['currency'].replace(null_variants, np.nan)
        
        # Step B: Source-based Imputation
        if source_name.lower() == 'reed':
            df['currency'] = df['currency'].fillna('GBP')
        elif source_name.lower() in ['adzuna', 'arbeitnow']:
            df['currency'] = df['currency'].fillna('EUR')
        else:
            df['currency'] = df['currency'].fillna('MAD')

    def convert_row(row, col_name):
        val = pd.to_numeric(row[col_name], errors='coerce')
        if pd.isna(val): return np.nan
        
        curr = str(row.get('currency', 'MAD')).upper()
        rate = rates_map.get(curr)
        
        return round(val * rate, 2) if rate else np.nan

    for col in ['salary_min', 'salary_max']:
        if col in df.columns:
            df[f'{col}_mad'] = df.apply(lambda r: convert_row(r, col), axis=1)
            
    df['currency_standardized'] = df.apply(
        lambda r: 'MAD' if pd.notna(r['salary_min_mad']) else np.nan, axis=1
    )
    return df

def standardize_contract_types(df):
    """
    Maps varied contract labels into a unified canonical taxonomy.
    """
    df = df.copy()
    contract_map = {
        'permanent': 'Full-Time', 'full_time': 'Full-Time', 'full-time': 'Full-Time',
        'full time': 'Full-Time', 'cdi': 'Full-Time', 'indefinite': 'Full-Time',
        'part_time': 'Part-Time', 'part-time': 'Part-Time', 'part time': 'Part-Time',
        'contract': 'Contractor', 'freelance': 'Contractor', 'cdd': 'Contractor',
        'temporary': 'Contractor', 'temp': 'Contractor', 'zero-hours': 'Contractor',
        'intern': 'Internship', 'internship': 'Internship', 'stage': 'Internship',
        'apprentice': 'Internship', 'graduate': 'Internship'
    }

    if 'contract_type' in df.columns:
        df['contract_type_std'] = df['contract_type'].astype(str).str.lower().str.strip().str.replace('-', '_').str.replace(' ', '_')
        df['contract_type_std'] = df['contract_type_std'].map(contract_map).fillna('Undefined')
        df.loc[df['contract_type'].isna(), 'contract_type_std'] = 'Undefined'
    else:
        df['contract_type_std'] = 'Undefined'
        
    return df

def standardize_locations(df, source_name):
    """
    Standardizes location strings into 'City, Country' format.
    """
    df = df.copy()
    def parse_location(loc_str):
        clean_loc = str(loc_str).lower().strip()
        if pd.isna(loc_str) or clean_loc in ['nan', 'none', 'null', '', 'unknown']:
            return "Unknown", "Unknown"
        if 'remote' in clean_loc or 'anywhere' in clean_loc:
            return "Remote", "Remote"
            
        parts = [p.strip() for p in str(loc_str).split(',')]
        city = parts[0]
        countries = {'adzuna': 'France', 'reed': 'United Kingdom', 'arbeitnow': 'Germany'}
        country = countries.get(source_name.lower(), "Unknown")
        return city, country

    if 'location' in df.columns:
        temp_locs = df['location'].apply(parse_location)
        df['city_std'] = temp_locs.apply(lambda x: x[0])
        df['country_std'] = temp_locs.apply(lambda x: x[1])
        df['location_std'] = df['city_std'] + ", " + df['country_std']
    return df

def standardize_timestamps(df, source_name):
    """
    Standardizes multiple date columns to UTC datetime at Midnight.
    Works for both Unix timestamps and standard date strings.
    """
    df = df.copy()
    
    # Define which columns should be treated as dates
    date_columns = ['posted_date', 'expires_date']
    
    for col in date_columns:
        if col in df.columns:
            # 1. Try handling as Unix Timestamps (common in Arbeitnow)
            numeric_dates = pd.to_numeric(df[col], errors='coerce')
            
            # If the column is mostly numeric, treat it as Unix seconds
            if numeric_dates.notna().sum() > (len(df) * 0.5): 
                df[f'{col}_std'] = pd.to_datetime(numeric_dates, unit='s', utc=True, errors='coerce')
            else:
                # 2. Otherwise, treat as standard date strings
                df[f'{col}_std'] = pd.to_datetime(df[col], dayfirst=True, utc=True, errors='coerce')
            
            # 3. Data Sanitization: Filter unrealistic dates
            cutoff = pd.Timestamp('2010-01-01', tz='UTC')
            df.loc[df[f'{col}_std'] < cutoff, f'{col}_std'] = pd.NaT
            
            # 4. Transform: Floor to Day (The 00:00:00 logic)
            df[f'{col}_std'] = df[f'{col}_std'].dt.floor('D')
            
    return df

# def unify_job_ids(df, source_prefix):
#     """
#     Ensures global ID uniqueness by adding source namespaces.
#     """
#     df = df.copy()
#     if 'job_id' in df.columns:
#         df['job_id'] = source_prefix.lower() + "_" + df['job_id'].astype(str)
#     return df


# ============================================================
# 3. MASTER PROCESSING PIPELINE
# ============================================================

def standardize_data(raw_df, source_name, rates_map):
    """
    Runs the full standardization pipeline for a single source.
    """
    logger.info(f"Processing {source_name} to Silver Layer...")
    
    df = standardize_salaries(raw_df, source_name, rates_map)
    df = standardize_contract_types(df)
    df = standardize_locations(df, source_name)
    df = standardize_timestamps(df, source_name)
    # df = unify_job_ids(df, source_prefix)
    
    logger.info(f"Standardization complete for {source_name}. Total records: {len(df)}")
    return df

# # ============================================================
# # 4. EXECUTION
# # ============================================================

# # 1. Prepare Exchange Rates once
# global_rates = fetch_rates_to_mad()

# # 2. Process all sources
# adzuna_silver = process_to_silver(adzuna_clean, 'Adzuna',global_rates)
# reed_silver = process_to_silver(reed_clean, 'Reed', global_rates)
# arbeitnow_silver = process_to_silver(arbeitnow_clean, 'Arbeitnow', global_rates)

# # 3. Final Master Merge (The Silver Table)
# master_silver_df = pd.concat([adzuna_silver, reed_silver, arbeitnow_silver], ignore_index=True)

# logger.info(f"--- GLOBAL MASTER TABLE CREATED ---")
# logger.info(f"Total Combined Records: {len(master_silver_df)}")


