# =============================================================================
# src/e03_competences_referentiels.py (version complète)
# =============================================================================

from core.database import get_connection
from data_generation.utils.llm_client import generate_json, LLMError
from core.config import get_config

def run():
    """
    Étape 3: Génération des compétences et référentiels
    Tables: skill, employee_skill
    """
    print("Étape 3: Génération des compétences et référentiels")
    
    config = get_config()
    company_profile = config['entreprise']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Lire le prompt pour les compétences
    with open('data_generation/prompts/03_skills_generation.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    prompt = prompt_template.format(
        sector=company_profile['secteur'],
        challenges=', '.join(company_profile['defis']),
        company_sector=company_profile['secteur'],
        location=company_profile['location'],
        region_culture=company_profile['region_culture'],
        company_culture=company_profile['culture'],
        language=company_profile['language'],
    )
    
    try:
        print("Génération du référentiel de compétences...")
        skills_data = generate_json(prompt)
        
        # Insérer les compétences
        skill_ids = {}
        if 'skills' in skills_data:
            for skill in skills_data['skills']:
                if 'name' in skill and 'category' in skill:
                    print(f"Création compétence: {skill['name']} ({skill['category']})")
                    cursor.execute("""
                        INSERT INTO skill (name, category)
                        VALUES (?, ?)
                    """, (skill['name'], skill['category']))
                    skill_ids[skill['name']] = cursor.lastrowid
        
        print(f"✓ {len(skill_ids)} compétences créées")
        
        # Récupérer tous les employés avec leurs postes
        cursor.execute("""
            SELECT e.id, e.first_name, e.last_name, p.title as position_title
            FROM employee e
            LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
            LEFT JOIN position p ON a.position_id = p.id
        """)
        employees = cursor.fetchall()
        
        if not employees:
            print("Aucun employé trouvé. Assurez-vous d'avoir exécuté l'étape 2.")
            return
        
        # Générer les compétences pour chaque employé
        print("Attribution des compétences aux employés...")
        
        with open('data_generation/prompts/03_employee_skills_assignment.txt', 'r', encoding='utf-8') as f:
            assignment_prompt_template = f.read()
        
        total_assignments = 0
        for employee in employees:
            assignment_prompt = assignment_prompt_template.format(
                employee_name=f"{employee['first_name']} {employee['last_name']}",
                position=employee['position_title'] or "Employee",
                available_skills=', '.join(skill_ids.keys()),
                sector=company_profile['secteur']
            )
            
            try:
                employee_skills_data = generate_json(assignment_prompt)
                # print(f"employee_skills_data: {employee_skills_data}")
                skills_assigned = 0
                if 'skills' in employee_skills_data:
                    for skill_assignment in employee_skills_data['skills']:
                        if 'skill_name' in skill_assignment and 'level' in skill_assignment:
                            skill_name = skill_assignment['skill_name']
                            level = skill_assignment['level']
                            
                            if skill_name in skill_ids:
                                cursor.execute("""
                                    INSERT INTO employee_skill (employee_id, skill_id, level)
                                    VALUES (?, ?, ?)
                                """, (employee['id'], skill_ids[skill_name], level))
                                skills_assigned += 1
                
                total_assignments += skills_assigned
                print(f"✓ {skills_assigned} compétences → {employee['first_name']} {employee['last_name']}")
                
            except LLMError:
                print(f"⚠ Échec attribution pour {employee['first_name']} {employee['last_name']}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"✓ {total_assignments} compétences attribuées au total")
        
    except LLMError as e:
        print(f"Erreur fatale: {e}")
        raise
    except Exception as e:
        print(f"Erreur: {e}")
        raise
