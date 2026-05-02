Good — now we move from pipeline → **data validation (very important step)** 👇

---

# 🧠 ✅ 1. First: connect to PostgreSQL


---

## 🟢 OPTION A — From your terminal (easiest)

Run:

```bash
docker exec -it postgres_db psql -U airflow -d airflow
```

# 🧠 ✅ 2. Show all tables

Once inside PostgreSQL:

```sql
\dt gold.*
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
SELECT * FROM gold.jobs_fact LIMIT 10;
```

---

# 🧠 ✅ 4. Check columns

```sql
\d gold.jobs_fact
```

---

# 🧠 ✅ 5. Count rows (VERY IMPORTANT)

```sql
SELECT COUNT(*) FROM gold.jobs_fact;
```

---


You’re already in the right place in Power BI 👍 — you just need to connect it properly to your PostgreSQL “gold” schema.

---

# ✅ Step-by-step: Connect PostgreSQL → Power BI

### 1. Choose the correct connector

In your screen:

![Image](https://images.openai.com/static-rsc-4/XztmjREC9D9N2i1uVe9XbpippSpiC7cIOom9sD32t1X9sF-5z0E435ZUzc4aNfShTVCmL79-Mj76W0_NRSh1r4Arw81R18MObQ30B6O6of7qJoHgLvklSiq6hJrTmEN6CvkYJleNhMBALTheZIsY8V4Y-RJqDYr1vU8oo43HxxMTQABgITj0qFJoDU02PtOO?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/gk6EBNndheJMSv0gg656ISox549pjMcHSm0zHNmdGQLWwSZxgkXMn8Bbd82xJY4p-O9-nU92ccd1j2ucYHGTzmpfEI8z0uKzuNuP4iNoqun-LIccG-ooaguAK0dzzAOHymERLFuxP6C8lUoMvxy35FiJxBssu3i8l52JbbkmX9Hm9xPE0h9jix2apBc0fIBM?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/xnmtBAwU0zT0hd0pfp_mc9DBQn1w4Kk8jL-cYwefsk8IOZ4wiflF8AHrLG864KssdvIjGOKbfscLt1kpfb4xpZW2q4ScGt0kQDMSYDOyEf5aa0FM2YzyieDABbYLmYg5AEnJJv3efEbfvC8inu0zrpwQrq1H7HcVfNuoQTZjQnoN1EjeJunVxi6FH9SHlmNw?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/NKrh-Sv5vP3eqHy0GLth88qLF1V3vYDOWDrPvYHwESfV_Ccx55QIxp0qFSzN90AqYnIyG6jlhM10-mu_c2fcQCB2HJjnrk2w08G_byOxB5JqoPz9wu9LF6-WvlPt8TTmyJPKjEGiJ4pN2Y1RDpJ9PWZIPRbt5S7AqIHAh-dmGF0_FOKuSfvloqpzjqQTnAJ1?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/bE8n5T51_RfYHgDNybY3W2PPurxRGbMCpL1_RBMIZMpZpBI2blCnYLX9_zzJm5Cq4qyCCEyniQYOM_yW8aiqM2Ce0XpKqFpUEvYkESRUgJEh-6tu3TC2ixqbp_DpDjHUu3MGazCwpEECJu3aFuu4gsW9frRH4JO0aczgNV2nPJN22v9hG4SrFR4DeMdunQmV?purpose=fullsize)

![Image](https://images.openai.com/static-rsc-4/Mo5iPFSJXP8GMV2uOVZXR7cZm3kYMNS-q2vbiSKaNF8K6bIFUllCRJdilAVkt3Sz6wrOmo29SASqm-dRfVE-ek2AGQAoXyOuDm86awt3rJv4JlfaQhht2PFM3HslEOcaRpkmQ2je3Rz7kVPK3--FKE7RRx4NmMsAPntzzSQg31wCy4UEtKs38HvU7clxjLot?purpose=fullsize)

👉 Click:
**`Más...` → search “PostgreSQL” → select PostgreSQL database**

---

## ⚠️ If PostgreSQL is not listed

Power BI requires the **Npgsql driver**.

👉 Install it:

* Download: [https://www.npgsql.org/download.html](https://www.npgsql.org/download.html)
* Install → restart Power BI

---

## 2. Connection settings

Fill this:

```text
Server: localhost:5432
Database: airflow
```

👉 Click **OK**

---

## 3. Authentication

Use your credentials:

```text
Username: airflow
Password: airflow
```

👉 IMPORTANT STEP:
At the bottom → choose:

✅ DirectQuery (not Import)

Click OK
---

## 4. Select your Gold tables

After connection, you’ll see schemas:

👉 Expand:

```text
gold
```

Then select:

* `jobs_fact`
* `dim_company`
* `dim_location`
* `dim_date`
* `salary_trends`
* etc.

👉 Click **Load**

---

## 💡 Best Practice (important)

Don’t just load everything blindly.

👉 For analytics:

* Use **fact + dimensions**
* Example model:

  * `jobs_fact` (main table)
  * join with:

    * `dim_company`
    * `dim_location`
    * `dim_date`

Power BI will auto-detect relationships, but verify them.

---

## 🔥 Optional (Better approach)

Instead of loading raw tables, use a SQL query:

👉 Click:
**Transform Data → Advanced Editor**

Example:

```sql
SELECT 
    f.job_id,
    f.job_title,
    c.company_name,
    l.location,
    d.posted_date,
    f.salary_avg
FROM gold.jobs_fact f
JOIN gold.dim_company c ON f.company_id = c.company_id
JOIN gold.dim_location l ON f.location_id = l.location_id
JOIN gold.dim_date d ON f.date_id = d.date_id
```

👉 This gives you a clean dataset directly.

---




