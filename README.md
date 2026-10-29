# Éligibilité à la Livraison Express - Architecture & Service ML

Projet d'industrialisation et de mise en production d'un modèle de Machine Learning pour l'évaluation en temps réel de l'éligibilité des commandes à la livraison express (**M2 IA dans le Cloud - TP1**).

---

## 1. Présentation du Projet

Ce projet structure le prototype Machine Learning issu du notebook (`notebooks/project_test_v1_final_final2.ipynb`) en une application modulaire et robuste selon les principes de la **Clean Architecture** :
- Séparation stricte entre **entraînement** (job CLI / batch) et **inférence** (API HTTP / CLI).
- Inversion de dépendances (**Repository Pattern**) pour le stockage des commandes (`OrderRepository`) et des artefacts de modèle (`ModelRepository`).
- Configuration externalisée via variables d'environnement (`pydantic-settings`).
- Point d'entrée unique par composition root (`Core`).
- Registre complet de décisions d'architecture (**ADR** couvrant le Cloud, le déploiement et la sécurité).
- Conteneurisation de production multi-stage (**Docker**).

---

## 2. Arborescence du Projet

```text
tp1/
├── src/
│   ├── livraison_express_lite/          # Package principal
│   │   ├── api/
│   │   │   └── app.py                   # API FastAPI (/health, /health/ready, /predict)
│   │   ├── core/
│   │   │   ├── core.py                  # Racine de composition (Core singleton)
│   │   │   └── learning/
│   │   │       ├── ml_pipeline.py       # Pipeline Scikit-Learn (imputation, scaling, one-hot, logreg)
│   │   │       ├── ml_predict.py        # Moteur d'inférence (MLPredict)
│   │   │       ├── ml_trainer.py        # Entraînement et tracking MLflow (MLTrainer)
│   │   │       ├── order_feature.py     # Contrat des colonnes et conversion DataFrame
│   │   │       └── train_test_splitter.py # Split stratifié train/test
│   │   ├── domain/
│   │   │   ├── entities.py              # Entités métier (OrderEntity, PredictionEntity, ModelEntity)
│   │   │   └── exceptions.py            # Exceptions du domaine
│   │   ├── infrastructure/
│   │   │   ├── model_repository.py      # Contrat ModelRepository (ABC)
│   │   │   ├── order_repository.py      # Contrat OrderRepository (ABC)
│   │   │   └── implementation/dev/
│   │   │       ├── in_memory_model_repository.py # FileModelRepository (Joblib)
│   │   │       ├── in_memory_order_repository.py # InMemoryOrderRepository
│   │   │       └── order_generator.py   # Générateur de commandes synthétiques
│   │   ├── cli.py                       # Commandes CLI (serve, train, predict)
│   │   ├── config.py                    # Configuration Settings (Pydantic)
│   │   └── __main__.py                  # Point d'entrée python -m
│   └── livraison_express/               # Alias de commande CLI
├── docs/                                # Architecture Decision Records (ADR)
│   └── adr/
│       ├── ADR-001-stockage-des-commandes.md
│       ├── ADR-002-stockage-des-artefacts-de-modele.md
│       ├── ADR-003-plateforme-de-deploiement-et-services-cloud.md
│       ├── ADR-004-strategie-de-deploiement-et-cycle-de-vie.md
│       ├── ADR-005-securisation-des-flux-et-protection-des-donnees.md
│       └── README.md                    # Index des 5 ADRs
├── notebooks/                           # Notebook historique et artefacts
│   ├── project_test_v1_final_final2.ipynb
│   └── artifacts/
│       ├── express_delivery_model.joblib
│       ├── features.json
│       └── metrics.json
├── artifacts/                           # Artefacts synchronisés du modèle
├── tests/                               # Suite de tests unitaires et d'intégration
│   ├── test_api.py
│   ├── test_cli.py
│   ├── test_data_generator.py
│   ├── test_infra.py
│   ├── test_learning.py
│   └── test_predictor.py
├── scripts/                             # Scripts utilitaires
│   ├── run_server.py
│   └── train.py
├── Dockerfile                           # Image de conteneur multi-stage non-root
├── .dockerignore                        # Règles d'exclusion Docker
├── main.py                              # Point d'entrée racine
├── order.json                           # Exemple de payload de commande
├── pyproject.toml                       # Configuration packaging et ruff
├── requirements.txt                     # Dépendances de production
├── requirements-dev.txt                 # Dépendances de développement & tests
└── .env.example                         # Modèle de variables d'environnement
```

---

## 3. Architecture Decision Records (ADR)

Le dossier [`docs/adr/`](docs/adr/) documente formellement les choix structurants au standard MADR :

1. [**ADR-001**](docs/adr/ADR-001-stockage-des-commandes.md) : Persistance des commandes (`OrderRepository` : SQLite en local / PostgreSQL en production Cloud).
2. [**ADR-002**](docs/adr/ADR-002-stockage-des-artefacts-de-modele.md) : Découplage du stockage d'artefacts (`ModelRepository` : Cloud Storage / S3 et In-Memory Caching au démarrage).
3. [**ADR-003**](docs/adr/ADR-003-plateforme-de-deploiement-et-services-cloud.md) : **Plateforme de déploiement** (Cloud vs On-premise vs Local ; Google Cloud Run / AWS ECS Fargate, Cloud SQL / RDS, Secret Manager).
4. [**ADR-004**](docs/adr/ADR-004-strategie-de-deploiement-et-cycle-de-vie.md) : **Stratégie de déploiement** (Canary Release 90/10 pour les modèles ML, Blue/Green pour les versions majeures, auto-rollback).
5. [**ADR-005**](docs/adr/ADR-005-securisation-des-flux-et-protection-des-donnees.md) : **Sécurisation de bout en bout** (TLS 1.3, Auth API Key/JWT, validation Pydantic stricte, IAM sans clés statiques, chiffrement AES-256 KMS, VPC privé).
6. [**ADR-006**](docs/adr/ADR-006-choix-sgbd-postgresql-vs-mongodb.md) : **Choix de la Base de Données (PostgreSQL vs MongoDB)** : Sélection de PostgreSQL pour l'historique complet (2015-présent), la robustesse relationnelle et le typage strict des features ML, tout en maintenant l'interchangeabilité via l'interface `OrderRepository`.

---

## 4. Guide de Démarrage Rapide

### 4.1. Installation des dépendances locales

```bash
# Activation de l'environnement virtuel (sous Windows)
.\.venv\Scripts\activate

# Installation du package en mode éditable avec ses dépendances
pip install -e .
pip install -r requirements-dev.txt
```

### 4.2. Configuration de l'environnement (.env)

```bash
copy .env.example .env
```

Variables configurables :
- `MODEL_PATH` : chemin vers l'artefact `.joblib` (par défaut `notebooks/artifacts/express_delivery_model.joblib`).
- `MODEL_THRESHOLD` : seuil de décision (par défaut `0.5`).
- `LOG_LEVEL` : niveau de log (`INFO`, `DEBUG`...).

---

## 5. Utilisation de la CLI

### 5.1. Entraîner le modèle
```bash
python -m livraison_express train
# ou :
python main.py train
```

### 5.2. Prédire une commande en local
```bash
python -m livraison_express predict --file order.json
# ou :
python main.py predict --file order.json
```

### 5.3. Démarrer le serveur API
```bash
python -m livraison_express serve --port 8000
# ou :
python main.py
# ou :
uvicorn main:app --reload
```

### 5.4. Orchestrateur de réentraînement continu
```bash
# Lancement de l'orchestrateur (surveillance continue toutes les 60s, seuil de 50 nouvelles commandes)
python -m livraison_express orchestrate --interval 60 --min-orders 50

# Ou via le script dédié :
python scripts/orchestrator.py --interval 60 --min-orders 50

# Exécution en mode batch ponctuel (une seule vérification, ex: tâche cron) :
python scripts/orchestrator.py --once
```

---

## 6. Endpoints de l'API HTTP

| Méthode | Route | Description | Code Succès | Code Erreur |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Sonde de vivacité du processus | `200 OK` | - |
| `GET` | `/health/ready` | Sonde de disponibilité (modèle chargé en mémoire) | `200 OK` | `503 Service Unavailable` |
| `POST` | `/predict` | Évaluation en temps réel de l'éligibilité d'une commande | `200 OK` | `422` (invalide), `503` (modèle absent) |

---

## 7. Conteneurisation & Environnements Docker Compose

### 7.1. Environnement de Test (`docker-compose.test.yml`)
Démarre une base PostgreSQL isolée (`livraison_test`), alimentée par l'ERP Simulator, et exécute automatiquement la suite de tests unitaires et d'intégration :
```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
```

### 7.2. Environnement de Production (`docker-compose.prod.yml`)
Déploie l'écosystème complet de production :
- **PostgreSQL 17** avec volume persistant (`livraison_postgres_prod_data`).
- **ERP Simulator** simulant le flux continu des commandes d'entreprise.
- **API FastAPI** (serveur de prédiction en temps réel avec probes de santé).
- **Orchestrateur MLOps** assurant le réentraînement continu et le quality gate automatique.

```bash
# Démarrage de tous les services de production en arrière-plan
docker compose -f docker-compose.prod.yml up -d --build

# Suivi des logs de l'API et de l'orchestrateur
docker compose -f docker-compose.prod.yml logs -f api orchestrator

# Arrêt propre
docker compose -f docker-compose.prod.yml down
```

---

## 8. Tests Automatisés

```bash
pytest tests/ -v
# ou :
python -m unittest discover -s tests -v
```
28 tests unitaires et d'intégration validant 100% des cas sans dépendance externe (mocks `psycopg` et `pymongo`, test client FastAPI, pipeline Scikit-Learn, générateur synthétique et orchestrateur de réentraînement).
