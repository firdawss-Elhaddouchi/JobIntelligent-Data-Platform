APIs (3 sources)
        ↓
Bronze (3 separate raw files)
        ↓
Processing (clean + normalize)
        ↓
Silver (1 unified dataset)
        ↓
NLP + Recommendation
        ↓
Gold (aggregated data)
        ↓
Power BI

OLTP = transactional system (fast inserts/updates)
OLAP = analytical queries (heavy aggregations)

🔥 Pro tip (this will impress your professor)

Say this:

“We separate layers logically using PostgreSQL schemas. In production, OLTP and OLAP would be physically separated, but for this project we simulate the data warehouse using a dedicated gold schema.”

### Github repo to follow:

https://github.com/avishek-sarkar/Job-Recommendation-System?tab=readme-ov-file