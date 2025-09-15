# =============================================================================
# etapes/e01_structure_organisationnelle.py
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config

def run():
    """
    Étape 1: Génération de la structure organisationnelle
    Tables: organizational_unit, position
    """
    print("Étape 1: Génération de la structure organisationnelle")
    
    config = get_config()
    company_profile = config['entreprise']
    
    # Lire le prompt pour la structure organisationnelle
    with open('prompts/01_organizational_structure.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Substituer les variables dans le prompt
    prompt = prompt_template.format(
        company_name=company_profile['nom'],
        sector=company_profile['secteur'],
        size=company_profile['taille'],
        culture=company_profile['culture'],
        departments=', '.join(company_profile['structure_organisationnelle']['departements']),
        hierarchy_levels=company_profile['structure_organisationnelle']['niveaux_hierarchiques']
    )
    
    # Générer les données via LLM
    print("Génération de la structure organisationnelle via LLM...")
    response = generate_text(prompt)
    clean_response = strip_markdown_fences(response)
    
    try:
        data = json.loads(clean_response)
        
        # Insérer en base de données
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insérer les unités organisationnelles
        print("Insertion des unités organisationnelles...")
        for unit in data['organizational_units']:
            cursor.execute("""
                INSERT INTO organizational_unit (name, description)
                VALUES (?, ?)
            """, (unit['name'], unit['description']))
        
        # Insérer les positions
        print("Insertion des positions...")
        for position in data['positions']:
            cursor.execute("""
                INSERT INTO position (title, description)
                VALUES (?, ?)
            """, (position['title'], position['description']))
        
        conn.commit()
        conn.close()
        
        print(f"✓ {len(data['organizational_units'])} unités organisationnelles créées")
        print(f"✓ {len(data['positions'])} positions créées")
        
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON: {e}")
        print(f"Réponse LLM: {clean_response[:500]}...")
    except Exception as e:
        print(f"Erreur lors de l'insertion: {e}")
