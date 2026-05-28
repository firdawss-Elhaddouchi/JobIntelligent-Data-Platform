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

class SettingsUpdate(BaseModel):
    refresh_rate: str

@app.get("/")
def root():
    return {"message": "Job Intelligent Platform API is running"}

@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "Server is perfectly alive!"}

# --- PLATFORM SETTINGS (AIRFLOW INTEGRATION) ---
@app.post("/api/settings")
def update_settings(settings: SettingsUpdate, db: Session = Depends(get_db)):
    """
    Saves the platform settings (e.g., Airflow Refresh Rate) to the database.
    In a real production environment, Airflow would query this table before triggering the DAG
    to dynamically adjust its schedule_interval.
    """
    # Create the settings table if it doesn't exist
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS app.platform_settings (
            setting_key VARCHAR(50) PRIMARY KEY,
            setting_value VARCHAR(255) NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Upsert the refresh rate setting
    db.execute(text("""
        INSERT INTO app.platform_settings (setting_key, setting_value, updated_at)
        VALUES ('airflow_refresh_rate', :val, CURRENT_TIMESTAMP)
        ON CONFLICT (setting_key) DO UPDATE 
        SET setting_value = EXCLUDED.setting_value,
            updated_at = EXCLUDED.updated_at
    """), {"val": settings.refresh_rate})
    db.commit()
    
    return {"status": "success", "message": f"Airflow refresh rate set to {settings.refresh_rate} in PostgreSQL."}

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
            f.salary_avg, f.is_remote,
            f.job_url, f.source, f.salary_min, f.salary_max, f.currency,
            ct.contract_type
        FROM gold.fact_jobs f
        LEFT JOIN gold.dim_company c ON f.company_id = c.company_id
        LEFT JOIN gold.dim_location l ON f.location_id = l.location_id
        LEFT JOIN gold.dim_date d ON f.posted_date_id = d.date_id
        LEFT JOIN gold.dim_contract_type ct ON f.contract_type_id = ct.contract_type_id
        WHERE 1=1
    """
    
    if remote_only:
        base_query += " AND f.is_remote = 1"
        
    if search:
        pass # NLP Scoring requires fetching the pool
    else:
        pass # Return all jobs when not searching
    
    result = db.execute(text(base_query)).fetchall()
    
    jobs = []
    for row in result:
        jobs.append({
            "job_id": row[0], "job_title": row[1], "company_name": row[2],
            "location": row[3], "city": row[4], "country": row[5],
            "posted_date": str(row[6]) if row[6] else None, 
            "salary_avg": row[7], "is_remote": row[8],
            "job_url": row[9], "source": row[10],
            "salary_min": row[11], "salary_max": row[12],
            "currency": row[13], "contract_type": row[14]
        })
        
    # ==========================================
    # --- NLP FUZZY MATCHING (TYPO TOLERANCE) ---
    # ==========================================
    # This block implements an NLP-based search algorithm designed to tolerate
    # human typos and spelling mistakes (e.g., "enginer" instead of "engineer").
    if search:
        import difflib
        search_lower = search.lower()
        scored_jobs = []
        
        for j in jobs:
            title = (j["job_title"] or "").lower()
            company = (j["company_name"] or "").lower()
            
            # 1. Exact Substring Match (Highest Priority)
            # If the user's query perfectly matches a substring in the title or company,
            # we assign a perfect score of 1.0 to ensure these results appear first.
            if search_lower in title or search_lower in company:
                scored_jobs.append((j, 1.0))
                continue
                
            # 2. NLP Typo Detection (Gestalt Pattern Matching Algorithm)
            # We use Python's difflib SequenceMatcher which uses the Ratcliff-Obershelp algorithm.
            # This calculates a similarity ratio [0.0, 1.0] between the search query and the job text.
            title_score = difflib.SequenceMatcher(None, search_lower, title).ratio()
            
            # 3. Granular Word-by-Word Analysis
            # We split the title and company names into individual tokens (words).
            # This ensures that searching for "data" matches the word "data" perfectly,
            # rather than comparing "data" against the entire string "senior data engineer".
            words = title.split() + company.split()
            word_scores = [difflib.SequenceMatcher(None, search_lower, w).ratio() for w in words]
            max_word_score = max(word_scores) if word_scores else 0
            
            # 4. Score Aggregation
            # We take the best score between the full title comparison and the individual word comparison.
            best_score = max(title_score, max_word_score)
            
            # 5. Dynamic Thresholding
            # Only keep jobs where the similarity score is 60% (0.6) or higher.
            # This threshold efficiently filters out irrelevant results while catching typos.
            if best_score >= 0.6:
                scored_jobs.append((j, best_score))
                
        # 6. Semantic Ranking
        # Sort the filtered jobs by their NLP score in descending order (most relevant first).
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
        
        # 7. Pagination / Truncation removed as requested by user
        jobs = [item[0] for item in scored_jobs]
        
    return {"jobs": jobs}

@app.get("/api/recommendations")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    ML-Powered Job Recommendation Engine (Content-Based Filtering)
    ==============================================================
    This endpoint implements a real Machine Learning recommendation model trained
    on our actual data corpus using:
    - TF-IDF Vectorization (Term Frequency-Inverse Document Frequency)
    - Cosine Similarity
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    
        # 1. Fetch user skills
        user = db.execute(text("SELECT skills FROM app.users WHERE user_id = :uid"), {"uid": user_id}).fetchone()
        if not user or not user[0]:
            return {"recommendations": []}

        user_skills = user[0].lower()
        user_skill_list = [s.strip() for s in user_skills.split(",") if s.strip()]
        user_document = " ".join(user_skill_list)
    
        # 2. Fetch the full job corpus (Training Data)
        query = text("""
            SELECT 
                j.job_id, f.job_title, f.salary_avg, j.extracted_skills,
                c.company_name, l.location, l.city, l.country, d.date AS posted_date,
                f.is_remote, f.job_url, f.source, f.salary_min, f.salary_max, f.currency,
                ct.contract_type
            FROM gold.job_features j
            JOIN gold.fact_jobs f ON j.job_id = f.job_id
            LEFT JOIN gold.dim_company c ON f.company_id = c.company_id
            LEFT JOIN gold.dim_location l ON f.location_id = l.location_id
            LEFT JOIN gold.dim_date d ON f.posted_date_id = d.date_id
            LEFT JOIN gold.dim_contract_type ct ON f.contract_type_id = ct.contract_type_id
        """)
        result = db.execute(query).fetchall()
    
        if not result:
            return {"recommendations": []}
    
        # 3. Feature Engineering: Build "Documents" for TF-IDF
        job_documents = []
        job_rows = []
    
        for row in result:
            doc_parts = []
            if row[1]: doc_parts.append(row[1].lower()) # Title
            if row[3]: doc_parts.append(row[3].lower().replace(",", " ")) # Extracted NLP skills
            if row[4]: doc_parts.append(row[4].lower()) # Company
            
            job_document = " ".join(doc_parts)
            job_documents.append(job_document)
            job_rows.append(row)
    
        # 4. TF-IDF Vectorization
        corpus = [user_document] + job_documents  # Index 0 is the User
        vectorizer = TfidfVectorizer(stop_words='english', max_features=5000, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(corpus)
    
        # 5. Cosine Similarity Scoring
        user_vector = tfidf_matrix[0:1]
        job_vectors = tfidf_matrix[1:]
        similarity_scores = cosine_similarity(user_vector, job_vectors).flatten()
    
        # 6. Rank Results
        scored_jobs = []
        for idx, score in enumerate(similarity_scores):
            if score > 0.01: # lowered threshold for testing
                scored_jobs.append((job_rows[idx], score))
    
        scored_jobs.sort(key=lambda x: x[1], reverse=True)
    
        # 7. Build Response
        recs = []
        for row, ml_score in scored_jobs[:30]: # Return top 30
            job_title_lower = (row[1] or "").lower()
            extracted_skills_raw = (row[3] or "").lower()
            
            # UI Tags: Intersect user skills with job extracted skills
            matched_tags = []
            for s in user_skill_list:
                if s in extracted_skills_raw or s in job_title_lower:
                    matched_tags.append(s.title() if len(s) > 3 else s.upper())
                    
            if not matched_tags:
                matched_tags.append("ML Match")
                
            recs.append({
                "job_id": row[0], "job_title": row[1], "salary_avg": row[2],
                "skills": list(set(matched_tags)), # Deduplicate tags
                "ml_score": round(float(ml_score), 4),
                "company_name": row[4], "location": row[5], "city": row[6], "country": row[7],
                "posted_date": str(row[8]) if row[8] else None, "is_remote": row[9],
                "job_url": row[10], "source": row[11], "salary_min": row[12], "salary_max": row[13],
                "currency": row[14], "contract_type": row[15]
            })
        
        return {"recommendations": recs}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR TF-IDF Full] {error_trace}")
        return {"error": str(e), "traceback": error_trace}

@app.get("/api/recommendations/semantic")
def get_semantic_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    ADVANCED BERT MODEL (Semantic Meaning)
    ======================================
    This endpoint uses a pre-trained Deep Learning Transformer model (Sentence-BERT)
    to generate dense vector embeddings of the user's CV and the Job Descriptions.
    It understands semantic meaning rather than just matching words.
    Example: "Software Engineer" will match "Python Programmer" based on context.
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except Exception as e:
        print(f"[ERROR Semantic] {e}")
        return {"error": "sentence-transformers library is not installed or failed to load."}

    # 1. Fetch user skills
    user = db.execute(text("SELECT skills FROM app.users WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    if not user or not user[0]:
        return {"recommendations": []}

    user_skills = user[0].lower()
    
    # 2. Fetch full job corpus
    query = text("""
        SELECT 
            j.job_id, f.job_title, f.salary_avg, j.extracted_skills, j.semantic_entities,
            c.company_name, l.location, l.city, l.country, d.date AS posted_date,
            f.is_remote, f.job_url, f.source, f.salary_min, f.salary_max, f.currency,
            ct.contract_type
        FROM gold.job_features j
        JOIN gold.fact_jobs f ON j.job_id = f.job_id
        LEFT JOIN gold.dim_company c ON f.company_id = c.company_id
        LEFT JOIN gold.dim_location l ON f.location_id = l.location_id
        LEFT JOIN gold.dim_date d ON f.posted_date_id = d.date_id
        LEFT JOIN gold.dim_contract_type ct ON f.contract_type_id = ct.contract_type_id
    """)
    result = db.execute(query).fetchall()

    if not result:
        return {"recommendations": []}

    # 3. Load the Sentence-Transformer Model (Lightweight BERT)
    # Caching in memory is recommended for production, but loaded here for demonstration
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 4. Prepare texts for embedding
    job_texts = []
    job_rows = []
    
    for row in result:
        # Build a semantic paragraph for the job
        title = str(row[1]) if row[1] else ""
        skills = str(row[3]).replace(",", " ") if row[3] else ""
        entities = str(row[4]).replace(",", " ") if row[4] else ""
        
        # Combine into a meaningful sentence context for BERT
        text_context = f"Job Title: {title}. Required skills and entities: {skills} {entities}."
        job_texts.append(text_context)
        job_rows.append(row)

    # 5. Generate Dense Vectors (Embeddings)
    # This encodes the semantic meaning into a 384-dimensional vector space
    corpus_embeddings = model.encode([user_skills] + job_texts)
    
    user_vector = corpus_embeddings[0:1]
    job_vectors = corpus_embeddings[1:]

    # 6. Compute Cosine Similarity on dense vectors
    similarity_scores = cosine_similarity(user_vector, job_vectors).flatten()

    # 7. Rank and Filter Results
    scored_jobs = []
    print(f"[DEBUG Semantic] Max similarity: {max(similarity_scores) if len(similarity_scores) > 0 else 0}")
    for idx, score in enumerate(similarity_scores):
        if score > 0.01: # Lowered threshold to ensure we capture semantic matches
            scored_jobs.append((job_rows[idx], score))

    scored_jobs.sort(key=lambda x: x[1], reverse=True)

    # 8. Build Response
    recs = []
    for row, semantic_score in scored_jobs[:30]:
        recs.append({
            "job_id": row[0], "job_title": row[1], "salary_avg": row[2],
            "skills": ["BERT Match", "Semantic AI"], # Semantic match tag
            "ml_score": round(float(semantic_score), 4),
            "company_name": row[5], "location": row[6], "city": row[7], "country": row[8],
            "posted_date": str(row[9]) if row[9] else None, "is_remote": row[10],
            "job_url": row[11], "source": row[12], "salary_min": row[13], "salary_max": row[14],
            "currency": row[15], "contract_type": row[16]
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

# ==========================================
# --- NLP CV PARSING & FEATURE EXTRACTION ---
# ==========================================
# This module simulates an NLP Named Entity Recognition (NER) pipeline.
# In a fully productionized ML system, this would utilize models like spaCy or HuggingFace Transformers.
# Here, we implement a robust keyword-based extraction heuristic to map raw CV text to our Gold Layer schema.

# Pre-defined technological ontology dictionary (Expanded for better NLP extraction)
TECH_SKILLS = [
    # Data & Analytics
    "python", "sql", "r", "sas", "excel", "power bi", "tableau", "looker", "qlik", "alteryx", "matlab", "data mining", "matplotlib",
    # Big Data & Cloud
    "aws", "azure", "gcp", "hadoop", "spark", "pyspark", "kafka", "snowflake", "bigquery", "redshift", "databricks",
    # Orchestration & DevOps
    "docker", "kubernetes", "airflow", "dbt", "terraform", "jenkins", "gitlab ci", "ansible", "linux", "windows", "bash", "git", "github", "gitlab",
    # Web & Backend
    "java", "scala", "c", "c++", "c#", "go", "rust", "javascript", "typescript", "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring boot", "php", "html", "css",
    # Machine Learning & AI
    "pandas", "numpy", "scikit-learn", "tensorflow", "keras", "pytorch", "huggingface", "nlp", "computer vision",
    # Databases
    "postgresql", "mysql", "mongodb", "cassandra", "redis", "elasticsearch", "neo4j", "oracle"
]

# Pre-defined professional taxonomy
ROLES = [
    "data engineer", "data scientist", "data analyst", "backend developer", "frontend developer", 
    "full stack", "software engineer", "machine learning engineer", "devops engineer", "cloud architect",
    "business analyst", "product manager", "scrum master"
]

def extract_info_from_text(text: str):
    """
    NLP function to parse raw, unstructured PDF text and extract structured entities (Skills, Roles).
    
    Args:
        text (str): The raw text extracted from the user's uploaded PDF CV.
        
    Returns:
        tuple: A comma-separated string of identified skills, and the identified professional role.
    """
    import re
    # Normalize text for case-insensitive matching
    text_lower = text.lower()
    
    # 1. Skill Extraction Phase
    found_skills = []
    for skill in TECH_SKILLS:
        # Handle special characters like C++ or Node.js by escaping them
        escaped_skill = re.escape(skill)
        # Use a custom boundary that supports non-word characters (+, #)
        pattern = r'(?<![a-zA-Z0-9_])' + escaped_skill + r'(?![a-zA-Z0-9_])'
        
        if re.search(pattern, text_lower):
            # Format cleanly: acronyms (AWS, SQL, GCP, C++) in uppercase, others in Title Case
            if len(skill) <= 3 or skill in ["html", "css", "json", "rest", "php"]:
                found_skills.append(skill.upper())
            else:
                found_skills.append(skill.title())
            
    # 2. Role Classification Phase
    found_role = ""
    for role in ROLES:
        # Token search to classify the user's primary professional domain
        if role in text_lower:
            found_role = role.title()
            break # Stop at the first confident match
            
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
