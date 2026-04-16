import pandas as pd
import json

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

if __name__ == "__main__":
    # Simple test
    print("Testing Adzuna cleaner with an empty DataFrame:")
    print(clean_adzuna_data([]))
