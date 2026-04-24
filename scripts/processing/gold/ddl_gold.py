"""
Gold Layer Schema Creation
--------------------------

This script initializes the **Gold layer** of the data warehouse in PostgreSQL.

The Gold layer represents **business-level, analytics-ready data**, structured
using a dimensional model (fact + dimensions + aggregated tables).

Main responsibilities:
- Create the `gold` schema if it does not exist
- Recreate dimension and fact tables
- Create aggregated analytics tables for reporting

Tables created:
1. dim_location       → Dimension table for locations
2. jobs_fact          → Central fact table for job postings
3. jobs_per_location  → Aggregated jobs count per location
4. jobs_per_company   → Aggregated jobs count per company
5. salary_trends      → Salary evolution over time
6. skills_demand      → Most demanded skills
7. job_features       → Feature-engineered dataset for analysis/ML

⚠️ Note:
All tables are dropped before creation to ensure a clean state.
This is suitable for batch pipelines but should be used carefully in production.
"""

from sqlalchemy import create_engine, text

# PostgreSQL connection URI (Airflow database)
POSTGRES_URI = "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow"

# Create SQLAlchemy engine
engine = create_engine(POSTGRES_URI)


def create_gold_schema():
    """
    Create and initialize the Gold schema with all required tables.
    """
    # Begin transaction (auto-commit at the end)
    with engine.begin() as conn:

        # =========================
        # Create schema
        # =========================
        # Ensure the 'gold' schema exists
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))

        # =========================
        # DIMENSION TABLE: LOCATION
        # =========================
        # Drop existing table (reset)
        conn.execute(text("DROP TABLE IF EXISTS gold.dim_location"))

        # Create location dimension table
        # Stores unique locations for normalization
        conn.execute(text("""
        CREATE TABLE gold.dim_location (
            location_id SERIAL PRIMARY KEY,
            location TEXT UNIQUE
        )
        """))

        # =========================
        # FACT TABLE: JOBS
        # =========================
        # Drop existing fact table
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_fact"))

        # Create main fact table
        # Contains job postings with references to dimensions
        conn.execute(text("""
        CREATE TABLE gold.jobs_fact (
            job_id TEXT PRIMARY KEY,
            job_title TEXT,
            company_name TEXT,
            location_id INT,              -- FK to dim_location
            salary_min FLOAT,
            salary_max FLOAT,
            salary_avg FLOAT,
            posted_date DATE,
            currency TEXT,
            remote BOOLEAN,
            job_url TEXT,
            source TEXT
        )
        """))

        # =========================
        # ANALYTICS: JOBS PER LOCATION
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_per_location"))

        # Aggregated table for number of jobs per location
        conn.execute(text("""
        CREATE TABLE gold.jobs_per_location (
            location TEXT,
            job_count INT
        )
        """))

        # =========================
        # ANALYTICS: JOBS PER COMPANY
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.jobs_per_company"))

        # Aggregated table for number of jobs per company
        conn.execute(text("""
        CREATE TABLE gold.jobs_per_company (
            company TEXT,
            job_count INT
        )
        """))

        # =========================
        # ANALYTICS: SALARY TRENDS
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.salary_trends"))

        # Tracks average salary over time
        conn.execute(text("""
        CREATE TABLE gold.salary_trends (
            date_posted DATE,
            salary_avg FLOAT
        )
        """))

        # =========================
        # ANALYTICS: SKILLS DEMAND
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.skills_demand"))

        # Stores frequency of each skill in job postings
        conn.execute(text("""
        CREATE TABLE gold.skills_demand (
            skill TEXT,
            count INT
        )
        """))

        # =========================
        # FEATURE TABLE (ML / ANALYSIS)
        # =========================
        conn.execute(text("DROP TABLE IF EXISTS gold.job_features"))

        # Feature-engineered dataset
        # Useful for ML models or advanced analytics
        conn.execute(text("""
        CREATE TABLE gold.job_features (
            job_id TEXT PRIMARY KEY,
            python INT,      -- 1 if Python required, else 0
            sql INT,         -- 1 if SQL required, else 0
            aws INT,         -- 1 if AWS required, else 0
            remote INT,      -- 1 if remote, else 0
            salary_avg FLOAT
        )
        """))

    print("✅ Gold schema created successfully")


# Entry point
if __name__ == "__main__":
    create_gold_schema()