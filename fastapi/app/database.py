from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Connect to the Airflow Postgres DB. Fallback to localhost if running outside Docker.
POSTGRES_URI = os.getenv("DATABASE_URL", "postgresql+psycopg2://airflow:airflow@localhost:5432/airflow")

engine = create_engine(POSTGRES_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
