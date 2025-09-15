# llm_client.py
import os
import requests
import json
from dotenv import load_dotenv

from config import load_config


# Charger les variables d'environnement depuis le fichier .env
# dotenv_path = load_dotenv(os.path.expanduser('~/env/.env'), override=True)
# if os.path.exists(dotenv_path):
#     load_dotenv(dotenv_path)
# else:
#     print("Attention: Fichier .env non trouvé. Utilisation des variables d'environnement système.")

OLLAMA_API_URL = "https://ollama.com/api/generate"
OLLAMA_MODEL = "gpt-oss:20b"
load_dotenv(os.path.expanduser('~/env/.env'), override=True)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")


def generate_text(prompt: str):
    """
    Envoie un prompt au LLM via l'API Ollama et retourne le texte généré.
    """
    # print(f"Configuration LLM: API_URL={OLLAMA_API_URL}, MODEL={OLLAMA_MODEL}, OLLAMA_API_KEY={OLLAMA_API_KEY}")

    if not OLLAMA_API_URL or not OLLAMA_MODEL:
        # print("Erreur: L'URL de l'API Ollama ou le nom du modèle n'est pas configuré dans .env.")
        return "Erreur de configuration LLM."

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False # On attend la réponse complète
    }
    

    # print(f"\n--- LLM >>>\n{prompt[:200]}...")

    try:
        response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(payload), timeout=300) # Timeout de 5 minutes
        response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP
        
        response_data = response.json()
        
        # Nettoyage de la réponse pour enlever les guillemets ou autres formatages
        clean_response = response_data.get('response', '').strip()
        
        # print(f"SUCCES\n\n---------------------------------")
        return clean_response

    except requests.exceptions.RequestException as e:
        print(f"Erreur critique lors de la requête LLM: {e}\n---------------------------------")
        return f"Erreur de communication avec le LLM: {e}"
    except json.JSONDecodeError:
        print(f"Erreur: Impossible de décoder la réponse JSON du LLM. Réponse brute: {response.text}\n---------------------------------")
        return "Erreur de format de réponse du LLM."