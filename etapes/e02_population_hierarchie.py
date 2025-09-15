# =============================================================================
# etapes/e02_population_hierarchie.py
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config
from datetime import datetime, timedelta
import random

def run():
    """
    Étape 2: Génération de la population et hiérarchie
    Tables: employee, assignment
    """
    print("Étape 2: Génération de la population et hiérarchie")
    
    config = get_config()
    company_profile = config['entreprise']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Récupérer les unités et positions existantes
    cursor.execute("SELECT id, name FROM organizational_unit")
    units = cursor.fetchall()
    
    cursor.execute("SELECT id, title FROM position")
    positions = cursor.fetchall()
    
    # Lire le prompt pour la génération d'employés
    with open('prompts/02_employee_generation.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Générer le directeur général d'abord
    print("Génération du directeur général...")
    dg_prompt = prompt_template.format(
        position="Chief Executive Officer",
        unit="Direction Générale",
        sector=company_profile['secteur'],
        culture=company_profile['culture'],
        avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
        count=1
    )
    
    response = generate_text(dg_prompt)
    clean_response = strip_markdown_fences(response)
    
    try:
        dg_data = json.loads(clean_response)
        employee = dg_data['employees'][0]
        
        # Insérer le DG (manager_id = NULL)
        cursor.execute("""
            INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
            VALUES (?, ?, ?, ?, NULL)
        """, (employee['first_name'], employee['last_name'], 
              employee['email'], employee['hire_date']))
        
        dg_id = cursor.lastrowid
        print(f"✓ DG créé: {employee['first_name']} {employee['last_name']}")
        
        # Générer les managers de département
        managers = {}
        for unit in units:
            if unit['name'] != "Direction Générale":
                manager_prompt = prompt_template.format(
                    position="Department Manager",
                    unit=unit['name'],
                    sector=company_profile['secteur'],
                    culture=company_profile['culture'],
                    avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
                    count=1
                )
                
                response = generate_text(manager_prompt)
                clean_response = strip_markdown_fences(response)
                manager_data = json.loads(clean_response)
                employee = manager_data['employees'][0]
                
                cursor.execute("""
                    INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee['first_name'], employee['last_name'], 
                      employee['email'], employee['hire_date'], dg_id))
                
                manager_id = cursor.lastrowid
                managers[unit['id']] = manager_id
                
                print(f"✓ Manager {unit['name']}: {employee['first_name']} {employee['last_name']}")
        
        # Générer les employés restants
        remaining_employees = company_profile['taille'] - len(managers) - 1
        employees_per_unit = remaining_employees // len(units)
        
        for unit in units:
            if unit['name'] != "Direction Générale":
                unit_positions = [p for p in positions if "Manager" not in p['title'] and "Director" not in p['title']]
                
                for _ in range(employees_per_unit):
                    pos = random.choice(unit_positions)
                    manager_id = managers.get(unit['id'], dg_id)
                    
                    emp_prompt = prompt_template.format(
                        position=pos['title'],
                        unit=unit['name'],
                        sector=company_profile['secteur'],
                        culture=company_profile['culture'],
                        avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
                        count=1
                    )
                    
                    response = generate_text(emp_prompt)
                    clean_response = strip_markdown_fences(response)
                    emp_data = json.loads(clean_response)
                    employee = emp_data['employees'][0]
                    
                    cursor.execute("""
                        INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (employee['first_name'], employee['last_name'], 
                          employee['email'], employee['hire_date'], manager_id))
                    
                    emp_id = cursor.lastrowid
                    
                    # Créer l'affectation
                    cursor.execute("""
                        INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                        VALUES (?, ?, ?, ?, NULL)
                    """, (emp_id, pos['id'], unit['id'], employee['hire_date']))
        
        conn.commit()
        conn.close()
        
        # Compter les employés créés
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM employee")
        employee_count = cursor2.fetchone()[0]
        conn2.close()
        
        print(f"✓ {employee_count} employés créés au total")
        
    except Exception as e:
        print(f"Erreur lors de la génération: {e}")
        conn.rollback()
        conn.close()
