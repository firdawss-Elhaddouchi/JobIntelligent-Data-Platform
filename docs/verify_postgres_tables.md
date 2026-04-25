Good — now we move from pipeline → **data validation (very important step)** 👇

---

# 🧠 ✅ 1. First: connect to PostgreSQL

Since you're using Docker, you have **2 ways**

---

## 🟢 OPTION A — From your terminal (easiest)

Run:

```bash
docker exec -it postgres_db psql -U airflow -d airflow
```

---

## 🟢 OPTION B — From your machine (if psql installed)

```bash
psql -h localhost -U airflow -d airflow
```

Password:

```text
airflow
```

---

# 🧠 ✅ 2. Show all tables

Once inside PostgreSQL:

```sql
\dt
```

👉 You should see:

```text
jobs_fact
jobs_per_location
jobs_per_company
salary_trends
skills_demand
job_features
```

---

# 🧠 ✅ 3. Inspect a table

Example:

```sql
SELECT * FROM jobs_fact LIMIT 10;
```

---

# 🧠 ✅ 4. Check columns

```sql
\d jobs_fact
```

---

# 🧠 ✅ 5. Count rows (VERY IMPORTANT)

```sql
SELECT COUNT(*) FROM jobs_fact;
```

---

# 🚨 If you see NO TABLES

Then your pipeline didn’t write to PostgreSQL.

### 👉 Debug quickly:

Run this in Python:

```python
print("Uploading to PostgreSQL...")
```

Or check if this ran:

```python
engine = get_postgres_engine()
upload_to_postgres(...)
```

---

# 🧠 🧪 6. Check directly via SQL query (advanced)

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

---

# 🧠 💡 Pro tip (important)

Right now you are doing:

```python
if_exists="replace"
```

👉 That means:

⚠️ Every run = deletes old data

Later you should use:

```python
if_exists="append"
```

---

# 🚀 BONUS — GUI (much easier)

If you want visual view:

👉 Uncomment your pgAdmin in docker-compose

Then open:

```text
http://localhost:5050
```

---

# 🎯 What you should verify

✔ Tables exist
✔ Data is not empty
✔ Columns match expected schema

---

