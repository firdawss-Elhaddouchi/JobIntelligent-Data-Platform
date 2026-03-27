from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Job Intelligent API is running", "version": "1.0"}