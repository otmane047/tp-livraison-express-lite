# ADR-006 : Choix du SGBD pour l'intégration des commandes ERP (PostgreSQL vs MongoDB)

* **Statut** : Accepté
* **Date** : 2026-10-29
* **Projet** : Éligibilité Livraison Express (`livraison-express-lite`)
* **Cadre** : M2 IA dans le Cloud - TP1 & TP4 (Intégration de données ERP & MLOps)
* **Décideurs** : Équipe Architecture & MLOps

---

## 1. Contexte et Problématique

Dans le cadre de l'industrialisation du service d'éligibilité à la livraison express, notre application doit ingérer les commandes provenant du système ERP (`ERP Pro 2015`). Les retours d'expérience transmis par les développeurs et l'équipe d'infrastructure révèlent une situation organisationnelle et technique singulière :

```mermaid
flowchart LR
    ERP["ERP Pro 2015"] <-->|Échange bilatéral<br/>temps réel logiciel| PG[("PostgreSQL<br/>(Base de production)")]
    PG -->|Échange unilatéral<br/>temps réel ETL| Mongo[("MongoDB<br/>(Base analytique)")]
    
    subgraph "Systèmes de Données Existants"
        PG
        Mongo
    end
```

### État des lieux des deux bases de données :

1. **PostgreSQL (Base de production transactionnelle OLTP)** :
   * Première base de données développée pour le système, existant depuis **2015**.
   * Schéma modifié successivement en **2017** (ajout du temps de préparation `preparation_time_min`) et en **2023**.
   * Base non mise à jour depuis 2023 suite à la démission de l'administrateur de base de données (DBA), non remplacé à ce jour.
   * **Contrainte critique** : Elle est activement partagée et requêtée par une **autre application métier critique** pour l'entreprise.

2. **MongoDB (Base analytique OLAP / Data Analysts)** :
   * Montée en **2023** pour isoler les requêtes exploratoires des Data Analysts afin d'éviter qu'ils ne surchargent ou ne « cassent » la base de production PostgreSQL.
   * Alimentée par un pipeline ETL unilatéral temps réel depuis PostgreSQL.
   * **Limite majeure** : L'historique des années précédentes (**2015-2022**) n'a **pas** été migré vers MongoDB. Seules les données depuis 2023 y sont présentes.
   * **Risque de gouvernance** : Elle est actuellement maintenue par un **alternant arrivant bientôt en fin de contrat**, posant un risque à moyen terme sur la maintenance de l'ETL.

---

## 2. Facteurs de Décision (Decision Drivers)

* **Volume et profondeur de l'historique d'entraînement ML** : Un modèle supervisé de classification requiert un volume représentatif couvrant la saisonnalité et les cas extrêmes (10 ans vs 2 ans).
* **Impact sur la production et l'application critique** : Éviter les verrous de table et la saturation CPU/I-O lors des extractions massives pour l'entraînement.
* **Gouvernance, résilience et pérennité opérationnelle** : Dépendance vis-à-vis du départ imminent de l'alternant maintenant MongoDB et l'absence de DBA sur PostgreSQL.
* **Typage et qualité des données** : Présence de schémas stricts vs documents flexibles, gestion des évolutions passées (valeurs nulles historiques).
* **Respect des principes SOLID (Inversion de Dépendance - DIP)** : L'architecture applicative doit découpler le code métier du choix du moteur sous-jacent.

---

## 3. Analyse Comparative des Options

| Critère d'évaluation | Option A : PostgreSQL (Production) | Option B : MongoDB (Analytique) |
| :--- | :--- | :--- |
| **Profondeur historique** | **10 ans (2015-présent)** : Données exhaustives avec historique long. | **2 ans (2023-présent)** : 8 années de données historiques manquantes. |
| **Rôle dans l'entreprise** | Base de production partagée avec une application critique. | Base analytique dédiée aux Data Analysts. |
| **Risque d'impact système** | Risque d'impact sur l'application critique en cas d'extraction non maîtrisée. | **Nul** sur la production applicative (base isolée). |
| **Maintenance humaine** | Pas de DBA actif depuis 2023 (mais moteur PostgreSQL standard et mature). | Maintenue par un alternant en fin de contrat (risque sur le flux ETL). |
| **Structure des données** | Schéma relationnel typé (`INTEGER`, `DOUBLE PRECISION`, `TEXT`). | BSON semi-structuré, validation flexible. |
| **Gestion des flux récents** | Écriture bilatérale temps réel depuis l'ERP. | Alimentation temps réel asynchrone par ETL unilatéral. |
| **Complexité d'intégration** | Requêtes SQL optimisées avec index (`order_date`, `order_id`). | Requêtes d'agrégation MongoDB / BSON decoding. |

---

## 4. Décision Retenue

Nous retenons **PostgreSQL** comme source de données primaire pour notre application de livraison express, tout en concevant un **système hybride et résilient grâce au Repository Pattern** :

1. **Choix primaire : PostgreSQL via [`PostgresOrderRepository`](file:///d:/Cours/m2/IA%20dans%20le%20cloud/tp1/src/livraison_express_lite/infrastructure/implementation/postgres_order_repository.py)** :
   * **Justification métier** : L'accès aux 10 années de données historiques (2015-présent) est indispensable pour entraîner un modèle de Machine Learning performant et capable de généraliser sur toutes les saisons et zones géographiques.
   * **Contournement du risque de charge** : Les requêtes d'extraction pour le réentraînement sont bornées (`max_rows=10000`, absence de verrous bloquants `NOLOCK` / lecture non bloquante par défaut en MVCC PostgreSQL).
   * **Pérennité** : PostgreSQL est nativement géré et ne dépend pas du script ETL de l'alternant susceptible de tomber en désuétude à son départ.

2. **Mesure de secours et de découplage : Double implémentation SOLID (DIP)** :
   * Conformément aux principes de Clean Architecture, nous avons également développé [`MongoOrderRepository`](file:///d:/Cours/m2/IA%20dans%20le%20cloud/tp1/src/livraison_express_lite/infrastructure/implementation/mongo_order_repository.py).
   * La factory [`Core`](file:///d:/Cours/m2/IA%20dans%20le%20cloud/tp1/src/livraison_express_lite/core/core.py) instancie automatiquement le repository adéquat selon la variable d'environnement `ORDER_REPOSITORY_URL` :
     * `postgresql://livraison:livraison@localhost:5432/livraison_express` (Recommandé)
     * `mongodb://localhost:27017` (Bascule immédiate si l'application critique subit une saturation)

```mermaid
flowchart TD
    subgraph "Sources Externes"
        PG[(PostgreSQL - Prod 2015+)]
        ETL[Pipeline ETL]
        Mongo[(MongoDB - Analytics 2023+)]
        PG -->|ETL unilatéral| ETL --> Mongo
    end

    subgraph "Application livraison-express-lite"
        DIP["Interface Abstraite : OrderRepository"]
        
        ImplPG["PostgresOrderRepository<br/>(Choix Principal : Historique 10 ans)"]
        ImplMongo["MongoOrderRepository<br/>(Choix Secours : Zéro impact Prod)"]
        
        DIP --- ImplPG
        DIP --- ImplMongo
        
        ImplPG -->|Connexion| PG
        ImplMongo -->|Connexion| Mongo
        
        AppCore["Core (Factory Singleton)"] --> DIP
        API["API FastAPI /predict"] --> AppCore
        Train["Orchestrateur ML / Retrain"] --> AppCore
    end
```

---

## 5. Gestion des Migrations Historiques dans le Code

L'historique PostgreSQL contenant les évolutions de schéma de 2015 et 2017, la classe `PostgresOrderRepository` encapsule la logique d'adaptation sans corrompre le domaine métier :

* **Colonne `weekend` (NULL avant juillet 2015)** : Dérivée automatiquement à la volée via la formule métier `day_of_week >= 5`.
* **Colonne `preparation_time_min` (NULL avant juillet 2017)** : Imputée par la médiane métier (`25.0 min`) ou prise en charge directement par le `SimpleImputer` du pipeline Scikit-Learn.

---

## 6. Conséquences

### Positives :
* **Qualité de l'IA** : Volume d'entraînement maximal (10 ans de données réelles).
* **Indépendance vis-à-vis du départ de l'alternant** : Pas de dépendance critique envers la maintenance du flux ETL vers MongoDB.
* **Agilité architecturale** : Bascule possible vers MongoDB en 0 seconde via simple changement de configuration d'environnement, sans recompilation ni modification de code.

### Compromis acceptés et surveillances :
* **Surveillance de la charge** : L'orchestrateur de réentraînement planifie ses cycles d'apprentissage avec modération (`MIN_NEW_ORDERS=50`, requêtes en lecture seule `SELECT`) pour préserver les performances de l'autre application critique partageant PostgreSQL.
