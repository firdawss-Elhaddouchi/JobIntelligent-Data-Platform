from fastapi import FastAPI
import os

app = FastAPI(title="Job Intelligent API")

@app.get("/")
def root():
    return {
        "message": "FastAPI is running successfully",
        "database_url": os.getenv("DATABASE_URL"),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT")
    }

@app.get("/health")
def health():
    return {"status": "ok"}