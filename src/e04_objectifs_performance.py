# =============================================================================
# src/e04_objectifs_performance.py (version complète)
# =============================================================================

from database import get_connection
from llm_client import generate_json, LLMError
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
    
    if not employees:
        print("Aucun employé trouvé. Assurez-vous d'avoir exécuté l'étape 2.")
        return
    
    # Lire les prompts
    with open('prompts/04_goals_generation.txt', 'r', encoding='utf-8') as f:
        goals_prompt_template = f.read()
    
    with open('prompts/04_performance_review.txt', 'r', encoding='utf-8') as f:
        review_prompt_template = f.read()
    
    print("Génération des objectifs et évaluations...")
    
    goals_created = 0
    reviews_created = 0
    
    for employee in employees:
        employee_name = f"{employee['first_name']} {employee['last_name']}"
        
        # Générer les objectifs (sauf pour le DG qui n'a pas de manager pour lui assigner)
        if employee['manager_id']:
            goals_prompt = goals_prompt_template.format(
                employee_name=employee_name,
                position=employee['position_title'] or "Employee",
                unit=employee['unit_name'] or "Unknown",
                year=current_year,
                challenges=', '.join(company_profile['defis']),
                culture=company_profile['culture']
            )
            
            try:
                goals_data = generate_json(goals_prompt)
                
                if 'goals' in goals_data:
                    for goal in goals_data['goals']:
                        if 'description' in goal and 'status' in goal:
                            cursor.execute("""
                                INSERT INTO goal (assignee_id, assigner_id, description, evaluation_year, status)
                                VALUES (?, ?, ?, ?, ?)
                            """, (employee['id'], employee['manager_id'], 
                                  goal['description'], current_year, goal['status']))
                            goals_created += 1
                
                print(f"✓ Objectifs générés pour {employee_name}")
                
            except LLMError:
                print(f"⚠ Échec objectifs pour {employee_name}")
        
        # Générer l'évaluation de performance
        review_prompt = review_prompt_template.format(
            employee_name=employee_name,
            position=employee['position_title'] or "Employee",
            unit=employee['unit_name'] or "Unknown",
            year=current_year,
            culture=company_profile['culture']
        )
        
        try:
            review_data = generate_json(review_prompt)
            
            if 'score' in review_data and 'comments' in review_data:
                reviewer_id = employee['manager_id'] or 1  # DG s'auto-évalue ou évalué par ID 1
                
                cursor.execute("""
                    INSERT INTO performance_review (employee_id, reviewer_id, evaluation_year, score, comments)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee['id'], reviewer_id, current_year, 
                      review_data['score'], review_data['comments']))
                reviews_created += 1
                
                print(f"✓ Évaluation générée pour {employee_name}")
            
        except LLMError:
            print(f"⚠ Échec évaluation pour {employee_name}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ {goals_created} objectifs créés")
    print(f"✓ {reviews_created} évaluations de performance créées")
