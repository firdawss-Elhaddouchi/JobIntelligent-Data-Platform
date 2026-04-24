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


def jobs_per_location(df):
    return (
        df.groupby("location")
        .size()
        .reset_index(name="job_count")
    )

def jobs_per_company(df):
    return (
        df.groupby("company")
        .size()
        .reset_index(name="job_count")
    )


def salary_trends(df):
    df = df.dropna(subset=["salary_min", "salary_max"])

    df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2

    return (
        df.groupby("date_posted")["salary_avg"]
        .mean()
        .reset_index()
    )


def skills_demand(df):
    skills = ["python", "sql", "aws", "spark", "docker"]
    results = []

    for skill in skills:
        count = df["description"].str.lower().str.contains(skill, na=False).sum()
        results.append({"skill": skill, "count": count})

    return pd.DataFrame(results)


def job_features(df):

    df_feat = df.copy()

    df_feat["python"] = df_feat["description"].str.contains("python", case=False, na=False).astype(int)
    df_feat["sql"] = df_feat["description"].str.contains("sql", case=False, na=False).astype(int)
    df_feat["aws"] = df_feat["description"].str.contains("aws", case=False, na=False).astype(int)

    df_feat["remote"] = df_feat["location"].str.contains("remote", case=False, na=False).astype(int)

    df_feat["salary_avg"] = (df_feat["salary_min"] + df_feat["salary_max"]) / 2

    return df_feat[[
        "job_id",
        "python",
        "sql",
        "aws",
        "remote",
        "salary_avg"
    ]]



def run_gold_pipeline():

    s3 = get_minio_client()
    timestamp = int(time.time())

    # 👉 Load latest Silver
    key = "reed/cleaning_timestamp=XXXX/data.json"
    df = read_silver_data(s3, key)

    # Build tables
    fact = build_jobs_fact(df)
    loc = jobs_per_location(df)
    comp = jobs_per_company(df)
    sal = salary_trends(df)
    skills = skills_demand(df)
    features = job_features(df)

    # Upload
    upload_gold(s3, fact, "jobs_fact", timestamp)
    upload_gold(s3, loc, "jobs_per_location", timestamp)
    upload_gold(s3, comp, "jobs_per_company", timestamp)
    upload_gold(s3, sal, "salary_trends", timestamp)
    upload_gold(s3, skills, "skills_demand", timestamp)
    upload_gold(s3, features, "job_features", timestamp)