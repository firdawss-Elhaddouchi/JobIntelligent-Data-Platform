from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Job Intelligent Platform API")

# Allow Frontend to connect to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Job Intelligent Platform API is running"}

@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch high-level statistics for the dashboard cards"""
    query_total = text("SELECT COUNT(*) FROM gold.fact_jobs")
    total_jobs = db.execute(query_total).scalar()
    
    query_remote = text("SELECT COUNT(*) FROM gold.fact_jobs WHERE is_remote = 1")
    remote_jobs = db.execute(query_remote).scalar()

    query_avg = text("SELECT ROUND(AVG(salary_avg)::numeric, 2) FROM gold.fact_jobs WHERE salary_avg IS NOT NULL")
    avg_salary = db.execute(query_avg).scalar()
    
    return {
        "total_jobs": total_jobs,
        "remote_jobs": remote_jobs,
        "avg_salary": float(avg_salary) if avg_salary else 0
    }

@app.get("/api/jobs")
def get_job_listings(search: str = None, remote_only: bool = False, db: Session = Depends(get_db)):
    """Fetch jobs, simulating the 'Search/Filter Jobs' use case"""
    
    base_query = """
        SELECT 
            f.job_id, f.job_title, c.company_name, 
            l.location, l.city, l.country, d.date AS posted_date, 
            f.salary_avg, f.is_remote
        FROM gold.fact_jobs f
        LEFT JOIN gold.dim_company c ON f.company_id = c.company_id
        LEFT JOIN gold.dim_location l ON f.location_id = l.location_id
        LEFT JOIN gold.dim_date d ON f.posted_date_id = d.date_id
        WHERE 1=1
    """
    
    if remote_only:
        base_query += " AND f.is_remote = 1"
        
    if search:
        base_query += f" AND (f.job_title ILIKE '%{search}%' OR c.company_name ILIKE '%{search}%')"
        
    base_query += " LIMIT 50"
    
    query = text(base_query)
    result = db.execute(query).fetchall()
    
    jobs = []
    for row in result:
        jobs.append({
            "job_id": row[0],
            "job_title": row[1],
            "company_name": row[2],
            "location": row[3],
            "city": row[4],
            "country": row[5],
            "posted_date": str(row[6]) if row[6] else None,
            "salary_avg": row[7],
            "is_remote": row[8]
        })
    return {"jobs": jobs}

@app.get("/api/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    """Simulate 'Get Personalized Recommendations' Use Case based on Job Features ML Table"""
    query = text("""
        SELECT j.job_id, f.job_title, f.salary_avg, j.python, j.sql, j.aws
        FROM gold.job_features j
        JOIN gold.fact_jobs f ON j.job_id = f.job_id
        WHERE j.python = 1 OR j.sql = 1
        LIMIT 5
    """)
    result = db.execute(query).fetchall()
    
    recs = []
    for row in result:
        recs.append({
            "job_id": row[0],
            "job_title": row[1],
            "salary_avg": row[2],
            "skills": [skill for skill, val in zip(['Python', 'SQL', 'AWS'], [row[3], row[4], row[5]]) if val == 1]
        })
    return {"recommendations": recs}
