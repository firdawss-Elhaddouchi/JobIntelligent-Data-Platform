import pandas as pd
import numpy as np
import emoji
import re
from bs4 import BeautifulSoup
import sys , os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from scripts.common.logging_config import setup_logger
import os
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


# ============================================================
# Cleaning Utilities
# ============================================================

def deep_clean_text(text,preserve_case=False):
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




# ============================================================
# Transformer: Adzuna → Silver
# ============================================================

def clean_adzuna_data(jobs_data):
    """
    Cleans and standardizes raw data from the Adzuna API.

    Args:
        jobs_data (list, dict, or str): Raw job records (list of dicts),
            a Bronze-layer envelope {"source": "adzuna", "data": [...]},
            or a path to the raw JSON file.

    Returns:
        pd.DataFrame: Cleaned DataFrame aligned to CANONICAL_COLUMNS.
    """
    # --- Load from file if path is given ---
    if isinstance(jobs_data, str):
        with open(jobs_data, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)

    # --- Unwrap Bronze envelope ---
    if isinstance(jobs_data, dict) and "data" in jobs_data:
        jobs_data = jobs_data["data"]

    if not jobs_data:
        logger.warning("No raw Adzuna data provided to cleaner.")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    # Flatten nested JSON (company.display_name, location.display_name, …)
    df = pd.json_normalize(jobs_data).copy(deep=True)
    initial_count = len(df)

    # =========================
    # Column mapping
    # =========================
    column_mapping = {
        'id': 'job_id',
        'title': 'job_title',
        'company.display_name': 'company_name',
        'description': 'job_description',
        'location.display_name': 'location',
        'salary_min': 'salary_min',
        'salary_max': 'salary_max',
        'created': 'posted_date',
        'contract_type': 'contract_type',
        'redirect_url': 'job_url',
        'category.label': 'tags',
    }

    # Fallbacks for alternative key names
    if 'location' in df.columns and 'location.display_name' not in df.columns:
        column_mapping['location'] = 'location'
    if 'URL' in df.columns:
        column_mapping['URL'] = 'job_url'

    cols_to_rename = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=cols_to_rename)

    # =========================
    # Cleaning (same helpers as arbeitnow)
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

    # Adzuna dates are ISO-8601 strings (e.g. "2026-04-14T12:00:00Z")
    if 'posted_date' in df.columns:
        df['posted_date'] = pd.to_datetime(
            df['posted_date'],
            utc=True,
            errors='coerce'
        )

    # Tags: category.label is a single string in Adzuna, keep as-is
    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(
            lambda x: deep_clean_text(x, preserve_case=True)
            if isinstance(x, str) else np.nan
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
    logger.info(f"[Adzuna] Initial records: {initial_count}")
    logger.info(f"[Adzuna] Final records: {len(final_df)}")
    logger.info(f"[Adzuna] Dropped records: {initial_count - len(final_df)}")

    return final_df


# ============================================================
# Transformer: Reed → Silver
# ============================================================
def clean_reed_data(jobs_data):
    """
    Clean and transform raw job data from the Reed API into the canonical schema.

    This function:
    - Accepts raw data in multiple formats (list, dict, file path)
    - Normalizes nested JSON structure
    - Cleans text, salary, currency, and dates
    - Aligns output to CANONICAL_COLUMNS
    - Applies data quality checks (null filtering, deduplication)

    Args:
        jobs_data (list | dict | str):
            - List of job dictionaries
            - Bronze format: {"source": "reed", "data": [...]}
            - File path to JSON file

    Returns:
        pd.DataFrame:
            Cleaned dataset aligned with CANONICAL_COLUMNS
    """
    try:
        logger.info("[Reed] Starting cleaning process")

        # =========================
        # Load data
        # =========================
        if isinstance(jobs_data, str):
            logger.info("[Reed] Loading data from file path")
            with open(jobs_data, 'r', encoding='utf-8') as f:
                jobs_data = json.load(f)

        # Unwrap Bronze layer
        if isinstance(jobs_data, dict) and "data" in jobs_data:
            logger.info("[Reed] Detected Bronze format, extracting 'data' field")
            jobs_data = jobs_data["data"]

        if not jobs_data:
            logger.warning("[Reed] No raw data provided")
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        # =========================
        # Create DataFrame
        # =========================
        df = pd.json_normalize(jobs_data).copy(deep=True)
        initial_count = len(df)

        logger.info(f"[Reed] Loaded {initial_count} raw records")

        # =========================
        # Column mapping
        # =========================
        column_mapping = {
            "jobId": "job_id",
            "jobTitle": "job_title",
            "employerName": "company_name",
            "jobDescription": "job_description",
            "locationName": "location",
            "minimumSalary": "salary_min",
            "maximumSalary": "salary_max",
            "date": "posted_date",
            "expirationDate": "expires_date",
            "jobUrl": "job_url",
            "currency": "currency"
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        logger.info("[Reed] Column mapping applied")

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

        logger.info("[Reed] Text, URL, and location cleaned")

        # =========================
        # Company cleaning
        # =========================
        if 'company_name' in df.columns:
            df['company_name'] = (
                df['company_name']
                .fillna("Unknown")
                .astype(str)
                .str.encode("latin1", errors="ignore").str.decode("utf-8", errors="ignore")
                .str.strip()
                .str.replace(r"\b(Ltd|Limited|PLC|Inc|LLC)\b", "", regex=True)
                .str.replace(r"[^\w\s]", "", regex=True)
                .str.title()
            )

        logger.info("[Reed] Company names normalized")

        # =========================
        # Salary cleaning
        # =========================
        for col in ['salary_min', 'salary_max']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df.loc[df[col] < 0, col] = np.nan

        logger.info("[Reed] Salary fields cleaned")

        # =========================
        # Currency cleaning
        # =========================
        if 'currency' in df.columns:
            df['currency'] = (
                df['currency']
                .fillna("UNKNOWN")
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({
                    "£": "GBP",
                    "$": "USD",
                    "€": "EUR"
                })
            )

        logger.info("[Reed] Currency normalized")

        # =========================
        # Date parsing
        # =========================
        if 'posted_date' in df.columns:
            df['posted_date'] = pd.to_datetime(
                df['posted_date'],
                format="%Y-%m-%d",
                errors="coerce",
                utc=True
            )

        if 'expires_date' in df.columns:
            df['expires_date'] = pd.to_datetime(
                df['expires_date'],
                format="%Y-%m-%d",
                errors="coerce",
                utc=True
            )

        logger.info("[Reed] Dates parsed")

        # =========================
        # Defaults
        # =========================
        # df['tags'] = np.nan
        # df['remote'] = False

        # =========================
        # Schema alignment
        # =========================
        final_df = df.reindex(columns=CANONICAL_COLUMNS)

        # =========================
        # Data quality checks
        # =========================

        final_df = final_df.dropna(subset=['job_id', 'job_title', 'job_url'])
        final_df = final_df.drop_duplicates(subset=['job_id'])
        final_df = final_df.drop_duplicates(subset=['job_url'])

        after_clean = len(final_df)
        print('###############################################')
        print('###############################################')
        print('###############################################')
        print('###############################################')
        print(f" columns : {final_df.columns}")
        print('###############################################')
        print('###############################################')
        print('###############################################')
        print('###############################################')
        # =========================
        # Logging summary
        # =========================
        logger.info(f"[Reed] Initial records: {initial_count}")
        logger.info(f"[Reed] After cleaning: {after_clean}")
        logger.info(f"[Reed] Dropped records: {initial_count - after_clean}")

        logger.info("[Reed] Cleaning process completed successfully")

        return final_df
    except Exception as e:
        logger.error(f"[Reed] Error during cleaning: {str(e)}")
        raise


# if __name__ == "__main__":
    
#     # ============================================================
#     # Simple exemple -> cleaning arbeitnow
#     # ============================================================
#     BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#     TEST_DIR = os.path.join(BASE_DIR, "test")
#     os.makedirs(TEST_DIR, exist_ok=True)

#     # Example file (you can change this)
#     input_file = os.path.join(TEST_DIR, "arbeitnow_data_only_1776341238.json")
#     print("Loading file:", input_file)

#     with open(input_file, "r", encoding="utf-8") as f:
#         data = json.load(f)
#     jobs = data if isinstance(data, list) else data.get("data", [])

#     df = clean_arbeitnow_data(jobs)
#     print("Cleaned shape:", df.shape)

#     output_file = os.path.join(TEST_DIR, "arbeitnow_cleaned.json")
#     df.to_json(output_file, orient="records", force_ascii=False, indent=2)
#     print("Saved cleaned file to:", output_file)
