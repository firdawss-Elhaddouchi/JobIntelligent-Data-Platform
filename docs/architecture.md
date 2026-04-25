# 🧠 🧩 Final architecture 
🟤 Bronze → raw API data (MinIO)
⚪ Silver → cleaned unified data (Parquet)
🟡 Gold → aggregated datasets (Parquet)

🗄️ PostgreSQL → serving layer
   ├── jobs_fact
   ├── jobs_per_location
   ├── jobs_per_company
   ├── salary_trends
   └── job_features

📊 Power BI → connected to PostgreSQL