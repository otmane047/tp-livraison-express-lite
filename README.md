# Éligibilité à la Livraison Express - Architecture & Service ML

Projet d'industrialisation et de mise en production d'un modèle de Machine Learning pour l'évaluation en temps réel de l'éligibilité des commandes à la livraison express (**M2 IA dans le Cloud - TP1**).

---

## 1. Présentation du Projet

Ce projet structure le prototype Machine Learning issu du notebook (`notebooks/project_test_v1_final_final2.ipynb`) en une application modulaire et robuste selon les principes de la **Clean Architecture** :
- Séparation stricte entre **entraînement** (job CLI / batch) et **inférence** (API HTTP / CLI).
- Inversion de dépendances (**Repository Pattern**) pour le stockage des commandes (`OrderRepository`) et des artefacts de modèle (`ModelRepository`).
- Configuration externalisée via variables d'environnement (`pydantic-settings`).
- Point d'entrée unique par composition root (`Core`).

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
├── main.py                              # Point d'entrée racine
├── order.json                           # Exemple de payload de commande
├── pyproject.toml                       # Configuration packaging et ruff
├── requirements.txt                     # Dépendances de production
├── requirements-dev.txt                 # Dépendances de développement & tests
└── .env.example                         # Modèle de variables d'environnement
```

---

## 3. Guide de Démarrage Rapide

### 3.1. Installation des dépendances

```bash
# Activation de l'environnement virtuel (sous Windows)
.\.venv\Scripts\activate

# Installation du package en mode éditable avec ses dépendances
pip install -e .
pip install -r requirements-dev.txt
```

### 3.2. Configuration de l'environnement (.env)

```bash
copy .env.example .env
```

Variables configurables :
- `MODEL_PATH` : chemin vers l'artefact `.joblib` (par défaut `notebooks/artifacts/express_delivery_model.joblib`).
- `MODEL_THRESHOLD` : seuil de décision (par défaut `0.5`).
- `LOG_LEVEL` : niveau de log (`INFO`, `DEBUG`...).

---

## 4. Utilisation de la CLI

Le projet expose une interface en ligne de commande complète :

### 4.1. Entraîner le modèle
```bash
python -m livraison_express train
# ou :
python main.py train
```
Cette commande génère le dataset, entraîne le pipeline Scikit-Learn avec tracking MLflow, calcule les métriques et sauvegarde l'artefact `.joblib`, `metrics.json` et `features.json`.

### 4.2. Prédire une commande en local (sans serveur HTTP)
```bash
python -m livraison_express predict --file order.json
# ou :
python main.py predict --file order.json
```
Sortie JSON attendue :
```json
{
  "express_eligible": true,
  "decision": "oui",
  "probability": 0.9377,
  "model_version": "1.0.0",
  "prediction_timestamp": "2026-10-29T08:19:58.124916+00:00"
}
```

### 4.3. Démarrer le serveur API
```bash
python -m livraison_express serve --port 8000
# ou :
python main.py
# ou :
uvicorn main:app --reload
```

---

## 5. Endpoints de l'API HTTP

| Méthode | Route | Description | Code Succès | Code Erreur |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Sonde de vivacité du processus | `200 OK` | - |
| `GET` | `/health/ready` | Sonde de disponibilité (modèle chargé en mémoire) | `200 OK` | `503 Service Unavailable` |
| `POST` | `/predict` | Évaluation en temps réel de l'éligibilité d'une commande | `200 OK` | `422` (invalide), `503` (modèle absent) |

---

## 6. Tests Automatisés

La suite de tests automatisés valide l'ensemble des couches de l'application :

```bash
pytest tests/
# ou :
python -m unittest discover -s tests -v
```
