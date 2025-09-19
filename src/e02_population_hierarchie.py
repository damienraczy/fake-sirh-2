# src/e02_population_hierarchie.py (refonte complète)
import json
from utils.database import get_connection, close_connection
from utils.llm_client import generate_json, LLMError
from config import get_config
from utils.names_generator import NamesGenerator
from datetime import datetime, timedelta
import sqlite3
import random

# (La fonction _create_employee reste la même)
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
            position=position_title, unit=unit_name, sector=company_profile['secteur'],
            culture=company_profile['culture'], avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
            first_name=prenom, last_name=nom, email=email
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

def _create_and_assign_employee(cursor, names_gen, config, prompt_template, pos_data, unit_id, manager_id):
    """Crée un employé ET son affectation."""
    emp_id, hire_date = _create_employee(
        cursor, names_gen, config, prompt_template,
        pos_data['title'], pos_data.get('unit_name', 'N/A'), manager_id
    )
    
    # Créer le poste s'il n'existe pas
    cursor.execute("SELECT id FROM position WHERE title = ?", (pos_data['title'],))
    result = cursor.fetchone()
    if result:
        pos_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO position (title, description, level, unit_id) VALUES (?, ?, ?, ?)",
            (pos_data['title'], f"Poste de {pos_data['title']}", pos_data['level'], unit_id)
        )
        pos_id = cursor.lastrowid
        
    # Créer l'affectation
    cursor.execute(
        "INSERT INTO assignment (employee_id, position_id, unit_id, start_date) VALUES (?, ?, ?, ?)",
        (emp_id, pos_id, unit_id, hire_date)
    )
    return emp_id

def _populate_from_plan(cursor, node, names_gen, config, prompt_template, units_map, manager_id=None):
    """Fonction récursive pour peupler l'organigramme."""
    pos_data = node['position']
    unit_name = node['unit_name']
    unit_id = units_map.get(unit_name)

    if not unit_id:
        print(f"Avertissement: Unité '{unit_name}' non trouvée dans la base. Affectation ignorée.")
        return

    # Créer les employés pour le poste de manager (s'il y en a plusieurs) ou le poste racine
    current_manager_id = manager_id
    for i in range(pos_data['headcount']):
        # Le premier employé créé pour un poste de manager devient le manager des subalternes
        new_emp_id = _create_and_assign_employee(cursor, names_gen, config, prompt_template, pos_data, unit_id, manager_id)
        if i == 0 and node.get('subordinates'):
            current_manager_id = new_emp_id

    # Appel récursif pour les subordonnés
    for subordinate_node in node.get('subordinates', []):
        _populate_from_plan(cursor, subordinate_node, names_gen, config, prompt_template, units_map, current_manager_id)

def run():
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
            "departments": company_profile['structure_organisationnelle']['departements']
        }
        plan_prompt = plan_prompt_template.format(**prompt_input)
        
        print(f"plan_prompt = \n{plan_prompt}\n\n")

        print("Génération du plan d'effectif via LLM...")
        plan = generate_json(plan_prompt, max_retries=3)
        
        # 3. Récupérer les unités depuis la BDD
        cursor.execute("SELECT id, name FROM organizational_unit")
        units_map = {name: id for id, name in cursor.fetchall()}
        
        # 4. Peupler la base de données de manière récursive
        print("Peuplement de la base de données selon le plan...")
        _populate_from_plan(cursor, plan['organizational_chart'], names_gen, config, employee_prompt_template, units_map)

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