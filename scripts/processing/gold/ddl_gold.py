"""
Gold Layer Schema Creation
--------------------------
Creates a production-ready Gold schema (Star Schema).
"""

from sqlalchemy import create_engine, text

POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"

engine = create_engine(POSTGRES_URI)


def create_gold_schema():
    with engine.begin() as conn:

        # =========================
        # SCHEMA
        # =========================
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))

        # =========================
        # DIMENSION: LOCATION
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_location CASCADE"))

        conn.execute(text("""
        CREATE TABLE gold.dim_location (
            location_id SERIAL PRIMARY KEY,
            location TEXT,
            city TEXT,
            country TEXT,
            is_remote INT
        );
        """))

        # =========================
        # FACT TABLE: JOBS
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_fact CASCADE"))

        conn.execute(text("""
        CREATE TABLE gold.jobs_fact (
            job_id TEXT PRIMARY KEY,
            job_title TEXT,
            company_name TEXT,
            location_id INT REFERENCES gold.dim_location(location_id),
            salary_min FLOAT,
            salary_max FLOAT,
            salary_avg FLOAT,
            posted_date DATE,
            currency TEXT,
            is_remote BOOLEAN,
            job_url TEXT,
            source TEXT
        );
        """))

        # 👉 Indexes (IMPORTANT 🔥)
        conn.execute(text("CREATE INDEX idx_jobs_location ON gold.jobs_fact(location_id);"))
        conn.execute(text("CREATE INDEX idx_jobs_date ON gold.jobs_fact(posted_date);"))

        # =========================
        # AGG: JOBS PER LOCATION
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_per_location"))

        conn.execute(text("""
        CREATE TABLE gold.jobs_per_location (
            city TEXT,
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
        conn.execute(text("DROP TABLE IF EXISTS gold.salary_trends"))

        conn.execute(text("""
        CREATE TABLE gold.salary_trends (
            posted_date DATE,
            salary_avg FLOAT
        );
        """))

        # =========================
        # AGG: SKILLS DEMAND
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.skills_demand"))

        conn.execute(text("""
        CREATE TABLE gold.skills_demand (
            skill TEXT,
            count INT
        );
        """))

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

    print("✅ Gold schema created successfully")


if __name__ == "__main__":
    create_gold_schema()