# src/e01_structure_organisationnelle.py (version réécrite)
import json
from utils.database import get_connection, close_connection
from utils.llm_client import generate_json, LLMError
from config import get_config
import sqlite3

def _generate_and_store_scaffolding(cursor: sqlite3.Cursor, config: dict) -> list:
    """Phase 1: Génère et stocke le squelette de l'organisation."""
    print("Phase 1a: Génération du squelette organisationnel...")
    company_profile = config['entreprise']
    
    with open('prompts/01a_organizational_scaffolding.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    prompt = prompt_template.format(
        company_name=company_profile['nom'],
        sector=company_profile['secteur'],
        size=company_profile['taille']
    )
    
    structure = generate_json(prompt, max_retries=3)
    
    # Stocker le squelette et préparer la phase de deep dive
    position_map = {} # title -> id
    units_to_deep_dive = []

    # 1. Créer le poste racine (CEO)
    ceo_data = structure['executive_team'][0]
    cursor.execute(
        "INSERT INTO position (title, description, level, reports_to_position_id, unit_id) VALUES (?, ?, ?, NULL, NULL)",
        (ceo_data['title'], "Overall direction of the company", ceo_data['level'])
    )
    ceo_id = cursor.lastrowid
    position_map[ceo_data['title']] = ceo_id
    
    # 2. Créer les unités et les postes de direction
    for dept in structure['departments']:
        cursor.execute(
            "INSERT INTO organizational_unit (name, description) VALUES (?, ?)",
            (dept['unit_name'], dept['description'])
        )
        unit_id = cursor.lastrowid
        
        head_data = dept['head']
        reports_to_id = position_map.get(head_data['reports_to'])
        
        cursor.execute(
            "INSERT INTO position (title, description, level, reports_to_position_id, unit_id) VALUES (?, ?, ?, ?, ?)",
            (head_data['title'], f"Head of {dept['unit_name']}", head_data['level'], reports_to_id, unit_id)
        )
        head_id = cursor.lastrowid
        position_map[head_data['title']] = head_id
        
        units_to_deep_dive.append({
            "unit_id": unit_id,
            "unit_name": dept['unit_name'],
            "head_title": head_data['title']
        })

    print(f"✓ Squelette créé avec {len(units_to_deep_dive)} départements.")
    return units_to_deep_dive, position_map

def _deep_dive_and_store_departments(cursor: sqlite3.Cursor, config: dict, units_to_deep_dive: list, position_map: dict):
    """Phase 2: Élabore la structure interne de chaque département."""
    print("\nPhase 1b: Élaboration de chaque département...")
    company_profile = config['entreprise']
    
    with open('prompts/01b_department_deep_dive.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
        
    for unit in units_to_deep_dive:
        print(f"  -> Élaboration de '{unit['unit_name']}'...")
        prompt = prompt_template.format(
            unit_name=unit['unit_name'],
            head_title=unit['head_title'],
            size=company_profile['taille'],
            sector=company_profile['secteur']
        )
        
        try:

            # print(f"prompt = \n{prompt}\===")

            positions = generate_json(prompt, max_retries=3, max_tokens=16000)
            
            # print(f"positions <<<---\n{positions}\n--->>>")

            # Pour résoudre les 'reports_to', on itère plusieurs fois si nécessaire
            # car les postes peuvent être définis dans le désordre.
            unresolved_positions = positions['department']
            for _ in range(len(positions) + 1): # Safety loop
                remaining = []
                for pos in unresolved_positions:
                    reports_to_id = position_map.get(pos['reports_to'])
                    if reports_to_id:
                        cursor.execute(
                            "INSERT INTO position (title, description, level, reports_to_position_id, unit_id) VALUES (?, ?, ?, ?, ?)",
                            (pos['title'], pos['description'], pos['level'], reports_to_id, unit['unit_id'])
                        )
                        position_map[pos['title']] = cursor.lastrowid
                    else:
                        remaining.append(pos)
                
                if not remaining:
                    break # Tout est résolu
                unresolved_positions = remaining
            
            if unresolved_positions:
                print(f"    ⚠ Impossible de résoudre {len(unresolved_positions)} postes pour '{unit['unit_name']}'.")

        except (LLMError, json.JSONDecodeError) as e:
            print(f"    ⚠ Erreur LLM pour '{unit['unit_name']}': {e}")
            continue

def run():
    """
    Étape 1: Génération du blueprint organisationnel complet.
    """
    print("Étape 1: Démarrage de la génération du blueprint organisationnel")
    config = get_config()
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Phase 1: Squelette
        units_to_deep_dive, position_map = _generate_and_store_scaffolding(cursor, config)
        
        # Phase 2: Élaboration
        _deep_dive_and_store_departments(cursor, config, units_to_deep_dive, position_map)
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM organizational_unit")
        unit_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM position")
        pos_count = cursor.fetchone()[0]
        print(f"\n✓ Blueprint terminé: {unit_count} unités et {pos_count} postes créés.")

    except Exception as e:
        print(f"\nErreur critique lors de la génération du blueprint: {e}")
        conn.rollback()
        raise
    finally:
        close_connection(conn)