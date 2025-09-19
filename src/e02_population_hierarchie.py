# src/e02_population_hierarchie.py (version refactorisée)
from utils.database import get_connection, close_connection
from llm_client import generate_json, LLMError
from config import get_config
from utils.names_generator import NamesGenerator
from datetime import datetime, timedelta
import random
import sqlite3 # Pour le type hinting du curseur

# --- Fonctions "Helpers" de bas niveau ---

def _fetch_initial_data(cursor: sqlite3.Cursor):
    """Récupère les unités et positions depuis la base de données."""
    cursor.execute("SELECT id, name FROM organizational_unit")
    units = cursor.fetchall()
    cursor.execute("SELECT id, title FROM position")
    positions = cursor.fetchall()
    
    if not units or not positions:
        raise ValueError("Aucune unité ou position trouvée. Exécutez d'abord l'étape 1.")
    
    print(f"Trouvé {len(units)} unités et {len(positions)} positions.")
    return units, positions

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
    
    # Date par défaut (fallback)
    hire_date = (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d')
    
    try:
        context_prompt = prompt_template.format(
            position=position_title, unit=unit_name, sector=company_profile['secteur'],
            culture=company_profile['culture'], avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
            first_name=prenom, last_name=nom, email=email
        )
        employee_data = generate_json(context_prompt, max_retries=3)
        if 'employees' in employee_data and employee_data['employees']:
            hire_date = employee_data['employees'][0].get('hire_date', hire_date)
            print(f"✓ Contexte LLM généré pour {prenom} {nom}")
    except (LLMError, Exception) as e:
        print(f"⚠ Fallback pour {prenom} {nom}: {e}")

    cursor.execute(
        "INSERT INTO employee (first_name, last_name, email, hire_date, manager_id) VALUES (?, ?, ?, ?, ?)",
        (prenom, nom, email, hire_date, manager_id)
    )
    return cursor.lastrowid, prenom, nom

def _create_assignment(cursor: sqlite3.Cursor, employee_id: int, position_id: int, unit_id: int, days_ago_min: int, days_ago_max: int):
    """Crée une affectation pour un employé."""
    start_date = (datetime.now() - timedelta(days=random.randint(days_ago_min, days_ago_max))).strftime('%Y-%m-%d')
    cursor.execute(
        "INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date) VALUES (?, ?, ?, ?, NULL)",
        (employee_id, position_id, unit_id, start_date)
    )

# --- Fonctions logiques de haut niveau ---

def _generate_ceo(cursor: sqlite3.Cursor, positions: list, names_gen: NamesGenerator, config: dict, prompt: str):
    """Génère le directeur général."""
    print("Génération du directeur général...")
    ceo_position = next((p for p in positions if any(w in p['title'].upper() for w in ['CEO', 'DIRECTOR', 'GENERAL', 'CHIEF'])), positions[0])
    
    dg_id, dg_prenom, dg_nom = _create_employee(cursor, names_gen, config, prompt, ceo_position['title'], "Direction Générale")
    print(f"✓ DG créé: {dg_prenom} {dg_nom}")
    return dg_id, ceo_position

def _generate_managers(cursor: sqlite3.Cursor, units: list, positions: list, ceo_id: int, names_gen: NamesGenerator, config: dict, prompt: str):
    """Génère un manager pour chaque unité organisationnelle."""
    print("Génération des managers de département...")
    managers = {}
    manager_positions = [p for p in positions if any(w in p['title'].upper() for w in ['MANAGER', 'HEAD', 'LEAD', 'SUPERVISOR'])]
    units_to_manage = [u for u in units if u['name'].upper() not in ["DIRECTION GÉNÉRALE", "EXECUTIVE"]]
    
    for unit in units_to_manage:
        manager_pos = random.choice(manager_positions) if manager_positions else random.choice(positions)
        manager_id, prenom, nom = _create_employee(cursor, names_gen, config, prompt, manager_pos['title'], unit['name'], manager_id=ceo_id)
        
        _create_assignment(cursor, manager_id, manager_pos['id'], unit['id'], 100, 800)
        managers[unit['id']] = manager_id
        print(f"✓ Manager {unit['name']}: {prenom} {nom}")
        
    return managers

def _generate_employees(cursor: sqlite3.Cursor, units: list, positions: list, managers: dict, ceo_pos_id: int, config: dict, names_gen: NamesGenerator, prompt: str):
    """Génère le reste des employés pour atteindre la taille cible."""
    print("Génération des employés...")
    total_target = config['entreprise']['taille']
    current_count = len(managers) + 1  # Managers + DG
    remaining_to_create = max(0, total_target - current_count)
    
    if not remaining_to_create:
        return
        
    print(f"Génération de {remaining_to_create} employés restants...")
    units_with_managers = [u for u in units if u['id'] in managers]
    
    employee_positions = [p for p in positions if not any(w in p['title'].upper() for w in ['MANAGER', 'DIRECTOR', 'CEO', 'HEAD', 'CHIEF'])]
    if not employee_positions:
        employee_positions = [p for p in positions if p['id'] != ceo_pos_id]

    # Simple répartition pour l'exemple
    for _ in range(remaining_to_create):
        unit = random.choice(units_with_managers)
        pos = random.choice(employee_positions) if employee_positions else random.choice(positions)
        manager_id = managers[unit['id']]
        
        emp_id, _, _ = _create_employee(cursor, names_gen, config, prompt, pos['title'], unit['name'], manager_id=manager_id)
        _create_assignment(cursor, emp_id, pos['id'], unit['id'], 30, 600)

def _print_final_stats(cursor: sqlite3.Cursor, config: dict):
    """Affiche les statistiques de la génération."""
    cursor.execute("SELECT COUNT(*) FROM employee")
    total_employees = cursor.fetchone()[0]
    print("\n=== STATISTIQUES ===")
    print(f"✓ {total_employees} employés créés au total (cible: {config['entreprise']['taille']})")
    print(f"✓ Domaine email: @{config['entreprise']['technique']['domaine_email']}")

# --- Orchestrateur principal ---

def run():
    """
    Étape 2: Génération de la population et hiérarchie.
    Orchestre la création des employés, des managers et du DG.
    """
    print("Étape 2: Démarrage de la génération de la population et hiérarchie")
    
    config = get_config()
    names_gen = NamesGenerator()
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        # 1. Préparation
        units, positions = _fetch_initial_data(cursor)
        with open('prompts/02_employee_generation.txt', 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 2. Génération de la hiérarchie
        dg_id, ceo_position = _generate_ceo(cursor, positions, names_gen, config, prompt_template)
        managers = _generate_managers(cursor, units, positions, dg_id, names_gen, config, prompt_template)
        _generate_employees(cursor, units, positions, managers, ceo_position['id'], config, names_gen, prompt_template)

        # 3. Affectation finale du DG
        print("Affectation du directeur général...")
        dg_unit = next((u for u in units if any(w in u['name'].upper() for w in ['DIRECTION', 'EXECUTIVE', 'GENERAL'])), units[0])
        _create_assignment(cursor, dg_id, ceo_position['id'], dg_unit['id'], 365, 1500)
        
        conn.commit()
        
        # 4. Statistiques
        _print_final_stats(cursor, config)
        
    except (ValueError, Exception) as e:
        print(f"\nErreur critique lors de la génération: {e}")
        conn.rollback()
        raise
    finally:
        close_connection(conn)