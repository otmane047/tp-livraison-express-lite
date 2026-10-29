# Politique de Sécurité (Security Policy)

La sécurité de notre application de Machine Learning et la protection des données de nos utilisateurs sont des priorités absolues.

---

## 1. Versions Supportées

Les mises à jour de sécurité et correctifs sont activement déployés sur les versions suivantes :

| Version | Supportée | Statut |
| :--- | :--- | :--- |
| `1.0.x` | ✅ Oui | Version courante de production |
| `< 1.0` | ❌ Non | Versions expérimentales obsolètes |

---

## 2. Signalement d'une Vulnérabilité

Si vous découvrez une faille de sécurité potentielle dans ce projet :

1. **Ne pas ouvrir d'issue publique** sur GitHub afin de protéger les utilisateurs tant que la vulnérabilité n'est pas corrigée (*Coordinated Vulnerability Disclosure*).
2. Contactez directement les mainteneurs par email à : **`otmane047@gmail.com`** en indiquant :
   - Le composant affecté (API, Pipeline ML, conteneur Docker, base de données).
   - Une description détaillée de la vulnérabilité.
   - Les étapes ou un script de preuve de concept (*Proof of Concept* - PoC) permettant de reproduire le problème.
   - L'impact potentiel estimé (DoS, fuite de données, exécution de code arbitraire).

---

## 3. Délais de Prise en Charge

- **Accusé de réception** : Sous **48 heures ouvrées**.
- **Évaluation et qualification** : Sous **5 jours ouvrés**.
- **Publication du correctif (Hotfix)** : Déployé en priorité selon le workflow GitFlow avec publication d'une nouvelle release mineure.

---

## 4. Bonnes Pratiques Appliquées au Projet

- **Zéro clé statique** : Aucun mot de passe ni clé d'API n'est stocké dans le dépôt (contrôle via Secret Manager et variables d'environnement).
- **Conteneurs non-root** : L'image Docker s'exécute avec un utilisateur restreint (`appuser:1000`).
- **Validation stricte** : Rejet automatique des charges utiles malveillantes via Pydantic et HTTPS TLS 1.3 obligatoire.

