# =============================================================================
# etapes/e05_formations_developpement.py
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config
import random
from datetime import datetime, timedelta

def run():
    """
    Étape 5: Génération des formations et développement
    Tables: training_program, training_record
    """
    print("Étape 5: Génération des formations et développement")
    
    config = get_config()
    company_profile = config['entreprise']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Lire le prompt pour le catalogue de formations
    with open('prompts/05_training_catalog.txt', 'r', encoding='utf-8') as f:
        catalog_prompt_template = f.read()
    
    catalog_prompt = catalog_prompt_template.format(
        sector=company_profile['secteur'],
        challenges=', '.join(company_profile['defis']),
        training_budget=company_profile['contexte_rh']['budget_formation']
    )
    
    print("Génération du catalogue de formations...")
    response = generate_text(catalog_prompt)
    clean_response = strip_markdown_fences(response)
    
    try:
        catalog_data = json.loads(clean_response)
        
        # Insérer les programmes de formation
        training_ids = {}
        for training in catalog_data['training_programs']:
            cursor.execute("""
                INSERT INTO training_program (name, description, duration_hours, cost, provider)
                VALUES (?, ?, ?, ?, ?)
            """, (training['name'], training['description'], 
                  training['duration_hours'], training['cost'], training['provider']))
            training_ids[training['name']] = cursor.lastrowid
        
        print(f"✓ {len(catalog_data['training_programs'])} programmes de formation créés")
        
        # Récupérer tous les employés
        cursor.execute("SELECT id, first_name, last_name FROM employee")
        employees = cursor.fetchall()
        
        # Lire le prompt pour l'attribution des formations
        with open('prompts/05_training_assignment.txt', 'r', encoding='utf-8') as f:
            assignment_prompt_template = f.read()
        
        print("Attribution des formations aux employés...")
        
        for employee in employees:
            assignment_prompt = assignment_prompt_template.format(
                employee_name=f"{employee['first_name']} {employee['last_name']}",
                available_trainings=', '.join([t['name'] for t in catalog_data['training_programs']]),
                budget_per_employee=company_profile['contexte_rh']['budget_formation'],
                sector=company_profile['secteur']
            )
            
            response = generate_text(assignment_prompt)
            clean_response = strip_markdown_fences(response)
            
            try:
                assignment_data = json.loads(clean_response)
                
                for training_record in assignment_data['training_records']:
                    training_name = training_record['training_name']
                    
                    if training_name in training_ids:
                        # Générer une date de completion dans les 6 derniers mois
                        completion_date = datetime.now() - timedelta(days=random.randint(1, 180))
                        
                        cursor.execute("""
                            INSERT INTO training_record (employee_id, training_program_id, completion_date, 
                                                       score, satisfaction_rating, comments)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (employee['id'], training_ids[training_name], 
                              completion_date.strftime('%Y-%m-%d'),
                              training_record.get('score'),
                              training_record['satisfaction_rating'],
                              training_record['comments']))
                
            except json.JSONDecodeError:
                print(f"Erreur parsing formations pour {employee['first_name']} {employee['last_name']}")
                continue
        
        conn.commit()
        conn.close()
        
        print("✓ Formations attribuées aux employés")
        
    except Exception as e:
        print(f"Erreur lors de la génération des formations: {e}")
