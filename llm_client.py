# llm_client.py (version corrigée)
import os
import requests
import json
import time
from dotenv import load_dotenv
from utils_llm import strip_markdown_fences

# Configuration API
OLLAMA_API_URL = "https://ollama.com/api/generate"
OLLAMA_MODEL = "gpt-oss:20b"
load_dotenv(os.path.expanduser("~/env/.env"), override=True)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

class LLMError(Exception):
    """Exception levée quand le LLM échoue après tous les retries"""
    pass

def generate_text(prompt: str, max_tokens: int = 2000):
    """
    Envoie un prompt au LLM via l'API Ollama et retourne le texte généré.
    """
    if not OLLAMA_API_URL or not OLLAMA_MODEL:
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

        return clean_response

    except requests.exceptions.RequestException as e:
        print(f"Erreur critique lors de la requête LLM: {e}")
        return f"Erreur de communication avec le LLM: {e}"
    except json.JSONDecodeError:
        print(f"Erreur: Impossible de décoder la réponse JSON du LLM. Réponse brute: {response.text}")
        return "Erreur de format de réponse du LLM."

def generate_json(prompt: str, max_retries: int = 5, delay: float = 2.0, max_tokens: int = 3000):
    """
    Génère du JSON valide via LLM avec retry automatique renforcé.
    """
    # Améliorer le prompt pour forcer le JSON
    enhanced_prompt = f"""
{prompt}

IMPORTANT: Répondez UNIQUEMENT avec du JSON valide. Ne pas ajouter de texte avant ou après le JSON.
Le JSON doit être complet et bien formé. Exemple de structure:
{{"exemple": "valeur"}}

JSON:
"""

    for attempt in range(max_retries):
        try:
            print(f"Génération LLM - tentative {attempt + 1}/{max_retries}")

            # Appel LLM avec plus de tokens
            response = generate_text(enhanced_prompt, max_tokens=max_tokens)

            if not response or "Erreur" in response:
                raise Exception(f"Erreur LLM: {response}")

            # Nettoyage plus agressif
            clean_response = strip_markdown_fences(response)
            
            # Essayer d'extraire le JSON s'il y a du texte en plus
            clean_response = extract_json_from_response(clean_response)
            
            # Validation et parsing
            data = json.loads(clean_response)

            if not isinstance(data, dict):
                raise json.JSONDecodeError("Réponse n'est pas un objet JSON", clean_response, 0)

            print(f"✓ JSON valide généré à la tentative {attempt + 1}")
            return data

        except json.JSONDecodeError as e:
            print(f"✗ Erreur parsing JSON (tentative {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"Réponse problématique: {clean_response[:300]}...")
                print(f"Nouvelle tentative dans {delay}s...")
                time.sleep(delay * (attempt + 1))  # Délai croissant
            else:
                print(f"Échec définitif après {max_retries} tentatives")
                print(f"Dernière réponse: {clean_response}")
                raise LLMError(f"Impossible de générer du JSON valide après {max_retries} tentatives")

        except Exception as e:
            print(f"✗ Erreur LLM (tentative {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"Nouvelle tentative dans {delay}s...")
                time.sleep(delay * (attempt + 1))
            else:
                print(f"Échec définitif après {max_retries} tentatives")
                raise LLMError(f"Erreur LLM après {max_retries} tentatives: {e}")

def extract_json_from_response(response: str) -> str:
    """
    Extrait le JSON d'une réponse qui pourrait contenir du texte supplémentaire.
    """
    response = response.strip()
    
    # Chercher le premier { et le dernier }
    start = response.find('{')
    end = response.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        return response[start:end+1]
    
    # Si pas de JSON trouvé, retourner tel quel
    return response