
def build_jobs_fact(df):
    df = df.copy()

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return df[[
        "job_id",
        "title",
        "company",
        "location",
        "country",
        "date_posted",
        "salary_min",
        "salary_max",
        "salary_avg",
        "currency",
        "source"
    ]]


# ============================================================
# Transformer: Arbeitnow
# ============================================================

def transform_arbeitnow_data(df):
    
    return df


# ============================================================
# Transformer: Adzuna
# ============================================================

def transform_adzuna_data(df):
    
    return df


# ============================================================
# Transformer: Reed
# ============================================================

def transform_reed_data(df):
    
    return df
