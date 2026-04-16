import pandas as pd
import pandas as pd
import numpy as np
import emoji
import re
from bs4 import BeautifulSoup
from ..common.logging_config import setup_logger
import json

logger = setup_logger("data_cleaner")

# ============================================================
#  Canonical Schema
# ============================================================
CANONICAL_COLUMNS = [
    "job_id",
    "job_title",
    "company_name",
    "job_description",
    "tags",
    "location",
    "salary_min",
    "salary_max",
    "posted_date",
    "expires_date",
    "contract_type",
    "currency",
    "remote",
    "job_url"
]


def clean_adzuna_data(jobs_data):
    """
    Cleans and standardizes raw data from the Adzuna API.
    
    Args:
        jobs_data (list or str): List of dictionaries (JSON data) or a path to the raw JSON file.
        
    Returns:
        pd.DataFrame: Cleaned DataFrame with standardized columns.
    """
    # Load the data if a file path is provided
    if isinstance(jobs_data, str):
        with open(jobs_data, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
            
    # If the data comes from our MinIO Bronze layer, it's wrapped in an envelope:
    # {"source": "adzuna", "data": [...]}
    if isinstance(jobs_data, dict) and "data" in jobs_data:
        jobs_data = jobs_data["data"]
            
    # Use pd.json_normalize to flatten nested JSON objects
    # (e.g., "company": {"display_name": "Company"} becomes "company.display_name")
    df = pd.json_normalize(jobs_data)
    
    # Column mapping dictionary: Original -> New Standard Name
    column_mapping = {
        'id': 'job_id',
        'title': 'job_title',
        'company.display_name': 'company_name',
        'description': 'job_description',
        'location.display_name': 'location', # Or just 'location' depending on how the API returns it
        'salary_min': 'salary_min',
        'salary_max': 'salary_max',
        'created': 'posted_date',
        'contract_type': 'contract_type',
        'redirect_url': 'job_url' # The URL in Adzuna is often called 'redirect_url'
    }
    
    # Handle the specific case for 'location' and 'URL' in case the API keys differ slightly
    if 'location' in df.columns and 'location.display_name' not in df.columns:
        column_mapping['location'] = 'location'
        
    if 'URL' in df.columns:
        column_mapping['URL'] = 'job_url'
        
    # Rename existing columns
    cols_to_rename = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=cols_to_rename)
    
    # Add a fixed column for the data source
    df['source_site'] = 'Adzuna'
    
    # Final list of recommended columns
    final_columns = [
        'job_id',
        'job_title',
        'company_name',
        'job_description',
        'tags',
        'location',
        'salary_min',
        'salary_max',
        'posted_date',
        'expires_date',
        'contract_type',
        'currency',
        'remote',
        'job_url',
        'source_site'
    ]
    
    # Keep only existing columns and add missing ones filled with None (NaN)
    for col in final_columns:
        if col not in df.columns:
            df[col] = None
            
    # Reorder and filter the columns
    df_cleaned = df[final_columns]
    
    # Suppression des doublons (extrêmement utile quand on aspire historiquement plusieurs jours sans filtre)
    df_cleaned = df_cleaned.drop_duplicates(subset=['job_id'], keep='first')
    
    # Réinitialisation propre de l'index
    df_cleaned = df_cleaned.reset_index(drop=True)
    
    return df_cleaned



# ============================================================
# Cleaning Utilities
# ============================================================

def deep_clean_text(text, preserve_case=False):
    """
    High-quality text cleaning without breaking technical terms (API, SQL, iOS)
    """
    if not text or pd.isna(text) or str(text).strip() == "":
        return np.nan

    try:
        # Remove HTML
        soup = BeautifulSoup(str(text), "html.parser")
        text = soup.get_text(separator=' ')
    except Exception:
        return np.nan

    # Remove emojis
    text = emoji.replace_emoji(text, replace='')

    # Keep technical symbols (#, +, -, ., /, @)
    text = re.sub(r'[^\w\s\.,#\+\-/@:]', '', text, flags=re.UNICODE)

    text = text.strip()

    # Normalize spaces (single pass only, no duplication)
    text = re.sub(r'\s+', ' ', text)

    return text


def clean_url(url):
    """Remove query parameters to avoid duplicates"""
    if not url or pd.isna(url):
        return np.nan
    return str(url).strip().split('?')[0]


def normalize_location(loc):
    """Basic location normalization without altering meaning"""
    if not loc or pd.isna(loc):
        return np.nan

    loc = str(loc).strip()
    loc = re.sub(r'\s+', ' ', loc)

    return loc


# ============================================================
# Transformer: Arbeitnow → Silver
# ============================================================

def  clean_arbeitnow_data(raw_jobs):

    if not raw_jobs:
        logger.warning("No raw data provided to cleaner.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    df = pd.DataFrame(raw_jobs).copy(deep=True)
    initial_count = len(df)

    # Column mapping
    column_mapping = {
        'slug': 'job_id',
        'title': 'job_title',
        'company_name': 'company_name',
        'description': 'job_description',
        'location': 'location',
        'url': 'job_url',
        'created_at': 'posted_date',
        'tags': 'tags',
        'remote': 'remote'
    }

    df = df.rename(columns=column_mapping)

    # =========================
    # Cleaning
    # =========================
    if 'job_description' in df.columns:
        df['job_description'] = df['job_description'].apply(
            lambda x: deep_clean_text(x, preserve_case=True)
        )

    if 'job_title' in df.columns:
        df['job_title'] = df['job_title'].apply(
            lambda x: deep_clean_text(x, preserve_case=True)
        )

    if 'job_url' in df.columns:
        df['job_url'] = df['job_url'].apply(clean_url)

    if 'location' in df.columns:
        df['location'] = df['location'].apply(normalize_location)

    if 'posted_date' in df.columns:
        df['posted_date'] = pd.to_datetime(
            df['posted_date'],
            unit='s',
            utc=True,
            errors='coerce'
        )

    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(
            lambda x: ", ".join([str(i).strip() for i in x if i])
            if isinstance(x, list) and len(x) > 0 else np.nan
        )

    # =========================
    # Remote normalization
    # =========================
    if 'remote' in df.columns:
        df['remote'] = df['remote'].fillna(False).astype(bool)

  

    # =========================
    # Schema alignment
    # =========================
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    final_df = df[CANONICAL_COLUMNS].copy()

    # =========================
    # Data quality checks
    # =========================
    final_df = final_df.dropna(subset=['job_id', 'job_title', 'job_url'])
    final_df = final_df.drop_duplicates(subset=['job_id'])
    final_df = final_df.drop_duplicates(subset=['job_url'])

    # Logging
    logger.info(f"Initial records: {initial_count}")
    logger.info(f"Final records: {len(final_df)}")
    logger.info(f"Dropped records: {initial_count - len(final_df)}")

    return final_df

if __name__ == "__main__":
    # Simple test
    print("Testing Adzuna cleaner with an empty DataFrame:")
    print(clean_adzuna_data([]))
