"""
Gold Layer Schema Creation
--------------------------
Extended Star Schema with multiple dimensions:
- Location
- Date
- Company
- Contract Type
- Salary
"""

from sqlalchemy import create_engine, text

POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"
engine = create_engine(POSTGRES_URI)


def create_gold_schema():
    with engine.begin() as conn:

        # =========================
        # SCHEMA
        # =========================
        conn.execute(text("DROP SCHEMA IF EXISTS gold CASCADE;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))

        # =========================
        # DIM: LOCATION
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_location CASCADE"))
        conn.execute(text("""
        CREATE TABLE gold.dim_location (
            location_id SERIAL PRIMARY KEY,
            location TEXT,
            city TEXT,
            country TEXT
            
        );
        """))

        # =========================
        # DIM: DATE
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_date CASCADE"))
        conn.execute(text("""
        CREATE TABLE gold.dim_date (
            date_id SERIAL PRIMARY KEY,
            date DATE UNIQUE,
            day INT,
            month INT,
            month_name TEXT,
            quarter INT,
            year INT,
            day_of_week TEXT
        );
        """))

        # =========================
        # DIM: COMPANY
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_company CASCADE"))
        conn.execute(text("""
        CREATE TABLE gold.dim_company (
            company_id SERIAL PRIMARY KEY,
            company_name TEXT UNIQUE
        );
        """))

        # =========================
        # DIM: CONTRACT TYPE
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_contract_type CASCADE"))
        conn.execute(text("""
        CREATE TABLE gold.dim_contract_type (
            contract_type_id SERIAL PRIMARY KEY,
            contract_type TEXT UNIQUE
        );
        """))

        # =========================
        # FACT TABLE: JOBS
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.fact_jobs CASCADE"))
        conn.execute(text("""
        CREATE TABLE gold.fact_jobs (
            job_id TEXT PRIMARY KEY,
            job_title TEXT,
            job_description TEXT,
            tags TEXT,
            company_id INT REFERENCES gold.dim_company(company_id),
            location_id INT REFERENCES gold.dim_location(location_id),
            posted_date_id INT REFERENCES gold.dim_date(date_id),
            expires_date_id INT REFERENCES gold.dim_date(date_id),
            contract_type_id INT REFERENCES gold.dim_contract_type(contract_type_id),
            salary_min FLOAT,
            salary_max FLOAT,
            salary_avg FLOAT,
            currency TEXT,
            is_remote INT,
            job_url TEXT,
            source TEXT
           
        );
        """))

        # =========================
        # INDEXES
        # =========================
        conn.execute(text("CREATE INDEX idx_jobs_location ON gold.fact_jobs(location_id);"))
        conn.execute(text("CREATE INDEX idx_jobs_posted_date ON gold.fact_jobs(posted_date_id);"))
        conn.execute(text("CREATE INDEX idx_jobs_expires_date ON gold.fact_jobs(expires_date_id);"))
        conn.execute(text("CREATE INDEX idx_jobs_company ON gold.fact_jobs(company_id);"))

        # =========================
        # AGG: JOBS PER LOCATION
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_per_location"))
        conn.execute(text("""
        CREATE TABLE gold.jobs_per_country (
            country TEXT,
            job_count INT
        );
        """))

        # =========================
        # AGG: JOBS PER COMPANY
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_per_company"))
        conn.execute(text("""
        CREATE TABLE gold.jobs_per_company (
            company_name TEXT,
            job_count INT
        );
        """))

        # =========================
        # AGG: SALARY TRENDS
        # =========================
        # conn.execute(text("DROP TABLE IF EXISTS gold.salary_trends"))
        # conn.execute(text("""
        # CREATE TABLE gold.salary_trends (
        #     full_date DATE,
        #     salary_avg FLOAT
        # );
        # """))

        # =========================
        # AGG: SKILLS DEMAND
        # =========================
        # conn.execute(text("DROP TABLE IF EXISTS gold.skills_demand"))
        # conn.execute(text("""
        # CREATE TABLE gold.skills_demand (
        #     skill TEXT,
        #     count INT
        # );
        # """))

        # =========================
        # FEATURE TABLE (ML)
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.job_features"))
        conn.execute(text("""
        CREATE TABLE gold.job_features (
            job_id TEXT PRIMARY KEY,
            python INT,
            sql INT,
            aws INT,
            remote INT,
            salary_avg FLOAT
        );
        """))

    print("✅ Extended Gold schema created successfully")


if __name__ == "__main__":
    create_gold_schema()