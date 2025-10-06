# utils/llm_client.py (version mise à jour avec logging)
import os
import requests
import json
import time
import logging
from dotenv import load_dotenv
from utils.utils_llm import strip_markdown_fences

# --- Début des modifications ---
# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='llm_calls.log', # Les logs seront sauvegardés dans ce fichier
    filemode='a'
)
# --- Fin des modifications ---

# Configuration API
OLLAMA_API_URL = "https://ollama.com/api/generate"
OLLAMA_MODEL = "gpt-oss:20b"
load_dotenv(os.path.expanduser("~/env/.env"), override=True)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

class LLMError(Exception):
    """Exception levée quand le LLM échoue après tous les retries"""
    pass

def generate_text(prompt: str, max_tokens: int = 16000):
    """
    Envoie un prompt au LLM via l'API Ollama et retourne le texte généré.
    """
    if not OLLAMA_API_URL or not OLLAMA_MODEL:
        logging.error("Configuration LLM manquante (URL ou MODEL).")
        return "Erreur de configuration LLM."

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9
        }
    }

    # --- Début des modifications ---
    start_time = time.time()
    try:
        response = requests.post(
            OLLAMA_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=300
        )
        response.raise_for_status()

        response_data = response.json()
        clean_response = response_data.get("response", "").strip()

        latency = time.time() - start_time
        logging.info(f"Appel LLM (generate_text) SUCCES - Latence: {latency:.2f}s - Prompt: '{prompt[:200]}...'")
        # --- Fin des modifications ---

        return clean_response

    except requests.exceptions.RequestException as e:
        latency = time.time() - start_time
        logging.error(f"Appel LLM (generate_text) ECHEC - Latence: {latency:.2f}s - Erreur: {e} - Prompt: '{prompt[:200]}...'")
        return f"Erreur de communication avec le LLM: {e}"
    except json.JSONDecodeError:
        latency = time.time() - start_time
        logging.error(f"Appel LLM (generate_text) ECHEC - Latence: {latency:.2f}s - Erreur: Décodage JSON - Réponse brute: {response.text[:200]}")
        return "Erreur de format de réponse du LLM."

def generate_json(prompt: str, max_retries: int = 5, delay: float = 0.5, max_tokens: int = 16000):
    """
    Génère du JSON valide via LLM avec retry automatique renforcé.
    """
    enhanced_prompt = prompt + "\nJSON:"

    for attempt in range(max_retries):
        try:
            # --- Début des modifications (logging simple ici) ---
            logging.info(f"Tentative {attempt + 1}/{max_retries} pour générer du JSON - Prompt: '{enhanced_prompt[:200]}...'")
            # --- Fin des modifications ---

            response = generate_text(enhanced_prompt, max_tokens=max_tokens)

            if not response or "Erreur" in response:
                raise Exception(f"Erreur LLM: {response}")

            clean_response = strip_markdown_fences(response)
            data = json.loads(clean_response)

            if not isinstance(data, dict):
                raise json.JSONDecodeError("La réponse n'est pas un objet JSON", clean_response, 0)

            logging.info(f"JSON valide généré à la tentative {attempt + 1}")
            return data

        except json.JSONDecodeError as e:
            logging.warning(f"Erreur parsing JSON (tentative {attempt + 1}): {e} - Réponse: {clean_response[:300]}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                logging.error(f"Échec final de génération JSON après {max_retries} tentatives.")
                raise LLMError(f"Impossible de générer du JSON valide après {max_retries} tentatives")

        except Exception as e:
            logging.warning(f"Erreur LLM (tentative {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                logging.error(f"Échec final de génération JSON après {max_retries} tentatives.")
                raise LLMError(f"Erreur LLM après {max_retries} tentatives: {e}")

def extract_json_from_response(response: str) -> str:
    """
    Extrait le JSON d'une réponse qui pourrait contenir du texte supplémentaire.
    """
    response = response.strip()
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1 and end > start:
        return response[start:end+1]
    return response