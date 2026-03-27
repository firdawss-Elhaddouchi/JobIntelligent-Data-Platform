from fastapi import FastAPI

app = FastAPI(title="JobIntelligent Data Platform API")

@app.get("/")
def read_root():
    return {"message": "JobIntelligent Data Platform API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}