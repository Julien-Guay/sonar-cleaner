import os
import sys
import logging
import requests
import urllib3
from datetime import datetime, timezone
from dotenv import load_dotenv

# --- INITIALISATION ---
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
URL = os.getenv("SONAR_URL", "https://sonar-kube.developpement.insee.fr")
TOKEN = os.getenv("SONAR_TOKEN")
PROJECT = os.getenv("PROJECT_KEY", "conjoncture2")
DAYS = int(os.getenv("DAYS_LIMIT", 30))
PROTECTED = ["main", "master", "develop", "release"]

def delete_item(session, item_id, is_mr=True):
    endpoint = "project_pull_requests" if is_mr else "project_branches"
    param_key = "pullRequest" if is_mr else "branch"
    url = f"{URL}/api/{endpoint}/delete"
    
    try:
        res = session.post(url, params={"project": PROJECT, param_key: item_id}, verify=False)
        if res.status_code == 204:
            logger.info(f"  ✅ {'MR' if is_mr else 'Branche'} {item_id} supprimée.")
            return True
        logger.error(f"  ❌ Échec {item_id} (Code: {res.status_code})")
    except Exception as e:
        logger.error(f"  ❌ Erreur sur {item_id}: {e}")
    return False

def run_clean():
    if not TOKEN:
        logger.error("SONAR_TOKEN manquant dans le .env")
        return

    session = requests.Session()
    session.auth = (TOKEN, "")
    now = datetime.now(timezone.utc)

    # --- 1. SCAN DES MR ---
    logger.info(f"🚀 Scan des Merge Requests pour {PROJECT}...")
    try:
        r_mr = session.get(f"{URL}/api/project_pull_requests/list", params={"project": PROJECT}, verify=False)
        r_mr.raise_for_status()
        mrs = r_mr.json().get("pullRequests", [])
        
        for mr in mrs:
            mid = mr['key']
            branch_ref = mr.get('branch', 'n/a')
            date_str = mr.get("analysisDate")
            
            if not date_str:
                logger.warning(f"  ⚠️ MR {mid} [{branch_ref}] : Aucune analyse trouvée. Suppression...")
                delete_item(session, mid, is_mr=True)
                continue
                
            age = (now - datetime.fromisoformat(date_str.replace("Z", "+00:00"))).days
            if age > DAYS:
                logger.info(f"  ⏳ MR {mid} [{branch_ref}] : Inactive ({age}j).")
                delete_item(session, mid, is_mr=True)
            else:
                logger.info(f"  ✨ MR {mid} [{branch_ref}] : Conservée (Active depuis {age}j).")
    except Exception as e:
        logger.error(f"Erreur lors du scan des MR: {e}")

    # --- 2. SCAN DES BRANCHES ---
    logger.info(f"🚀 Scan des Branches pour {PROJECT}...")
    try:
        r_br = session.get(f"{URL}/api/project_branches/list", params={"project": PROJECT}, verify=False)
        r_br.raise_for_status()
        branches = r_br.json().get("branches", [])
        
        for br in branches:
            name = br['name']
            is_main = br.get("isMain", False)
            date_str = br.get("analysisDate")

            if is_main or name in PROTECTED:
                logger.info(f"  🛡️ Branche {name} : Ignorée (Protégée ou Main).")
                continue

            if not date_str:
                logger.warning(f"  ⚠️ Branche {name} : Aucune analyse. Suppression...")
                delete_item(session, name, is_mr=False)
                continue

            age = (now - datetime.fromisoformat(date_str.replace("Z", "+00:00"))).days
            if age > DAYS:
                logger.info(f"  ⏳ Branche {name} : Inactive ({age}j).")
                delete_item(session, name, is_mr=False)
            else:
                logger.info(f"  ✨ Branche {name} : Conservée (Active depuis {age}j).")
    except Exception as e:
        logger.error(f"Erreur lors du scan des branches: {e}")

if __name__ == "__main__":
    run_clean()