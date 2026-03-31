# 🧹 Sonar Cleaner

Utilitaire de nettoyage des branches et MR issues du **community branch plugin** qui ne sont pas supportées par les fonctions de housekeeping natives de sonar. 

- Nettoies les branches inactives depuis n jours,
- Supprime les MR inactives depuis n jours.

Une branche ou MR est considérée comme inactive si elle n'a pas été sujette à une analyse sonar depuis n jours.

---

## 🚀 Installation rapide

Cet outil nécessite [uv](https://github.com/astral-sh/uv). Si vous ne l'avez pas : `pip install uv` (ou via l'installeur officiel).


1.  **Préparer l'environnement** :
    ```bash
    uv sync
    ```

---

## ⚙️ Configuration

La configuration est gérée dans un `.env` à la racine :

```text
# URL de l'instance SonarQube
SONAR_URL=[https://sonar-kube.developpement.insee.fr](https://sonar-kube.developpement.insee.fr)

# Votre Token d'accès (Généré dans Sonar > Mon Compte > Sécurité)
SONAR_TOKEN=votre_token_ici

# Clé du projet cible
PROJECT_KEY=mon_projet_id

# Seuil d'inactivité en jours (30 par défaut)
DAYS_LIMIT=30
```

## 📖 Exécution

Pour lancer le scirpt :
```
uv run src/cleaner.py
```

## 🛡️ Branches protégées

Les branches **main**, **master**, **develop**, **release** ne sont pas supprimées.

## 🔍 Logs

- 🛡️ Ignorée : Branche protégée.
- ✨ Conservée : Analyse récente (inférieure à DAYS_LIMIT).
- ⏳ Inactive : Seuil d'inactivité dépassé, suppression déclenchée.
- ✅ Supprimée : Confirmation de la suppression par le serveur Sonar.

## 🛠️ Structure du projet
```
sonar-cleaner/
├── src/
│   └── cleaner.py    # Script principal
├── .env              # Configuration (exclu de Git)
├── pyproject.toml    # Dépendances
└── uv.lock           # Versions figées des dépendances
```


