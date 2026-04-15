# 🚀 PROJET JOB INTELLIGENT : DashBoard PowerBI

![Status](https://img.shields.io/badge/Status-En%20D%C3%A9veloppement-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.8.1-brightgreen)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![MinIO](https://img.shields.io/badge/MinIO-Datalake-purple)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## 📌 1. Contexte du Projet

Le secteur de la data (Data Science, Data Engineering, etc.) connaît une croissance rapide. Face à la diversité des plateformes d’emploi (Indeed, LinkedIn, France-Travail) et à l'hétérogénéité des formats et des intitulés de poste, la recherche d'opportunités est devenue chronophage et complexe pour les talents.

Ce projet propose de développer un **écosystème de données intelligent et centralisé** pour réévaluer et fluidifier la recherche d'emploi. L'outil final se manifestera par un **Dashboard Power BI** analytique et prédictif, propulsé par une architecture en arrière-plan capable d'ingérer, d'analyser et de lier les compétences aux offres grâce à l'Intelligence Artificielle (NLP).

## 🎯 2. Problématique & Objectifs

**Problèmes identifiés :**
- Dispersion extrême des annonces entre plusieurs *Job Boards*.
- Manque de standardisation des intitulés de postes et des compétences requises.
- Processus de recherche long, manuel et souvent frustrant.

**Objectifs de la plateforme :**
1. **Centraliser** de manière unifiée toutes les offres provenant de différentes sources (Adzuna, Arbeitnow, Reed, etc.).
2. **Standardiser et Nettoyer** ces données grâce au Traitement du Langage Naturel (NLP) pour une meilleure extraction d'entités (compétences, salaires, rôles).
3. **Moteur de recommandation** basé sur l'expérience et le profil.
4. **Performance & Scalabilité**, assurées par une architecture moderne adaptée aux forts volumes.

---

## 🏗️ 3. Architecture Technique (Modèle Medallion)

Le traitement de la donnée suit le standard industriel de l'**Architecture Medaillon**, gérant la donnée brute jusqu'à la restitution métier :

*   🥉 **Couche Bronze (Raw Data) - *MinIO Datalake***:
    * Stockage pur des données extraites (via API ou web scraping) aux formats bruts JSON/CSV.
    * Aucun filtrage, conservation de l'historique complet.
*   🥈 **Couche Silver (Cleaned Data) - *MinIO Datalake***:
    * Filtrage, déduplication et application des algorithmes de NLP.
    * Extraction de concepts clés : Salaires normés, listes de "Hard Skills" et "Soft Skills", localisation unifiée.
*   🥇 **Couche Gold (Business/Aggregated) - *PostgreSQL***:
    * Modélisation relationnelle (Modèle en étoile/flocon) adaptée pour l'analytique.
    * Données agrégées et hautement disponibles, prêtes à être interrogées par **FastAPI** ou visualisées par **Power BI**.

---

## ⚙️ 4. Stack Technique & Services Docker

L'ensemble du projet est encapsulé dans conteneurs, orchestrés par **Docker Compose**. Voici la liste des services de l'infrastructure :

| Service | Technologie | Rôle dans l'écosystème | Port local |
| :--- | :--- | :--- | :--- |
| **Orchestrateur** | Apache Airflow (2.8.1) | Planiﬁcation des DAGs, exécution des tâches d'ingestion/transformation (Init, Scheduler, Webserver). | `http://localhost:8080` |
| **Object Storage**| MinIO | Datalake S3-compatible, hébergeant les couches Bronze et Silver. | `http://localhost:9001` |
| **Base de Données**| PostgreSQL 15 | Data Warehouse de la couche Gold et base backend pour Airflow. | `localhost:5432` |
| **Gestion BDD** | PgAdmin 4 | Interface de gestion visuelle de la base PostgreSQL. | `http://localhost:5050` |
| **Backend API** | FastAPI | Sert la donnée manipulée provenant de Minio/Postgres pour le Dashboard PowerBI ou des clients web. | `http://localhost:8000` |
| **Exploration** | Jupyter Notebook | Environnement pour les tests Data Science (EDA, NLP prototyping). | `http://localhost:8888` |

---

## 📂 5. Arborescence du Dépôt

Le projet est rigoureusement compartimenté pour une séparation stricte des préoccupations (Orchestrateur / API / Scripts) :

```text
JobIntelligent-Data-Platform/
├── dags/                       # Définition des workflows Airflow
│   ├── dag_daily_ingestion.py  # Ex: Routine d'intégration quotidienne
│   └── dag_pipeline_medallion.py # Ex: Workflows des transformations (Bronze->Silver)
├── data/                       # Points de montage Docker (Volume local)
│   ├── minio_data/             # Persistance du Datalake MinIO (Buckets)
│   └── postgres_data/          # Persistance de la base Gold (PostgreSQL)
├── fastapi/                    # Backend API (Python)
│   ├── app/                    # Code source FastAPI (Endpoints, Models, Schemas)
│   ├── requirements.txt
│   └── Dockerfile
├── notebooks/                  # Expérimentations & Exploration
│   └── exploration_adzuna.ipynb
├── scripts/                    # Scripts "briques" (Task Airflow / Scripts isolés)
│   ├── ingestion/              # Interactions avec les APIs externes (Extraction)
│   ├── processing/             # Pipelines de transformation (Nettoyage, NLP)
│   └── analytics/              # Scripts de calculs statistiques
├── plugins/                    # Modules et Opérateurs Airflow personnalisés
├── .env                        # [Important] Clés APIs, Passwords et environnement
├── docker-compose.yml          # Définition complète de l'infra (7+ services)
└── requirements.txt            # Dépendances générales
```

---

## 🚀 6. Guide de Démarrage Rapide

### Prérequis
*   [Docker](https://www.docker.com/) et [Docker Compose](https://docs.docker.com/compose/) installés.
*   Avoir configuré le fichier `.env` situé à la racine (basé sur le `.env.example`).

### Lancement de l'infrastructure
1. **Initialiser l'environnement Airflow** (migration de DB et création d'admin) :
   ```bash
   docker-compose up airflow-init
   ```
2. **Démarrer l'ensemble des services** en arrière-plan :
   ```bash
   docker-compose up -d
   ```
3. **Vérifier l'état** :
   ```bash
   docker-compose ps
   ```

### Connexion aux services (Mots de passe selon votre `.env`) :
*   **Airflow UI** : [http://localhost:8080](http://localhost:8080)
*   **Console MinIO** : [http://localhost:9001](http://localhost:9001)
*   **PgAdmin** : [http://localhost:5050](http://localhost:5050)
*   **Jupyter Lab** : [http://localhost:8888](http://localhost:8888) (Token affiché dans les logs de la console)
*   **FastAPI Swagger UI** : [http://localhost:8000/docs](http://localhost:8000/docs)

---
*Ce projet vise à révolutionner et agréger de façon optimale le marché du recrutement de talents Data en fournissant un système complet Big Data couplé à la Business Intelligence.*
