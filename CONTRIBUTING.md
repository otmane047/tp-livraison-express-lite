# Guide de Contribution (Contributing Guidelines)

Merci de contribuer au projet **Éligibilité Livraison Express** (`livraison-express-lite`) !

Ce document présente les règles et bonnes pratiques pour maintenir un code robuste, testé et respectant les standards professionnels.

---

## 1. Modèle de Branches Git : GitFlow

Le projet suit rigoureusement la méthodologie **GitFlow** :

```text
main (production) ─────────────────────────● (v1.0.0) ───────────────● (v1.1.0)
                                           ▲                         ▲
develop (intégration) ────●──────●─────────┴──────────●──────●───────┘
                           \    /                      \    /
feature/*                   └──●                        └──●
```

### Branches permanentes
- **`main`** : Branche stable de production. Tout commit sur `main` correspond à une version publiable et taguée (`vX.Y.Z`).
- **`develop`** : Branche principale d'intégration. Elle regroupe les fonctionnalités validées avant la publication en production.

### Branches temporaires
- **`feature/<nom-fonctionnalite>`** : Issue de `develop`, fusionnée dans `develop` via Pull Request (PR) après validation des tests.
- **`release/<version>`** : Issue de `develop` pour préparer une nouvelle version (stabilisation, bump de version), fusionnée dans `main` et `develop`.
- **`hotfix/<nom-correctif>`** : Issue de `main` en cas de bug critique en production, fusionnée dans `main` et `develop`.

---

## 2. Convention de Messages de Commit

Les commits doivent suivre la spécification [Conventional Commits](https://www.conventionalcommits.org/) :

```text
<type>(<portée optionnelle>): <description courte et impérative>
```

### Types autorisés :
* **`feat`** : Nouvelle fonctionnalité
* **`fix`** : Correction de bug
* **`docs`** : Modification de la documentation (README, ADR...)
* **`refactor`** : Refactorisation de code sans modification de comportement
* **`test`** : Ajout ou mise à jour de tests
* **`chore`** : Tâches de maintenance, dépendances, configuration

*Exemples :*
- `feat(api): ajouter le support du batch de prédictions`
- `fix(model): corriger la gestion des valeurs manquantes dans le scaler`
- `docs(adr): rédiger ADR-003 sur l'hébergement cloud`

---

## 3. Environnement de Développement Local

### Installation
```bash
# Cloner le dépôt et se placer sur develop
git clone git@github.com:otmane047/tp-livraison-express-lite.git
cd tp-livraison-express-lite
git checkout develop

# Créer et activer l'environnement virtuel
python -m venv .venv
.\.venv\Scripts\activate

# Installer les dépendances en mode éditable et outils de dev
pip install -e .
pip install -r requirements-dev.txt
```

---

## 4. Qualité du Code & Validation Avant Commit

Avant de soumettre une Pull Request, assurez-vous que tous les contrôles passent localement :

### 1. Formatage et Linting (Ruff)
```bash
ruff check .
```

### 2. Tests unitaires et couverture (Pytest)
```bash
pytest --cov=livraison_express_lite tests/
```
> **Exigence :** Aucun test ne doit échouer et la couverture de code doit rester supérieure ou égale à 75%.

---

## 5. Processus de Pull Request (PR)

1. Créez votre branche depuis `develop` : `git checkout -b feature/ma-fonctionnalite develop`
2. Développez et ajoutez les tests correspondants dans `tests/`.
3. Vérifiez la conformité locale (`ruff` + `pytest`).
4. Poussez votre branche : `git push -u origin feature/ma-fonctionnalite`
5. Ouvrez une **Pull Request vers `develop`** sur GitHub.
6. Le pipeline CI exécutera automatiquement la suite de tests et le linter. Une fois validée par un pair, la PR sera fusionnée.

