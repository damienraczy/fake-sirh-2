# =============================================================================
# src/e04_objectifs_performance.py - Version avec évaluations historiques
# =============================================================================

from utils.database import get_connection
from utils.llm_client import generate_json, LLMError
from config import get_config
from datetime import datetime, timedelta
import random

def get_evaluation_date(year: int, quarter: str, hire_date: str) -> str:
    """
    Calcule la date d'évaluation pour une année et un trimestre donnés.
    L'employé doit avoir 6 mois d'ancienneté pleins avant le début du trimestre.
    """
    hire_datetime = datetime.strptime(hire_date, '%Y-%m-%d')
    
    # Définir les trimestres
    quarters = {
        'Q1': (1, 3),   # Janvier-Mars
        'Q2': (4, 6),   # Avril-Juin  
        'Q3': (7, 9),   # Juillet-Septembre
        'Q4': (10, 12)  # Octobre-Décembre
    }
    
    if quarter not in quarters:
        return None
    
    start_month, end_month = quarters[quarter]
    quarter_start = datetime(year, start_month, 1)
    
    # Vérifier les 6 mois d'ancienneté avant le début du trimestre
    required_tenure = quarter_start - timedelta(days=183)  # 6 mois pleins
    if hire_datetime > required_tenure:
        return None  # Pas assez d'ancienneté
    
    # Générer une date aléatoire dans le trimestre
    start_date = datetime(year, start_month, 1)
    if end_month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, end_month + 1, 1) - timedelta(days=1)
    
    # Date aléatoire dans le trimestre
    days_diff = (end_date - start_date).days
    random_days = random.randint(0, days_diff)
    evaluation_date = start_date + timedelta(days=random_days)
    
    return evaluation_date.strftime('%Y-%m-%d')

def run():
    """
    Étape 4: Génération des objectifs et évaluations de performance
    Tables: goal, performance_review
    """
    print("Étape 4: Génération des objectifs et évaluations de performance")
    
    config = get_config()
    company_profile = config['entreprise']
    current_year = datetime.now().year
    
    # Récupérer la période d'évaluation depuis la config
    annual_reviews = company_profile['contexte_rh'].get('annual_reviews', 'Q1')
    print(f"Période d'évaluation configurée: {annual_reviews}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Récupérer tous les employés avec leurs informations incluant hire_date
    cursor.execute("""
        SELECT e.id, e.first_name, e.last_name, e.manager_id, e.hire_date,
               e.conciousness, e.cooperation, e.flexibility,  
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
    
    # Vider les objectifs et évaluations existants pour éviter les doublons
    cursor.execute("DELETE FROM goal")
    cursor.execute("DELETE FROM performance_review")
    conn.commit()

    print("Génération des objectifs et évaluations...")
    
    goals_created = 0
    reviews_created = 0
    
    for employee in employees:
        employee_name = f"{employee['first_name']} {employee['last_name']}"
        hire_date = employee['hire_date']
        hire_year = datetime.strptime(hire_date, '%Y-%m-%d').year
        
        print(f"Traitement de {employee_name} (embauché le {hire_date})")
        
        past_objective = None  # Pour stocker l'objectif de l'année précédente
        goals_data = None

        # Générer les évaluations pour chaque année depuis l'embauche jusqu'à aujourd'hui
        for eval_year in range(hire_year, current_year + 1):
            evaluation_date = get_evaluation_date(eval_year, annual_reviews, hire_date)
            
            if evaluation_date is None:
                print(f"  → {eval_year}: Non éligible (ancienneté insuffisante)")
                continue  # Pas éligible cette année-là
            
            # Vérifier que la date d'évaluation est dans le passé
            if datetime.strptime(evaluation_date, '%Y-%m-%d') > datetime.now():
                print(f"  → {eval_year}: Évaluation future, ignorée")
                continue  # Évaluation future, on ne la génère pas encore
            
            print(f"  → {eval_year}: Génération objectif {employee_name} ")
            

            # Générer les objectifs (sauf pour le DG qui n'a pas de manager)
            if employee['manager_id']:
                goals_prompt = goals_prompt_template.format(
                    employee_name=employee_name,
                    position=employee['position_title'] or "Employee",
                    unit=employee['unit_name'] or "Unknown",
                    year=eval_year,  # Utiliser l'année d'évaluation, pas l'année courante
                    challenges=', '.join(company_profile['defis']),
                    culture=company_profile['culture'],
                    language=company_profile['language'],
                    sector=company_profile['secteur'],
                    location=company_profile['location'],
                    region_culture=company_profile['region_culture'],
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
                                      goal['description'], eval_year, goal['status']))
                                goals_created += 1
                    
                except LLMError:
                    print(f"    ⚠ Échec objectifs pour {employee_name} ({eval_year})")
            
            print(f"  → {eval_year}: Génération évaluation {employee_name} ")

            # Générer l'évaluation de performance
            review_prompt = review_prompt_template.format(
                employee_name=employee_name,
                position=employee['position_title'] or "Employee",
                unit=employee['unit_name'] or "Unknown",
                year=eval_year,  # Utiliser l'année d'évaluation, pas l'année courante
                culture=company_profile['culture'],
                language=company_profile['language'],
                sector=company_profile['secteur'],
                location=company_profile['location'],
                region_culture=company_profile['region_culture'],
                conciousness=employee['conciousness'] or 3,
                cooperation=employee['cooperation'] or 3,
                flexibility=employee['flexibility'] or 3,
                past_objective=past_objective or "No past objective available"
            )
            
            try:
                review_data = generate_json(review_prompt)
                
                if 'score' in review_data and 'comments' in review_data:
                    reviewer_id = employee['manager_id'] or 1  # DG s'auto-évalue ou évalué par ID 1
                    
                    cursor.execute("""
                        INSERT INTO performance_review (employee_id, reviewer_id, evaluation_year, score, comments)
                        VALUES (?, ?, ?, ?, ?)
                    """, (employee['id'], reviewer_id, eval_year, 
                          review_data['score'], review_data['comments']))
                    reviews_created += 1


            except LLMError:
                print(f"    ⚠ Échec évaluation pour {employee_name} ({eval_year})")

        if goals_data and 'goals' in goals_data and goals_data['goals']:
            past_objective = str(goals_data['goals'][0])
        else:
            past_objective = "No past objective available"
    
    conn.commit()
    conn.close()
    
    print(f"✓ {goals_created} objectifs créés")
    print(f"✓ {reviews_created} évaluations de performance créées")