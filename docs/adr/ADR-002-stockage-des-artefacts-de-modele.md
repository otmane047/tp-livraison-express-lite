# ADR-002 : Stratégie de stockage et gestion des artefacts de modèle Machine Learning

* **Statut** : Accepté
* **Date** : 2026-10-06
* **Projet** : Éligibilité Livraison Express (`eligibilite-livraison-express`)
* **Cadre** : M2 IA dans le Cloud - TP1 (Industrialisation & Architecture MLOps)
* **Décideurs** : Équipe Architecture & MLOps

---

## 1. Contexte et Problématique

L'application d'inférence repose sur un pipeline complet de Machine Learning entraîné avec `scikit-learn` (prétraitement `ColumnTransformer` + imputation + encodage `OneHotEncoder` + normalisation `StandardScaler` + classifieur `LogisticRegression`).

Le cycle de vie du modèle produit et consomme plusieurs artefacts critiques :
1. **Le binaire du modèle** : `express_delivery_model.joblib` (sérialisation de la pipeline scikit-learn complète).
2. **Les métadonnées d'évaluation** : `metrics.json` (`accuracy`, `precision`, `recall`, `f1_score`, `roc_auc`).
3. **Le contrat de features** : `features.json` (colonnes obligatoires numériques et catégorielles).
4. **La Model Card** : exposée par l'endpoint **`GET /v1/model`** (séance 3 du contrat OpenAPI), comprenant la version, la date d'entraînement, les hyperparamètres, les métriques et les limitations opérationnelles.
5. **La sonde de disponibilité** : **`GET /health/ready`**, qui exige la vérification `checks.model: "loaded"`.

### Problématique
Comment stocker, versionner et distribuer les artefacts du modèle afin de :
1. Assurer la **reproductibilité stricte** et l'**immuabilité** des modèles entraînés ?
2. Découpler le cycle de vie du code applicatif (API) du cycle de vie des modèles ML (entraînements fréquents) ?
3. Garantir une **latence d'inférence ultra-faible** sans goulot d'étranglement réseau lors des requêtes HTTP ?
4. Supporter la transition du développement local vers les environnements d'intégration continue (CI/CD) et le déploiement Cloud managé (séances 1 à 7) ?
5. Intégrer de façon native les outils MLOps prévus au cursus (MLflow Tracking et Model Registry, séance 4) ?

---

## 2. Facteurs de Décision (Decision Drivers)

* **Immuabilité et Traçabilité** : Chaque version de modèle (ex. `1.0.0`) doit être figée, auditable et associée à son commit Git, ses données d'entraînement et ses métriques.
* **Découplage Code / Données / Modèle** : Éviter de lier la publication d'un modèle à la recompilation d'une image Docker.
* **Performance d'inférence** : Le modèle doit être préchargé en mémoire vive du serveur au démarrage de l'API (latence de prédiction < 10 ms).
* **Indépendance d'infrastructure (Stateless API)** : L'API d'inférence doit pouvoir être déployée sous forme de conteneurs stateless auto-scalables (Kubernetes, AWS ECS, Google Cloud Run).
* **Facilité d'expérimentation locale** : Permettre d'exécuter et tester le projet sans abonnement cloud payant ni connexion internet obligatoire en phase de TP initial.
* **Gouvernance MLOps** : Capacité à gérer les stades de promotion (`Staging`, `Production`, `Archived`) et les rollbacks instantanés.

---

## 3. Options Considérées

| Option | Description | Avantages | Inconvénients / Limites |
| :--- | :--- | :--- | :--- |
| **Option 1 : Binaire embarqué dans l'image Docker ("Baked-in Model")** | Le fichier `.joblib` est copié directement dans l'image Docker (`COPY artifacts/ /app/artifacts/`). | • Image totalement autonome et portable<br>• Démarrage ultra-rapide sans appel externe<br>• Aucune dépendance réseau au boot | • **Anti-pattern MLOps** : couple le cycle de vie du modèle et du code<br>• Nécessite de rebuilder, scanner et redéployer toute l'image Docker à chaque réentraînement<br>• Gonfle la taille des registres Docker |
| **Option 2 : Dépôt Git / Git LFS** | Les artefacts `.joblib` et `.json` sont versionnés directement dans Git avec Git LFS. | • Versionné avec le code source<br>• Pas d'infrastructure dédiée | • Git n'est pas conçu pour les binaires volumineux et fréquents<br>• Absence de métadonnées MLOps (stades de modèle, métriques comparatives)<br>• Clones de dépôts lents |
| **Option 3 : Volume persistant partagé (NFS, AWS EFS, PVC Kubernetes)** | Les conteneurs montent un volume réseau partagé contenant le dossier `artifacts/`. | • Mise à jour du fichier sur le disque partagé immédiatement visible | • SPOF (Single Point of Failure) d'infrastructure<br>• Latence d'I/O réseau imprévisible<br>• Verrous de fichiers complexes et gestion des droits délicate<br>• Difficilement portable en local |
| **Option 4 : Stockage Objet Cloud (AWS S3, GCP Cloud Storage, MinIO local)** | Les artefacts sont stockés dans des compartiments (*buckets*) versionnés avec chemin préfixé : `s3://bucket/models/{version}/`. | • Standard mondial du Cloud<br>• Disponibilité 99.99%, immuabilité native (*S3 Object Lock* / versioning)<br>• Coût extrêmement faible<br>• Émulation locale parfaite via **MinIO**<br>• Stateless pour les conteneurs | • Nécessite une étape de téléchargement au démarrage du conteneur API<br>• Ne fournit pas d'interface de comparaison graphique des métriques sans outil tiers |
| **Option 5 : MLflow Model Registry adossé à un Stockage Objet (S3/GCS)** | MLflow gère le registre centralisé, les métadonnées et le cycle de vie ; les artefacts physiques reposent dans un bucket S3. | • Solution MLOps de référence de l'industrie<br>• Traçabilité complète (runs, hyperparamètres, métriques)<br>• Gestion des alias et tags (`champion`, `challenger`, `Production`)<br>• Alignement parfait avec la séance 4 du TP | • Nécessite un serveur MLflow Tracking opérationnel en production |

---

## 4. Décision Retenue

Nous retenons l'**Option 5 (MLflow Model Registry adossé à un Stockage Objet compatible S3)**, orchestrée via une **architecture de stockage à deux niveaux découplée par une interface `ModelArtifactStore`** :

```
[ Entraînement / CI/CD ]
         │
         ├──> Log run, métriques & modèle ──> [ MLflow Tracking Server ]
         └──> Dépôt physique de l'artefact ──> [ Stockage Objet (S3 / MinIO) ]
                                                            │
                                                            │ (Download au boot)
                                                            ▼
                                                [ API FastAPI (Stateless) ]
                                                • In-Memory Cache (RAM)
                                                • Sonde /health/ready : OK
                                                • Endpoint /v1/model : OK
```

### Justification de la décision :
1. **Découplage strict Code vs Modèle** : Le conteneur Docker de l'API reste générique et léger. Il télécharge la version du modèle ciblée (définie par variable d'environnement `MODEL_VERSION` ou tag MLflow `Production`) lors de son initialisation.
2. **Zéro latence en phase d'inférence** : Le modèle est téléchargé **une seule fois** au démarrage via le gestionnaire de cycle de vie FastAPI (`lifespan`), puis instancié en mémoire vive sous forme de Singleton. Les prédictions `/v1/predictions` sont traitées en mémoire (latence < 1 ms) sans jamais interroger le stockage distant.
3. **Protection par la sonde de disponibilité (`/health/ready`)** : Si le stockage objet est inaccessible ou si le fichier est corrompu, le modèle n'est pas chargé : l'API répond `503 Service Unavailable` sur `/health/ready`, et l'orchestrateur ne route aucun trafic vers ce nœud.
4. **Stratégie progressive par environnement** :
   * **En développement local (Séance 1 & 2)** : Le store utilise l'implémentation `LocalModelArtifactStore` pointant sur le dossier local `artifacts/` (déjà présent dans le code).
   * **En test d'intégration & CI** : Utilisation d'un conteneur léger **MinIO** compatible avec l'API AWS S3.
   * **En production Cloud (Séances 3 à 7)** : Connexion directe à un bucket sécurisé **AWS S3** ou **GCP Cloud Storage**, synchronisé avec le **MLflow Model Registry**.

---

## 5. Spécifications Techniques et Implémentation

### 5.1. Structure d'organisation des artefacts dans le Bucket S3

Les artefacts respectent une arborescence immuable et sémantiquement versionnée :

```text
s3://livraison-express-ml-artifacts/
└── models/
    ├── v1.0.0/
    │   ├── express_delivery_model.joblib   # Pipeline sérialisée
    │   ├── metrics.json                    # Métriques d'évaluation
    │   ├── features.json                   # Définition des variables d'entrée
    │   └── model_card.json                 # Métadonnées complètes OpenAPI /v1/model
    └── v1.1.0/
        ├── express_delivery_model.joblib
        ├── metrics.json
        ├── features.json
        └── model_card.json
```

### 5.2. Interface Abstraite `ModelArtifactStore`

Pour respecter le principe d'Inversion de Dépendance (DIP - SOLID) :

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.pipeline import Pipeline

class ModelArtifactStore(ABC):
    """Interface d'accès aux artefacts de modèle ML."""

    @abstractmethod
    def load_model(self, version: str) -> Pipeline:
        """Charge la pipeline de modèle en mémoire."""
        pass

    @abstractmethod
    def load_metadata(self, version: str) -> Dict[str, Any]:
        """Charge les métadonnées (model_card.json / metrics.json)."""
        pass

    @abstractmethod
    def save_artifacts(
        self,
        version: str,
        model_pipeline: Pipeline,
        metrics: Dict[str, float],
        model_card: Dict[str, Any],
    ) -> None:
        """Sauvegarde l'ensemble des artefacts pour une version donnée."""
        pass
```

### 5.3. Cycle de Vie FastAPI (`lifespan`) et Cache Mémoire

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.local_model_store import LocalModelArtifactStore

# État partagé en mémoire vive (Singleton)
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Démarrage : chargement unique du modèle ──────────────────────
    store = get_model_artifact_store()
    try:
        app_state["model"] = store.load_model(version=MODEL_VERSION)
        app_state["model_card"] = store.load_metadata(version=MODEL_VERSION)
        app_state["model_loaded"] = True
    except Exception as e:
        app_state["model_loaded"] = False
        app_state["load_error"] = str(e)
    
    yield
    
    # ── Arrêt : nettoyage des ressources ─────────────────────────────
    app_state.clear()

app = FastAPI(lifespan=lifespan)
```

---

## 6. Conséquences

### Positives
* **Immuabilité garantie** : Une fois poussée avec son numéro de version, une archive de modèle n'est jamais écrasée.
* **Mise à l'échelle horizontale fluide** : 10 ou 100 réplicas de l'API peuvent démarrer simultanément et télécharger la même version de modèle depuis le stockage objet.
* **Rollback instantané** : Revenir à la version précédente `1.0.0` ne nécessite aucun redéploiement d'image Docker, simplement la mise à jour de la variable `MODEL_VERSION=1.0.0`.
* **Conformité stricte OpenAPI** : L'endpoint `GET /v1/model` est alimenté directement par `model_card.json` stocké aux côtés du modèle.

### Négatives / Compromis
* **Temps de démarrage à froid (*Cold Start*)** : Le téléchargement du fichier `.joblib` ajoute quelques secondes au boot du conteneur (atténué par la taille modeste du modèle scikit-learn, < 10 Mo).
* **Dépendance réseau au démarrage** : L'accès au bucket S3 / MinIO doit être opérationnel au démarrage de l'API.

---

## 7. Feuille de Route d'Évolution (Par Séance)

* **Séance 1 (Initialisation)** : Sauvegarde locale dans `artifacts/` via `joblib.dump()` et `json.dump()`, lecture au démarrage de l'API.
* **Séance 2 (Déploiement Docker)** : Externalisation du chargement d'artefacts (volume monté ou téléchargement S3).
* **Séance 3 (Model Card & CI/CD)** : Automatisation de la génération de `model_card.json` exposée sur `GET /v1/model`.
* **Séance 4 (MLflow)** : Enregistrement automatique des artefacts dans MLflow Tracking et enregistrement dans le Model Registry (`mlflow.sklearn.log_model`).
* **Séance 5 (Batch)** : Réutilisation du modèle stocké pour exécuter les prédictions batch massives sur `POST /v1/predictions/batch`.
* **Séance 7 (Observabilité & Drift)** : Comparaison des prédictions réelles avec la distribution de référence stockée dans les métadonnées d'artefact.
