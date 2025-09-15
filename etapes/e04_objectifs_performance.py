# =============================================================================
# etapes/e04_objectifs_performance.py
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config
from datetime import datetime

def run():
    """
    Étape 4: Génération des objectifs et évaluations de performance
    Tables: goal, performance_review
    """
    print("Étape 4: Génération des objectifs et évaluations de performance")
    
    config = get_config()
    company_profile = config['entreprise']
    current_year = datetime.now().year
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Récupérer tous les employés avec leurs managers et postes
    cursor.execute("""
        SELECT e.id, e.first_name, e.last_name, e.manager_id,
               p.title as position_title, ou.name as unit_name
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
    """)
    employees = cursor.fetchall()
    
    # Lire les prompts
    with open('prompts/04_goals_generation.txt', 'r', encoding='utf-8') as f:
        goals_prompt_template = f.read()
    
    with open('prompts/04_performance_review.txt', 'r', encoding='utf-8') as f:
        review_prompt_template = f.read()
    
    print("Génération des objectifs et évaluations...")
    
    for employee in employees:
        if employee['manager_id']:  # Skip DG pour les objectifs assignés
            # Générer les objectifs
            goals_prompt = goals_prompt_template.format(
                employee_name=f"{employee['first_name']} {employee['last_name']}",
                position=employee['position_title'] or "Employee",
                unit=employee['unit_name'] or "Unknown",
                year=current_year,
                challenges=', '.join(company_profile['defis']),
                culture=company_profile['culture']
            )
            
            response = generate_text(goals_prompt)
            clean_response = strip_markdown_fences(response)
            
            try:
                goals_data = json.loads(clean_response)
                
                for goal in goals_data['goals']:
                    cursor.execute("""
                        INSERT INTO goal (assignee_id, assigner_id, description, evaluation_year, status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (employee['id'], employee['manager_id'], 
                          goal['description'], current_year, goal['status']))
                
            except json.JSONDecodeError:
                print(f"Erreur parsing objectifs pour {employee['first_name']} {employee['last_name']}")
        
        # Générer l'évaluation de performance
        review_prompt = review_prompt_template.format(
            employee_name=f"{employee['first_name']} {employee['last_name']}",
            position=employee['position_title'] or "Employee",
            unit=employee['unit_name'] or "Unknown",
            year=current_year,
            culture=company_profile['culture']
        )
        
        response = generate_text(review_prompt)
        clean_response = strip_markdown_fences(response)
        
        try:
            review_data = json.loads(clean_response)
            
            reviewer_id = employee['manager_id'] or 1  # DG s'auto-évalue
            
            cursor.execute("""
                INSERT INTO performance_review (employee_id, reviewer_id, evaluation_year, score, comments)
                VALUES (?, ?, ?, ?, ?)
            """, (employee['id'], reviewer_id, current_year, 
                  review_data['score'], review_data['comments']))
            
        except json.JSONDecodeError:
            print(f"Erreur parsing évaluation pour {employee['first_name']} {employee['last_name']}")
    
    conn.commit()
    conn.close()
    
    print("✓ Objectifs et évaluations de performance générés")
