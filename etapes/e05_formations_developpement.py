# =============================================================================
# etapes/e05_formations_developpement.py (version complète)
# =============================================================================

from database import get_connection
from llm_client import generate_json, LLMError
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
    
    try:
        print("Génération du catalogue de formations...")
        catalog_data = generate_json(catalog_prompt)
        
        # Insérer les programmes de formation
        training_ids = {}
        if 'training_programs' in catalog_data:
            for training in catalog_data['training_programs']:
                if all(key in training for key in ['name', 'description', 'duration_hours', 'cost', 'provider']):
                    cursor.execute("""
                        INSERT INTO training_program (name, description, duration_hours, cost, provider)
                        VALUES (?, ?, ?, ?, ?)
                    """, (training['name'], training['description'], 
                          training['duration_hours'], training['cost'], training['provider']))
                    training_ids[training['name']] = cursor.lastrowid
        
        print(f"✓ {len(training_ids)} programmes de formation créés")
        
        # Récupérer tous les employés
        cursor.execute("SELECT id, first_name, last_name FROM employee")
        employees = cursor.fetchall()
        
        if not employees:
            print("Aucun employé trouvé. Assurez-vous d'avoir exécuté l'étape 2.")
            return
        
        # Lire le prompt pour l'attribution des formations
        with open('prompts/05_training_assignment.txt', 'r', encoding='utf-8') as f:
            assignment_prompt_template = f.read()
        
        print("Attribution des formations aux employés...")
        
        total_training_records = 0
        for employee in employees:
            assignment_prompt = assignment_prompt_template.format(
                employee_name=f"{employee['first_name']} {employee['last_name']}",
                available_trainings=', '.join(training_ids.keys()),
                budget_per_employee=company_profile['contexte_rh']['budget_formation'],
                sector=company_profile['secteur']
            )
            
            try:
                assignment_data = generate_json(assignment_prompt)
                
                records_created = 0
                if 'training_records' in assignment_data:
                    for training_record in assignment_data['training_records']:
                        if 'training_name' in training_record:
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
                                      training_record.get('satisfaction_rating', 3),
                                      training_record.get('comments', '')))
                                records_created += 1
                
                total_training_records += records_created
                print(f"✓ {records_created} formations → {employee['first_name']} {employee['last_name']}")
                
            except LLMError:
                print(f"⚠ Échec formations pour {employee['first_name']} {employee['last_name']}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"✓ {total_training_records} enregistrements de formation créés")
        
    except LLMError as e:
        print(f"Erreur fatale: {e}")
        raise
    except Exception as e:
        print(f"Erreur lors de la génération des formations: {e}")
        raise
