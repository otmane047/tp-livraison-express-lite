# Registre des Décisions d'Architecture (Architecture Decision Records - ADR)

Ce répertoire contient l'ensemble des **Architecture Decision Records (ADR)** pour le projet **`livraison-express-lite`** (M2 IA dans le Cloud - TP1).

Les ADR documentent les choix techniques structurants, les contextes de décision, les alternatives évaluées et les conséquences opérationnelles pour assurer la pérennité, la sécurité et la scalabilité de l'architecture logicielle et MLOps.

---

## Index des Décisions

| Identifiant | Titre | Statut | Date | Portée / Thématique |
| :--- | :--- | :--- | :--- | :--- |
| [**ADR-001**](file:///./ADR-001-stockage-des-commandes.md) | Stratégie de stockage et persistance des commandes (Order Store) | **Accepté** | 2026-10-06 | Base de données SQL (SQLite / PostgreSQL), Repository Pattern, OpenAPI `/v1/orders` |
| [**ADR-002**](file:///./ADR-002-stockage-des-artefacts-de-modele.md) | Stratégie de stockage et gestion des artefacts de modèle Machine Learning | **Accepté** | 2026-10-06 | Stockage Objet Cloud (S3 / MinIO), In-Memory Caching au démarrage, OpenAPI `/v1/model` |
| [**ADR-003**](file:///./ADR-003-plateforme-de-deploiement-et-services-cloud.md) | Plateforme d'hébergement et services Cloud pour la mise en production | **Accepté** | 2026-10-29 | Cloud vs On-Premise vs Local, Serverless Containers (Cloud Run / ECS), Services managés |
| [**ADR-004**](file:///./ADR-004-strategie-de-deploiement-et-cycle-de-vie.md) | Stratégie de déploiement et cycle de vie des modèles ML | **Accepté** | 2026-10-29 | Déploiement Canary & Blue/Green, Sondes liveness/readiness, Auto-rollback sur dérive |
| [**ADR-005**](file:///./ADR-005-securisation-des-flux-et-protection-des-donnees.md) | Sécurisation des flux d'entrées/sorties et protection des accès aux données | **Accepté** | 2026-10-29 | TLS 1.3, Auth, Validation Pydantic, Moindre privilège IAM, Chiffrement KMS, VPC privé |

---

## Format d'un ADR

Chaque enregistrement suit le standard international MADR (*Markdown Architectural Decision Records*) et comprend les sections suivantes :
1. **Contexte et Problématique** : Description du besoin métier, des contraintes d'API et des objectifs techniques.
2. **Facteurs de Décision** : Critères d'évaluation clés (performance, sécurité, portabilité, coût, principes SOLID/YAGNI).
3. **Options Considérées** : Tableau comparatif objectif des solutions techniques envisageables avec leurs avantages et inconvénients.
4. **Décision Retenue** : Solution adoptée et argumentation détaillée avec schéma Mermaid d'architecture.
5. **Architecture Technique & Implémentation** : Déclinaisons pratiques, cartographie de services et interfaces.
6. **Conséquences** : Bilan des impacts positifs et des compromis (*trade-offs*) acceptés.
