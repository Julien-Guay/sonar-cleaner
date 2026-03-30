
import os
import sys
import logging
import requests
from datetime import datetime, timezone

# --- CONFIGURATION ---
# On récupère les infos via l'environnement pour la sécurité
SONAR_URL = os.getenv("SONAR_URL", "https://sonar-kube.developpement.insee.fr")
SONAR_TOKEN = "squ_d60268a17d676ac294300bf600bd6fbb326c9965"
PROJECT_KEY = "conjoncture2"
DAYS_LIMIT = 30

# Configuration du logging (Sortie standard avec couleurs simples)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

def clean_mrs():
    if not SONAR_TOKEN:
        logger.error("Variable d'environnement SONAR_TOKEN manquante.")
        sys.exit(1)

    session = requests.Session()
    # Le token Sonar s'utilise comme 'username' avec un mot de passe vide
    session.auth = (SONAR_TOKEN, "")
    
    logger.info(f"🚀 Début du scan pour {PROJECT_KEY} sur {SONAR_URL}")

    try:
        # 1. Récupérer la liste des MR
        response = session.get(f"{SONAR_URL}/api/project_pull_requests/list", params={"project": PROJECT_KEY})
        response.raise_for_status()
        mrs = response.json().get("pullRequests", [])

        if not mrs:
            logger.info("✅ Aucune MR trouvée.")
            return

        now = datetime.now(timezone.utc)
        deleted_count = 0

        for mr in mrs:
            mr_id = mr.get("key")
            branch = mr.get("branch", "n/a")
            analysis_date_str = mr.get("analysisDate")

            # Cas d'une MR sans analyse (fantôme)
            if not analysis_date_str:
                logger.warning(f"MR {mr_id} [{branch}] : Aucune analyse. Suppression...")
                delete_mr(session, mr_id)
                deleted_count += 1
                continue

            # Parsing de la date (Python 3.7+ gère bien l'ISO8601 avec fromisoformat)
            # On remplace le Z par +00:00 si présent pour la compatibilité
            analysis_date = datetime.fromisoformat(analysis_date_str.replace("Z", "+00:00"))
            
            # Calcul de l'âge
            age_days = (now - analysis_date).days

            if age_days > DAYS_LIMIT:
                logger.info(f"🗑️ MR {mr_id} [{branch}] : Inactive depuis {age_days} jours. Suppression...")
                if delete_mr(session, mr_id):
                    deleted_count += 1
            else:
                logger.info(f"✨ MR {mr_id} [{branch}] : Active ({age_days} jours).")

        logger.info(f"🏁 Terminé. {deleted_count} MR(s) supprimée(s).")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur réseau ou API : {e}")
        sys.exit(1)

def delete_mr(session, mr_id):
    """Effectue l'appel de suppression"""
    url = f"{SONAR_URL}/api/project_pull_requests/delete"
    res = session.post(url, params={"project": PROJECT_KEY, "pullRequest": mr_id})
    if res.status_code == 204:
        slogger.info(f" ✅ MR {mr_id} supprimée avec succès sur Sonar.")
        return True
    else:
        logger.error(f"❌ Échec suppression MR {mr_id} (Code: {res.status_code})")
        return False

if __name__ == "__main__":
    clean_mrs()