from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import io
import PyPDF2

app = FastAPI(title="Job Intelligent Platform API")

# Allow Frontend to connect to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- Pydantic Models ---
class UserRegister(BaseModel):
    full_name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class JobAction(BaseModel):
    user_id: int
    job_id: str

@app.get("/")
def root():
    return {"message": "Job Intelligent Platform API is running"}

# --- AUTH & USERS ---
@app.post("/api/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # Check if email exists
    query_check = text("SELECT user_id FROM app.users WHERE email = :email")
    if db.execute(query_check, {"email": user.email}).fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = hash_password(user.password)
    
    query_insert = text("""
        INSERT INTO app.users (full_name, email, password_hash, skills)
        VALUES (:name, :email, :pw, '') RETURNING user_id
    """)
    result = db.execute(query_insert, {"name": user.full_name, "email": user.email, "pw": hashed_pw})
    user_id = result.scalar()
    db.commit()
    
    return {"user_id": user_id, "full_name": user.full_name, "email": user.email, "skills": ""}

@app.post("/api/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    hashed_pw = hash_password(user.password)
    query = text("SELECT user_id, full_name, email, skills FROM app.users WHERE email = :email AND password_hash = :pw")
    result = db.execute(query, {"email": user.email, "pw": hashed_pw}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    return {"user_id": result[0], "full_name": result[1], "email": result[2], "skills": result[3]}

# --- DASHBOARD & JOBS ---
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
    
    result = db.execute(text(base_query)).fetchall()
    jobs = []
    for row in result:
        jobs.append({
            "job_id": row[0], "job_title": row[1], "company_name": row[2],
            "location": row[3], "city": row[4], "country": row[5],
            "posted_date": str(row[6]) if row[6] else None, "salary_avg": row[7], "is_remote": row[8]
        })
    return {"jobs": jobs}

@app.get("/api/recommendations")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Personalized Recommendations based on the User's actual skills vs Job Features ML Table"""
    # 1. Fetch user skills
    user = db.execute(text("SELECT skills FROM app.users WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    if not user or not user[0]:
        return {"recommendations": []} # No skills = no recs
        
    user_skills = user[0].lower()
    
    # 2. Build dynamic ML query based on what we have in job_features (python, sql, aws)
    conditions = []
    if "python" in user_skills: conditions.append("j.python = 1")
    if "sql" in user_skills: conditions.append("j.sql = 1")
    if "aws" in user_skills: conditions.append("j.aws = 1")
    
    if not conditions:
        return {"recommendations": []} # No matching skills in our ML model
        
    where_clause = " OR ".join(conditions)
    
    query = text(f"""
        SELECT j.job_id, f.job_title, f.salary_avg, j.python, j.sql, j.aws
        FROM gold.job_features j
        JOIN gold.fact_jobs f ON j.job_id = f.job_id
        WHERE {where_clause}
        LIMIT 5
    """)
    result = db.execute(query).fetchall()
    
    recs = []
    for row in result:
        recs.append({
            "job_id": row[0], "job_title": row[1], "salary_avg": row[2],
            "skills": [skill for skill, val in zip(['Python', 'SQL', 'AWS'], [row[3], row[4], row[5]]) if val == 1]
        })
    return {"recommendations": recs}

# --- FAVORITES & APPLICATIONS ---
@app.get("/api/user/{user_id}/favorites")
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    query = text("""
        SELECT f.job_id FROM app.user_favorites uf
        JOIN gold.fact_jobs f ON uf.job_id = f.job_id
        WHERE uf.user_id = :uid
    """)
    result = db.execute(query, {"uid": user_id}).fetchall()
    return {"favorites": [row[0] for row in result]}

@app.post("/api/user/favorite")
def toggle_favorite(action: JobAction, db: Session = Depends(get_db)):
    # Check if exists
    check = db.execute(text("SELECT 1 FROM app.user_favorites WHERE user_id = :uid AND job_id = :jid"), {"uid": action.user_id, "jid": action.job_id}).fetchone()
    if check:
        db.execute(text("DELETE FROM app.user_favorites WHERE user_id = :uid AND job_id = :jid"), {"uid": action.user_id, "jid": action.job_id})
        status_msg = "removed"
    else:
        db.execute(text("INSERT INTO app.user_favorites (user_id, job_id) VALUES (:uid, :jid)"), {"uid": action.user_id, "jid": action.job_id})
        status_msg = "added"
    db.commit()
    return {"status": status_msg}

@app.get("/api/user/{user_id}/applications")
def get_applications(user_id: int, db: Session = Depends(get_db)):
    query = text("""
        SELECT f.job_id FROM app.user_applications ua
        JOIN gold.fact_jobs f ON ua.job_id = f.job_id
        WHERE ua.user_id = :uid
    """)
    result = db.execute(query, {"uid": user_id}).fetchall()
    return {"applications": [row[0] for row in result]}

@app.post("/api/user/apply")
def apply_job(action: JobAction, db: Session = Depends(get_db)):
    check = db.execute(text("SELECT 1 FROM app.user_applications WHERE user_id = :uid AND job_id = :jid"), {"uid": action.user_id, "jid": action.job_id}).fetchone()
    if not check:
        db.execute(text("INSERT INTO app.user_applications (user_id, job_id) VALUES (:uid, :jid)"), {"uid": action.user_id, "jid": action.job_id})
        db.commit()
    return {"status": "applied"}

class UserProfileUpdate(BaseModel):
    full_name: str
    skills: str

@app.put("/api/user/{user_id}/profile")
def update_profile(user_id: int, profile: UserProfileUpdate, db: Session = Depends(get_db)):
    db.execute(
        text("UPDATE app.users SET full_name = :name, skills = :skills WHERE user_id = :uid"),
        {"name": profile.full_name, "skills": profile.skills, "uid": user_id}
    )
    db.commit()
    return {"status": "updated", "full_name": profile.full_name, "skills": profile.skills}

@app.delete("/api/user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # Deletes the user. ON DELETE CASCADE in PostgreSQL will automatically remove favorites & applications.
    db.execute(text("DELETE FROM app.users WHERE user_id = :uid"), {"uid": user_id})
    db.commit()
    return {"status": "deleted"}

# --- NLP CV PARSING ---
TECH_SKILLS = ["python", "sql", "aws", "azure", "gcp", "docker", "kubernetes", "airflow", "power bi", "tableau", "java", "scala", "javascript", "react", "fastapi", "pandas", "spark", "hadoop"]
ROLES = ["data engineer", "data scientist", "data analyst", "backend developer", "frontend developer", "full stack", "software engineer", "machine learning engineer"]

def extract_info_from_text(text: str):
    text_lower = text.lower()
    
    found_skills = []
    for skill in TECH_SKILLS:
        # Simple exact match (in a real ML system, we'd use spaCy NER)
        if skill in text_lower:
            found_skills.append(skill.title() if len(skill) > 3 else skill.upper())
            
    found_role = ""
    for role in ROLES:
        if role in text_lower:
            found_role = role.title()
            break
            
    return ", ".join(found_skills), found_role

@app.post("/api/user/{user_id}/upload_cv")
async def upload_cv(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for now.")
        
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        
        cv_text = ""
        for page in pdf_reader.pages:
            cv_text += page.extract_text() + " "
            
        skills, role = extract_info_from_text(cv_text)
        
        # Update user profile automatically
        if skills:
            db.execute(
                text("UPDATE app.users SET skills = :skills WHERE user_id = :uid"),
                {"skills": skills, "uid": user_id}
            )
            db.commit()
            
        return {
            "status": "success",
            "extracted_skills": skills,
            "extracted_role": role,
            "message": "CV Analyzed successfully by our system!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
