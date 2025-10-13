# =============================================================================
# src/e05_formations_developpement.py - Version respectant l'architecture existante
# =============================================================================

from core.database import get_connection
from data_generation.utils.llm_client import generate_json, LLMError
from core.config import get_config
import random
from datetime import datetime, timedelta
import uuid

def generate_training_date(year: int, hire_date: str) -> str:
    """Génère une date de formation aléatoire dans l'année."""
    hire_datetime = datetime.strptime(hire_date, '%Y-%m-%d')
    year_start = datetime(year, 1, 1)
    start_date = max(year_start, hire_datetime)
    
    if year == datetime.now().year:
        end_date = datetime.now()
    else:
        end_date = datetime(year, 12, 31)
    
    if start_date > end_date:
        return None
    
    days_diff = (end_date - start_date).days
    if days_diff <= 0:
        return start_date.strftime('%Y-%m-%d')
    
    random_days = random.randint(0, days_diff)
    training_date = start_date + timedelta(days=random_days)
    return training_date.strftime('%Y-%m-%d')

def update_employee_skills_from_training(cursor, employee_id: int, training_name: str, training_description: str, training_score: int, config: dict):
    """Met à jour les compétences d'un employé suite à une formation via LLM."""
    # Récupérer les compétences disponibles
    cursor.execute("SELECT name FROM skill")
    available_skills = [row[0] for row in cursor.fetchall()]
    
    if not available_skills:
        return
    
    # Lire le prompt pour l'analyse des compétences
    with open('data_generation/prompts/05_skills_mapping.txt', 'r', encoding='utf-8') as f:
        skills_prompt_template = f.read()
    
    skills_prompt = skills_prompt_template.format(
        training_name=training_name,
        training_description=training_description,
        available_skills=', '.join(available_skills),
        sector=config['entreprise']['secteur'],
        language=config['entreprise']['language']
    )
    
    try:
        skills_data = generate_json(skills_prompt)
        related_skills = skills_data.get('related_skills', [])
        
        if not related_skills:
            return
        
        # Déterminer le nouveau niveau basé sur le score
        if training_score >= 90:
            new_level = 'Expert'
        elif training_score >= 80:
            new_level = 'Advanced'
        elif training_score >= 70:
            new_level = 'Intermediate'
        else:
            new_level = 'Beginner'
        
        level_hierarchy = {'Beginner': 1, 'Intermediate': 2, 'Advanced': 3, 'Expert': 4}
        
        for skill_name in related_skills:
            # Vérifier si la compétence existe
            cursor.execute("SELECT id FROM skill WHERE name = ?", (skill_name,))
            skill_result = cursor.fetchone()
            
            if not skill_result:
                continue
            
            skill_id = skill_result[0]
            
            # Vérifier si l'employé a déjà cette compétence
            cursor.execute("""
                SELECT level FROM employee_skill 
                WHERE employee_id = ? AND skill_id = ?
            """, (employee_id, skill_id))
            
            existing_skill = cursor.fetchone()
            
            if existing_skill:
                current_level = existing_skill[0]
                if level_hierarchy.get(new_level, 0) > level_hierarchy.get(current_level, 0):
                    cursor.execute("""
                        UPDATE employee_skill 
                        SET level = ? 
                        WHERE employee_id = ? AND skill_id = ?
                    """, (new_level, employee_id, skill_id))
            else:
                cursor.execute("""
                    INSERT INTO employee_skill (employee_id, skill_id, level)
                    VALUES (?, ?, ?)
                """, (employee_id, skill_id, new_level))
        
    except LLMError:
        return  # Échec silencieux

def run():
    """
    Étape 5: Génération des formations et développement
    Tables: training_program, training_record
    """
    print("Étape 5: Génération des formations et développement")
    
    config = get_config()
    company_profile = config['entreprise']
    current_year = datetime.now().year
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Lire le prompt pour le catalogue de formations
    with open('data_generation/prompts/05_training_catalog.txt', 'r', encoding='utf-8') as f:
        catalog_prompt_template = f.read()
    
    catalog_prompt = catalog_prompt_template.format(
        sector=company_profile['secteur'],
        challenges=', '.join(company_profile['defis']),
        training_budget=company_profile['contexte_rh']['budget_formation'],
        language=company_profile['language']
    )
    
    try:
        print("Génération du catalogue de formations...")
        catalog_data = generate_json(catalog_prompt)
        
        # Insérer les programmes de formation
        training_ids = {}
        training_descriptions = {}
        if 'training_programs' in catalog_data:
            for training in catalog_data['training_programs']:
                if all(key in training for key in ['name', 'description', 'duration_hours', 'cost', 'provider']):
                    cursor.execute("""
                        INSERT INTO training_program (name, description, duration_hours, cost, provider)
                        VALUES (?, ?, ?, ?, ?)
                    """, (training['name'], training['description'], 
                          training['duration_hours'], training['cost'], training['provider']))
                    training_ids[training['name']] = cursor.lastrowid
                    training_descriptions[training['name']] = training['description']
        
        print(f"✓ {len(training_ids)} programmes de formation créés")
        
        # Récupérer tous les employés avec leur date d'embauche
        cursor.execute("SELECT id, first_name, last_name, hire_date FROM employee")
        employees = cursor.fetchall()
        
        if not employees:
            print("Aucun employé trouvé. Assurez-vous d'avoir exécuté l'étape 2.")
            return
        
        # Lire le prompt pour l'attribution des formations
        with open('data_generation/prompts/05_training_assignment.txt', 'r', encoding='utf-8') as f:
            assignment_prompt_template = f.read()
        
        print("Attribution des formations aux employés...")
        
        total_training_records = 0
        total_skill_updates = 0
        
        for employee in employees:
            employee_name = f"{employee['first_name']} {employee['last_name']}"
            hire_date = employee['hire_date']
            hire_year = datetime.strptime(hire_date, '%Y-%m-%d').year
            
            # Générer des formations pour chaque année depuis l'embauche
            for training_year in range(hire_year, current_year + 1):
                training_date = generate_training_date(training_year, hire_date)
                
                if training_date is None:
                    continue
                
                # 0-2 formations par an
                num_trainings = random.choices([0, 1, 2], weights=[30, 50, 20])[0]
                
                if num_trainings == 0:
                    continue
                
                assignment_prompt = assignment_prompt_template.format(
                    employee_name=employee_name,
                    available_trainings=', '.join(training_ids.keys()),
                    budget_per_employee=company_profile['contexte_rh']['budget_formation'],
                    sector=company_profile['secteur'],
                    currency=company_profile.get('currency', 'XPF'),
                    language=company_profile['language'],
                    year=training_year
                )
                
                try:
                    assignment_data = generate_json(assignment_prompt)
                    
                    records_created = 0
                    if 'training_records' in assignment_data:
                        selected_trainings = assignment_data['training_records'][:num_trainings]
                        
                        for training_record in selected_trainings:
                            if 'training_name' in training_record:
                                training_name = training_record['training_name']
                                
                                if training_name in training_ids:
                                    score = training_record.get('score', random.randint(70, 95))
                                    
                                    cursor.execute("""
                                        INSERT INTO training_record (employee_id, training_program_id, completion_date, 
                                                                   score, satisfaction_rating, comments)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (employee['id'], training_ids[training_name], 
                                          training_date,
                                          score,
                                          training_record.get('satisfaction_rating', random.randint(3, 5)),
                                          training_record.get('comments', '')))
                                    
                                    # Mettre à jour les compétences
                                    update_employee_skills_from_training(
                                        cursor, employee['id'], training_name, 
                                        training_descriptions[training_name], score, config
                                    )
                                    total_skill_updates += 1
                                    records_created += 1
                    
                    total_training_records += records_created
                    print(f"✓ {records_created} formations → {employee_name} ({training_year})")
                    
                except LLMError:
                    print(f"⚠ Échec formations pour {employee_name} ({training_year})")
                    continue
        
        conn.commit()
        conn.close()
        
        print(f"✓ {total_training_records} enregistrements de formation créés")
        print(f"✓ {total_skill_updates} mises à jour de compétences effectuées")
        
    except LLMError as e:
        print(f"Erreur fatale: {e}")
        raise
    except Exception as e:
        print(f"Erreur lors de la génération des formations: {e}")
        raise