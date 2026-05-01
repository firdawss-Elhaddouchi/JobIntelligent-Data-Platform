# 🧠 What is `.pbip`?

* `.pbip` = **Power BI Project** file format
* Introduced in **Power BI Desktop / Power BI Project (PBIP)**.
* Unlike `.pbix` (single binary file), `.pbip` is **folder-based / decomposed format**:

  * Stores **queries, data model, measures, and reports as separate files**.
  * Fully **text-based / JSON**, which makes it **Git-friendly**.

✅ This is exactly what teams need for collaborative work.

---

# 🔹 Advantages over `.pbix` for teams

| Feature         | `.pbix`              | `.pbip`                                  |
| --------------- | -------------------- | ---------------------------------------- |
| Editable in Git | ❌                    | ✅                                        |
| Merge conflicts | High                 | Low                                      |
| Modularity      | No                   | Yes, everything decomposed               |
| Team workflow   | One person at a time | Multiple people can edit different parts |

---

# 🏗️ How it works in your project

### Folder structure inside `.pbip` (simplified)

```
my_dashboard.pbip/
├── DataSources/
│   └── jobs_silver.json
├── Model/
│   ├── tables.json
│   └── relationships.json
├── Measures/
│   └── DAX/
├── Report/
│   └── pages.json
└── Theme/
    └── theme.json
```

* Each file can be version-controlled separately in Git.
* Team members can work on **different parts** at the same time:

  * One edits **data model**
  * One edits **report pages**
  * One edits **DAX measures**

---

# 🔹 How your team should use `.pbip`

1. **Data team**

   * Prepares Silver layer in PostgreSQL / CSV
   * Updates `DataSources/` in `.pbip` if needed

2. **Report / BI team**

   * Works on `Report/pages.json` or visual pages
   * Can merge changes via Git

3. **Analytics / NLP team**

   * Provides tables for top skills, job matching
   * Stored in PostgreSQL → connected in `.pbip` dataset

4. **Git Workflow**

   * Use `main` branch for stable dashboards
   * Use feature branches for editing pages or measures
   * Merge via Git → `.pbip` can handle text diffs

---

# ✅ TL;DR

* `.pbip` = **best for team collaboration**
* `.pbix` = good for single-user / simple projects
* **Recommendation for your project**:

  * Use `.pbip` format
  * Store in **Git / OneDrive**
  * Connect to **Silver dataset** (PostgreSQL)
  * Each team member works on different parts

---

# 📊 Trame pour Présentation PPT (Intégration PBIP Étape par Étape)

Voici le plan exact, slide par slide, pour expliquer à votre équipe ou votre jury comment vous intégrez le format `.pbip` dans l'architecture **JobIntelligent-Data-Platform**.

### Slide 1 : Le Défi du Travail en Équipe sur Power BI
* **Problème :** Le format classique `.pbix` est un fichier binaire lourd. Il est impossible de travailler à plusieurs en même temps sans écraser le travail de l'autre (conflits de fusion).
* **Impact sur le projet :** Ralentissement du développement du tableau de bord de la Data Platform.
* **Solution :** Activer la fonctionnalité "Power BI Project (.pbip)".

### Slide 2 : Qu'est-ce que le format PBIP ?
* **Concept :** Décomposition du fichier binaire en dossiers lisibles par l'homme (texte / JSON / TMDL).
* **Séparation claire :** 
  * Un dossier pour le modèle de données (`.Dataset`).
  * Un dossier pour les visuels/rapports (`.Report`).
* **Avantage clé :** Compatible avec Git (GitHub/GitLab) pour l'intégration continue (CI/CD) de notre plateforme.

### Slide 3 : Étape 1 - Préparation et Connexion aux Données
* **Action :** Dans Power BI Desktop, activer "Enregistrer en tant que projet Power BI (.pbip)" dans les options en préversion.
* **Architecture JobIntelligent :** Connecter Power BI à notre **Couche Gold (ou Silver)**.
  * *Option A :* Connexion à PostgreSQL (si les données agrégées y sont stockées).
  * *Option B :* Connexion S3/MinIO (pour lire les fichiers Parquet directement).
* **Résultat :** Importation ou DirectQuery des données nettoyées par Airflow.

### Slide 4 : Étape 2 - Modélisation des Données (Dataset)
* **Membre de l'équipe Data Analyst/Engineer :** 
  * Crée le schéma en étoile (Table de faits "Offres d'emploi", Tables de dimensions "Temps, Compétences, Entreprises, Localisation").
  * Crée les mesures DAX complexes (Salaire moyen, Top mots-clés, Nombre d'offres).
* **Sauvegarde :** Le travail est sauvegardé dans le dossier `.Dataset` du projet `.pbip`.

### Slide 5 : Étape 3 - Création des Rapports (Report)
* **Membre de l'équipe BI/Data Viz :**
  * Se connecte au *Dataset* déjà créé.
  * Construit les visuels (Cartes pour la localisation des offres, Graphiques à barres pour les salaires, Nuages de mots pour les compétences).
* **Sauvegarde :** Le travail est sauvegardé dans le dossier `.Report` du projet `.pbip`.
* **Collaboration :** Les deux membres de l'équipe travaillent en parallèle !

### Slide 6 : Étape 4 - Intégration Git (Versionnement)
* **Action :** Commit et Push des dossiers PBIP sur notre dépôt GitHub.
* **Workflow :**
  * Création de branches séparées (ex: `feature/dax-measures` et `feature/map-visuals`).
  * *Pull Requests* : On peut lire exactement ce qui a été modifié grâce au format JSON.
  * Les conflits sont gérés ligne par ligne comme pour du code Python ou SQL.

### Slide 7 : Étape 5 - Déploiement CI/CD (DataOps)
* **Le futur de la plateforme :**
  * Utilisation de l'intégration Git native de Power BI Service (ou Azure DevOps).
  * Lorsqu'un "Merge" est fait sur la branche `main`, le tableau de bord est automatiquement mis à jour et déployé dans le workspace Power BI de l'entreprise.
* **Bénéfice final :** Une Data Platform 100% automatisée, de l'ingestion (Airflow/Adzuna) jusqu'à la restitution visuelle (Power BI).

