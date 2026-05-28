# Présentation des Fonctionnalités NLP / ML et des Outils de la Plateforme Job Intelligent

Ce document détaille les implémentations liées à l'Intelligence Artificielle (NLP et ML) réalisées dans le projet, ainsi que la stack technique complète utilisée pour construire la plateforme.

---

## 1. Ce qui a été réalisé en NLP et Machine Learning (ML)

La plateforme intègre plusieurs fonctionnalités avancées de traitement du langage naturel (NLP) et de recommandation, réparties entre le Data Pipeline et le Backend applicatif.

### A. NLP : Extraction des Compétences des Offres (Job Skills Extraction)
*   **Où ça se passe :** Dans le Data Pipeline (Couche Gold) - `scripts/processing/gold/gold_transformations.py`.
*   **Comment ça marche :** Lors de la transformation des données vers la couche Gold, un algorithme d'analyse de texte parcourt les descriptions brutes des offres d'emploi (issues de la couche Silver). Il effectue une recherche sémantique ciblée pour détecter la présence de technologies clés (Python, SQL, AWS) et de modalités de travail (Remote).
*   **Objectif :** Transformer du texte non structuré en variables binaires structurées (0 ou 1) stockées dans la table `job_features` pour faciliter l'analyse et la recommandation ultérieure.

### B. NLP : Analyse et Parsing de CV (Resume Parsing)
*   **Où ça se passe :** Dans l'API Backend - `fastapi/app/main.py`.
*   **Comment ça marche :** Lorsqu'un utilisateur télécharge son CV au format PDF, la bibliothèque `PyPDF2` extrait le texte brut. Ensuite, un pipeline NLP basé sur des heuristiques d'extraction d'entités nommées (NER) personnalisées et des expressions régulières (Regex) avancées scanne le document. 
*   **Objectif :** Le système confronte le texte du CV à une ontologie prédéfinie (dictionnaires de mots-clés techniques et de métiers) pour extraire automatiquement les **compétences de l'utilisateur** (ex: React, Docker, Pandas) et classifier son **rôle professionnel** (ex: Data Engineer). Ces informations mettent à jour son profil automatiquement.

### C. NLP : Recherche Floue Tolérante aux Fautes (Fuzzy Search & Similarity)
*   **Où ça se passe :** Dans l'API Backend - `fastapi/app/main.py` (Endpoint `/api/jobs`).
*   **Comment ça marche :** Pour la barre de recherche des offres, le système n'utilise pas une simple recherche exacte SQL. Il implémente l'algorithme de similarité de texte de Ratcliff/Obershelp (via `difflib.SequenceMatcher`).
*   **Objectif :** Le moteur calcule un score de similarité entre la requête de l'utilisateur et les titres/entreprises des offres. Il analyse la phrase complète mais aussi mot par mot (Tokenization). Cela permet de trouver les offres pertinentes **même si l'utilisateur fait une faute d'orthographe** (ex: taper "enginer" trouvera quand même "engineer" avec un score de similarité élevé).

### D. ML : Moteur de Recommandation d'Offres (Job Recommendations)
*   **Où ça se passe :** Dans l'API Backend - `fastapi/app/main.py` (Endpoint `/api/recommendations`).
*   **Comment ça marche :** Il s'agit d'un système de recommandation hybride basé sur le contenu (Content-Based Filtering). L'algorithme récupère les compétences extraites du CV de l'utilisateur et construit dynamiquement une requête de "Matching" complexe.
*   **Objectif :** Le système calcule le croisement entre les compétences de l'utilisateur et :
    1. Les variables ML pré-calculées (`j.python`, `j.sql`, `j.aws`).
    2. Les titres et descriptions des offres via un filtrage Regex sémantique.
    L'algorithme renvoie ensuite les offres d'emploi classées par pertinence, en affichant visuellement à l'utilisateur quels mots-clés exacts ont déclenché la recommandation (Skill Match).

---

## 2. Tous les Outils Utilisés dans la Plateforme (Stack Technique)

La plateforme repose sur une architecture moderne, modulaire et conteneurisée. Voici le détail de chaque outil utilisé :

### A. Data Engineering & Pipeline
*   **Python 3 :** Le langage principal pour tout le traitement des données.
*   **MinIO :** Un serveur de stockage objet haute performance (compatible Amazon S3) utilisé pour construire le **Data Lake**. Il héberge la couche *Bronze* (données brutes JSON) et la couche *Silver* (données nettoyées Parquet).
*   **Pandas & PyArrow :** Bibliothèques Python utilisées pour le nettoyage, la standardisation des données et la sérialisation performante au format **Parquet** (qui préserve les types et optimise le stockage).
*   **PostgreSQL :** Le Système de Gestion de Base de Données Relationnelle (SGBDR) principal. Il agit à la fois comme **Data Warehouse (Couche Gold)** en modélisant les données en schéma en étoile (Star Schema), et comme **Base de données OLTP** pour l'application (utilisateurs, paramètres, favoris).
*   **SQLAlchemy :** L'ORM (Object-Relational Mapping) Python utilisé pour interagir avec PostgreSQL de manière sécurisée et performante.
*   **Apache Airflow :** L'outil d'orchestration. Il permet de planifier (Scheduling), d'exécuter et de monitorer le pipeline de données (les DAGs) de bout en bout (Extraction -> MinIO -> Traitement -> PostgreSQL).

### B. Backend Applicatif (API)
*   **FastAPI :** Framework web moderne et ultra-rapide utilisé pour créer l'API REST qui fait le pont entre la base de données et l'interface utilisateur.
*   **Uvicorn :** Le serveur ASGI utilisé pour faire tourner l'application FastAPI en production.
*   **Pydantic :** Utilisé au sein de FastAPI pour la validation stricte des données (Data parsing) entre le frontend et le backend.
*   **PyPDF2 :** Bibliothèque Python spécialisée dans la lecture et l'extraction de texte à partir de fichiers PDF (utilisée pour le Resume Parsing).
*   **Hashlib :** Module de cryptographie utilisé pour sécuriser les mots de passe des utilisateurs en base de données (hachage SHA-256).

### C. Frontend (Interface Utilisateur)
*   **HTML5 / CSS3 :** Pour la structure et le design visuel de la plateforme. Le style utilise des techniques modernes de mise en page (Flexbox, Grid) pour assurer la réactivité.
*   **JavaScript (Vanilla) :** Utilisé pour toute la logique côté client (DOM manipulation, gestion des états).
*   **Fetch API :** Utilisée en JavaScript pour effectuer des requêtes HTTP asynchrones vers le backend FastAPI (pour la connexion, la recherche, l'upload de CV).

### D. Infrastructure & Déploiement
*   **Docker :** Utilisé pour la conteneurisation de chaque composant (PostgreSQL, MinIO, Airflow, FastAPI). Cela garantit que l'application s'exécute de la même manière sur n'importe quel ordinateur.
*   **Docker Compose :** Outil permettant de définir et d'orchestrer tous les conteneurs multi-services via un seul fichier (`docker-compose.yml`), gérant les réseaux internes et les volumes de persistance des données.

### E. Business Intelligence (BI)
*   **Power BI :** L'outil de visualisation de données de Microsoft. Il se connecte directement à la base de données PostgreSQL (Couche Gold) pour générer des tableaux de bord interactifs et analytiques sur les tendances du marché de l'emploi (salaires, compétences demandées, répartition géographique).
