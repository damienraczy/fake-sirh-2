# src/e02_population_hierarchie.py (version corrigée et complète)
import json
from utils.database import get_connection, close_connection
from utils.llm_client import generate_json, LLMError
from config import get_config
from utils.names_generator import NamesGenerator
from datetime import datetime, timedelta
import sqlite3
import random

def _create_employee(
    cursor: sqlite3.Cursor,
    names_gen: NamesGenerator,
    config: dict,
    prompt_template: str,
    position_title: str,
    unit_name: str,
    manager_id=None
):
    """Génère un nom local, appelle le LLM pour le contexte, et insère un employé."""
    company_profile = config['entreprise']
    is_male = random.random() < company_profile['contexte_rh']['ratio_hommes']
    prenom, nom, email_base = names_gen.generate_unique_name(is_male)
    email = f"{email_base}@{company_profile['technique']['domaine_email']}"

    hire_date = (datetime.now() - timedelta(days=random.randint(30, 2000))).strftime('%Y-%m-%d')

    try:
        context_prompt = prompt_template.format(
            position=position_title, 
            unit=unit_name,
            sector=company_profile['secteur'],
            culture=company_profile['culture'],
            avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
            first_name=prenom,
            last_name=nom,
            email=email,
            location = company_profile['location'],
            language = company_profile['language'],
            region_culture = company_profile['region_culture'],
        )
        employee_data = generate_json(context_prompt, max_retries=3)
        if 'employees' in employee_data and employee_data['employees']:
            hire_date = employee_data['employees'][0].get('hire_date', hire_date)
    except (LLMError, Exception) as e:
        print(f"⚠ Fallback LLM pour {prenom} {nom}: {e}")

    cursor.execute(
        "INSERT INTO employee (first_name, last_name, email, hire_date, manager_id) VALUES (?, ?, ?, ?, ?)",
        (prenom, nom, email, hire_date, manager_id)
    )
    return cursor.lastrowid, hire_date

def _create_positions_from_plan(cursor: sqlite3.Cursor, node: dict, units_map: dict, parent_pos_id=None):
    """
    Crée récursivement tous les postes et leur hiérarchie à partir du plan.
    Cette fonction MODIFIE le dictionnaire 'node' en y ajoutant la clé 'db_id'.
    """
    pos_data = node['position']
    unit_id = units_map.get(node['unit_name'])
    
    cursor.execute(
        "INSERT INTO position (title, description, level, unit_id, reports_to_position_id) VALUES (?, ?, ?, ?, ?)",
        (pos_data['title'], f"Poste de {pos_data['title']}", pos_data.get('level'), unit_id, parent_pos_id)
    )
    current_pos_id = cursor.lastrowid
    # Stocker l'ID de la BDD dans le plan pour l'utiliser lors du peuplement
    pos_data['db_id'] = current_pos_id

    for subordinate_node in node.get('subordinates', []):
        _create_positions_from_plan(cursor, subordinate_node, units_map, current_pos_id)

def _create_employees_from_plan(cursor: sqlite3.Cursor, node: dict, names_gen: NamesGenerator, config: dict, prompt_template: str, units_map: dict, manager_id=None):
    """
    Peuple récursivement la structure avec des employés en se basant sur les postes déjà créés.
    """
    pos_data = node['position']
    unit_id = units_map.get(node['unit_name'])
    pos_id = pos_data['db_id'] # Récupère l'ID du poste depuis le plan
    
    current_manager_id = manager_id
    for i in range(pos_data['headcount']):
        emp_id, hire_date = _create_employee(
            cursor, names_gen, config, prompt_template,
            pos_data['title'], node['unit_name'], manager_id
        )
        
        cursor.execute(
            "INSERT INTO assignment (employee_id, position_id, unit_id, start_date) VALUES (?, ?, ?, ?)",
            (emp_id, pos_id, unit_id, hire_date)
        )
        
        # Le premier employé créé pour un poste de manager devient le manager des subalternes
        if i == 0 and node.get('subordinates'):
            current_manager_id = emp_id

    for subordinate_node in node.get('subordinates', []):
        _create_employees_from_plan(cursor, subordinate_node, names_gen, config, prompt_template, units_map, current_manager_id)

def run():
    """
    Étape 2: Génère un plan d'effectif, crée la hiérarchie des postes,
    puis peuple la structure avec les employés.
    """
    print("Étape 2: Génération du plan d'effectif et peuplement")
    config = get_config()
    company_profile = config['entreprise']
    names_gen = NamesGenerator()
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        # 1. Lire les prompts
        with open('prompts/01_headcount_plan_generation.txt', 'r', encoding='utf-8') as f:
            plan_prompt_template = f.read()
        with open('prompts/02_employee_generation.txt', 'r', encoding='utf-8') as f:
            employee_prompt_template = f.read()
            
        # 2. Préparer et appeler le LLM pour le plan
        prompt_input = {
            "company_name": company_profile['nom'],
            "sector": company_profile['secteur'],
            "target_headcount": company_profile['taille'],
            "culture": company_profile['culture'],
            "departments": json.dumps(company_profile['structure_organisationnelle']['departements'])
        }
        plan_prompt = plan_prompt_template.format(**prompt_input)
        
        print("Génération du plan d'effectif via LLM...")
        plan = generate_json(plan_prompt, max_retries=3)
        
        # 3. Récupérer les unités depuis la BDD
        cursor.execute("SELECT id, name FROM organizational_unit")
        units_map = {name: id for id, name in cursor.fetchall()}
        
        # 4. Créer la hiérarchie des postes
        print("Création de la hiérarchie des postes...")
        _create_positions_from_plan(cursor, plan['organizational_chart'], units_map)
        
        # 5. Peupler la base de données avec les employés
        print("Peuplement de la base de données avec les employés...")
        _create_employees_from_plan(cursor, plan['organizational_chart'], names_gen, config, employee_prompt_template, units_map)

        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM employee")
        total_employees = cursor.fetchone()[0]
        print(f"\n✓ Peuplement terminé. Total de {total_employees} employés créés (cible: {company_profile['taille']}).")

    except Exception as e:
        print(f"Erreur critique lors du peuplement: {e}")
        conn.rollback()
        raise
    finally:
        close_connection(conn)