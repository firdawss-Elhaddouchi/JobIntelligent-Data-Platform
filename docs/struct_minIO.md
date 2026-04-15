minio_server/
│
├── 🪣 bronze/                          
│   │
│   ├── 📁 2025-04-04/                  
│   │   ├── adzuna_20250404.json
│   │   ├── reed_20250404.json
│   │   └── arbeitnow_20250404.json
│   │
│   ├── 📁 2025-04-03/                  
│   │   ├── adzuna_20250403.json
│   │   ├── reed_20250403.json
│   │   └── arbeitnow_20250403.json
│   │
│   ├── 📁 2025-04-02/
│   │   └── ...
│   │
│   └── 📁 latest/                    
│       ├── adzuna_latest.json
│       ├── reed_latest.json
│       └── arbeitnow_latest.json
│
├── 🪣 silver/                         
│   │
│   ├── 📁 2025-04-04/                 
│   │   ├── jobs_cleaned_20250404.parquet
│   │   └── skills_extracted_20250404.parquet
│   │
│   ├── 📁 2025-04-03/
│   │   └── ...
│   │
│   └── 📁 latest/
│       ├── jobs_cleaned_latest.parquet
│       └── skills_extracted_latest.parquet
│
├── 🪣 gold/                            
│   │
│   ├── 📁 2025-04-04/                  
│   │   ├── jobs_by_skill_20250404.parquet
│   │   ├── jobs_by_location_20250404.parquet
│   │   ├── salary_ranges_20250404.parquet
│   │   └── trends_daily_20250404.parquet
│   │
│   ├── 📁 2025-04-03/
│   │   └── ...
│   │
│   ├── 📁 analytics/                   
│   │   ├── jobs_by_skill.parquet
│   │   ├── jobs_by_location.parquet
│   │   ├── salary_ranges.parquet
│   │   └── trends_daily.parquet
│   │
│   ├── 📁 exports/                     # ⭐ files Power BI
│   │   ├── powerbi_jobs.csv
│   │   ├── powerbi_skills.csv
│   │   └── powerbi_trends.csv
│   │
│   └── 📁 latest/
│       └── ...
│
└── 🪣 models/                          #  NLP 
    ├── skill_extractor/
    │   └── model_v1.pkl
    └── embeddings/
        └── job_embeddings_v1.npy