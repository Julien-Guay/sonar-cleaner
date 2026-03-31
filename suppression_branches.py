import os
import sys
import logging
import requests
import urllib3
from datetime import datetime, timezone

# --- CONFIGURATION SSL (NO VERIFY) ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
SONAR_URL = os.getenv("SONAR_URL", "https://sonar-kube.developpement.insee.fr")
SONAR_TOKEN = "squ_d60268a17d676ac294300bf600bd6fbb326c9965"
PROJECT_KEY = "conjoncture2"
DAYS_LIMIT = 30
PROTECTED_BRANCHES = ["main", "master", "develop", "release"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

def delete_item(session, item_id, is_mr=True):
    """Supprime une MR ou une Branche"""
    if is_mr:
        url = f"{SONAR_URL}/api/project_pull_requests/delete"
        params = {"project": PROJECT_KEY, "pullRequest": item_id}
        label = f"MR {item_id}"
    else:
        url = f"{SONAR_URL}/api/project_branches/delete"
        params = {"project": PROJECT_KEY, "branch": item_id}
        label = f"Branche {item_id}"

    try:
        res = session.post(url, params=params, verify=False)
        if res.status_code == 204:
            logger.info(f" ✅ {label} supprimée avec succès.")
            return True
        else:
            logger.error(f" ❌ Échec {label} (Code: {res.status_code})")
            return False
    except Exception as e:
        logger.error(f" ❌ Erreur lors de la suppression de {label}: {e}")
        return False

def clean_sonar():
    session = requests.Session()
    session.auth = (SONAR_TOKEN, "")
    now = datetime.now(timezone.utc)

    # --- 1. NETTOYAGE DES MR ---
    logger.info(f"🚀 --- Nettoyage des Merge Requests ---")
    try:
        resp_mr = session.get(f"{SONAR_URL}/api/project_pull_requests/list", params={"project": PROJECT_KEY}, verify=False)
        resp_mr.raise_for_status()
        for mr in resp_mr.json().get("pullRequests", []):
            mr_id = mr.get("key")
            date_str = mr.get("analysisDate")
            
            if not date_str:
                delete_item(session, mr_id, is_mr=True)
                continue
                
            age = (now - datetime.fromisoformat(date_str.replace("Z", "+00:00"))).days
            if age > DAYS_LIMIT:
                logger.info(f" ⏳ MR {mr_id} inactive ({age}j).")
                delete_item(session, mr_id, is_mr=True)
    except Exception as e:
        logger.error(f"Erreur MR: {e}")

    # --- 2. NETTOYAGE DES BRANCHES ---
    logger.info(f"🚀 --- Nettoyage des Branches ---")
    try:
        resp_br = session.get(f"{SONAR_URL}/api/project_branches/list", params={"project": PROJECT_KEY}, verify=False)
        resp_br.raise_for_status()
        for br in resp_br.json().get("branches", []):
            name = br.get("name")
            is_main = br.get("isMain", False)
            date_str = br.get("analysisDate")

            if is_main or name in PROTECTED_BRANCHES:
                logger.info(f" 🛡️ Branche {name} protégée. Passage.")
                continue

            if not date_str:
                delete_item(session, name, is_mr=False)
                continue

            age = (now - datetime.fromisoformat(date_str.replace("Z", "+00:00"))).days
            if age > DAYS_LIMIT:
                logger.info(f" ⏳ Branche {name} inactive ({age}j).")
                delete_item(session, name, is_mr=False)
            else:
                logger.info(f" ✨ Branche {name} active ({age}j).")

    except Exception as e:
        logger.error(f"Erreur Branches: {e}")

if __name__ == "__main__":
    clean_sonar()