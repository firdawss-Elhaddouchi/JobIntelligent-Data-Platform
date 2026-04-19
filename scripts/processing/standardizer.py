# # ============================================================
# # Standardizer: Arbeitnow
# # ============================================================

# def standardize_arbeitnow_data(df):
    
#     return df


# # ============================================================
# # Standardizer: Adzuna
# # ============================================================

# def standardize_adzuna_data(df):
    
#     return df


# # ============================================================
# # Standardizer: Reed
# # ============================================================

# def standardize_reed_data(df):
   
#     return df


import pandas as pd
import numpy as np
import re

def normalize_company(name):
    if pd.isna(name):
        return np.nan

    name = str(name).lower().strip()

    # remove legal suffixes
    name = re.sub(r'\b(llc|ltd|inc|gmbh|sa|sarl|co\.?)\b', '', name)

    # normalize spaces
    name = re.sub(r'\s+', ' ', name)

    return name.title().strip()

def normalize_location_std(loc):
    if pd.isna(loc):
        return np.nan

    loc = str(loc).lower().strip()

    # unify separators
    loc = loc.replace("-", ",").replace("|", ",")

    # remove extra spaces
    loc = re.sub(r'\s+', ' ', loc)

    return loc.title().strip()

def normalize_tags(tags):
    if pd.isna(tags):
        return np.nan

    if isinstance(tags, list):
        tags = ",".join(tags)

    tags = str(tags).lower()
    tags = re.sub(r'\s+', ' ', tags)

    return tags.strip()


def normalize_remote(val):
    if pd.isna(val):
        return False

    if isinstance(val, str):
        return val.lower() in ["true", "1", "yes", "remote"]

    return bool(val)

def normalize_date(date):
    return pd.to_datetime(date, errors='coerce').strftime("%Y-%m-%d")

def standardize_job_data(df, source_name="unknown"):

    df = df.copy()

    # =========================
    # Company
    # =========================
    if 'company_name' in df.columns:
        df['company_name'] = df['company_name'].apply(normalize_company)

    # =========================
    # Location
    # =========================
    if 'location' in df.columns:
        df['location'] = df['location'].apply(normalize_location_std)

    # =========================
    # Tags
    # =========================
    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(normalize_tags)

    # =========================
    # Remote
    # =========================
    if 'remote' in df.columns:
        df['remote'] = df['remote'].apply(normalize_remote)

    # =========================
    # Dates
    # =========================
    if 'posted_date' in df.columns:
        df['posted_date'] = df['posted_date'].apply(normalize_date)

    # =========================
    # Source tracking (VERY IMPORTANT 🔥)
    # =========================
    df['source'] = source_name

    return df