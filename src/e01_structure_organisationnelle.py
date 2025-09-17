# src/e01_structure_organisationnelle.py (version corrigée)
import json
from database import get_connection, close_connection
from llm_client import generate_json, LLMError
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
    
    conn = get_connection()
    
    try:
        # Générer les données via LLM avec retry renforcé
        print("Génération de la structure organisationnelle via LLM...")
        data = generate_json(prompt, max_retries=5, max_tokens=4000)
        
        cursor = conn.cursor()
        
        # Validation des données
        if 'organizational_units' not in data or 'positions' not in data:
            raise Exception("Structure JSON invalide: clés manquantes")
        
        # Insérer les unités organisationnelles
        print("Insertion des unités organisationnelles...")
        units_created = 0
        for unit in data['organizational_units']:
            if 'name' in unit and 'description' in unit:
                cursor.execute("""
                    INSERT INTO organizational_unit (name, description)
                    VALUES (?, ?)
                """, (unit['name'], unit['description']))
                units_created += 1
            else:
                print(f"⚠ Unité ignorée (données incomplètes): {unit}")
        
        # Insérer les positions
        print("Insertion des positions...")
        positions_created = 0
        for position in data['positions']:
            if 'title' in position and 'description' in position:
                cursor.execute("""
                    INSERT INTO position (title, description)
                    VALUES (?, ?)
                """, (position['title'], position['description']))
                positions_created += 1
            else:
                print(f"⚠ Position ignorée (données incomplètes): {position}")
        
        conn.commit()
        
        print(f"✓ {units_created} unités organisationnelles créées")
        print(f"✓ {positions_created} positions créées")
        
        # Vérification finale
        if units_created == 0 or positions_created == 0:
            raise Exception("Aucune donnée valide créée")
        
    except LLMError as e:
        print(f"Erreur LLM fatale: {e}")
        conn.rollback()
        
        # Fallback: créer des données par défaut
        print("🔄 Création de données par défaut...")
        create_fallback_data(conn, company_profile)
        
    except Exception as e:
        print(f"Erreur lors de l'insertion: {e}")
        conn.rollback()
        
        # Fallback: créer des données par défaut
        print("🔄 Création de données par défaut...")
        create_fallback_data(conn, company_profile)
        
    finally:
        close_connection(conn)

def create_fallback_data(conn, company_profile):
    """Crée des données par défaut si le LLM échoue."""
    cursor = conn.cursor()
    
    try:
        # Unités organisationnelles par défaut
        default_units = [
            {"name": dept, "description": f"Département {dept} de {company_profile['nom']}"}
            for dept in company_profile['structure_organisationnelle']['departements']
        ]
        
        # Positions par défaut
        default_positions = [
            {"title": "Director", "description": "Senior leadership position"},
            {"title": "Manager", "description": "Team management position"},
            {"title": "Senior Specialist", "description": "Senior individual contributor"},
            {"title": "Specialist", "description": "Individual contributor"},
            {"title": "Junior Specialist", "description": "Entry-level position"},
            {"title": "Intern", "description": "Internship position"}
        ]
        
        # Insérer les unités
        for unit in default_units:
            cursor.execute("""
                INSERT INTO organizational_unit (name, description)
                VALUES (?, ?)
            """, (unit['name'], unit['description']))
        
        # Insérer les positions
        for position in default_positions:
            cursor.execute("""
                INSERT INTO position (title, description)
                VALUES (?, ?)
            """, (position['title'], position['description']))
        
        conn.commit()
        
        print(f"✓ {len(default_units)} unités par défaut créées")
        print(f"✓ {len(default_positions)} positions par défaut créées")
        
    except Exception as e:
        print(f"Erreur lors de la création des données par défaut: {e}")
        conn.rollback()
        raise