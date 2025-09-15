# =============================================================================
# etapes/e03_competences_referentiels.py
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config

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
    with open('prompts/03_skills_generation.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    prompt = prompt_template.format(
        sector=company_profile['secteur'],
        challenges=', '.join(company_profile['defis'])
    )
    
    print("Génération du référentiel de compétences...")
    response = generate_text(prompt)
    clean_response = strip_markdown_fences(response)
    
    try:
        skills_data = json.loads(clean_response)
        
        # Insérer les compétences
        skill_ids = {}
        for skill in skills_data['skills']:
            cursor.execute("""
                INSERT INTO skill (name, category)
                VALUES (?, ?)
            """, (skill['name'], skill['category']))
            skill_ids[skill['name']] = cursor.lastrowid
        
        print(f"✓ {len(skills_data['skills'])} compétences créées")
        
        # Récupérer tous les employés avec leurs postes
        cursor.execute("""
            SELECT e.id, e.first_name, e.last_name, p.title as position_title
            FROM employee e
            LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
            LEFT JOIN position p ON a.position_id = p.id
        """)
        employees = cursor.fetchall()
        
        # Générer les compétences pour chaque employé
        print("Attribution des compétences aux employés...")
        
        with open('prompts/03_employee_skills_assignment.txt', 'r', encoding='utf-8') as f:
            assignment_prompt_template = f.read()
        
        for employee in employees:
            assignment_prompt = assignment_prompt_template.format(
                employee_name=f"{employee['first_name']} {employee['last_name']}",
                position=employee['position_title'] or "Employee",
                available_skills=', '.join([s['name'] for s in skills_data['skills']]),
                sector=company_profile['secteur']
            )
            
            response = generate_text(assignment_prompt)
            clean_response = strip_markdown_fences(response)
            
            try:
                employee_skills = json.loads(clean_response)
                
                for skill_assignment in employee_skills['skills']:
                    skill_name = skill_assignment['skill']
                    level = skill_assignment['level']
                    
                    if skill_name in skill_ids:
                        cursor.execute("""
                            INSERT INTO employee_skill (employee_id, skill_id, level)
                            VALUES (?, ?, ?)
                        """, (employee['id'], skill_ids[skill_name], level))
                        
            except json.JSONDecodeError:
                print(f"Erreur parsing compétences pour {employee['first_name']} {employee['last_name']}")
                continue
        
        conn.commit()
        conn.close()
        
        print("✓ Compétences attribuées aux employés")
        
    except Exception as e:
        print(f"Erreur lors de la génération des compétences: {e}")
