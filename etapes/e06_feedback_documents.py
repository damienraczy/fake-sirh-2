# =============================================================================
# etapes/e06_feedback_documents.py
# =============================================================================

import json
import os
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config
from datetime import datetime, timedelta
import random

def run():
    """
    Étape 6: Génération des feedback et documents
    Tables: feedback, document
    """
    print("Étape 6: Génération des feedback et documents")
    
    config = get_config()
    company_profile = config['entreprise']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Créer le répertoire pour les documents
    os.makedirs('data/documents', exist_ok=True)
    
    # Récupérer tous les employés avec leurs informations
    cursor.execute("""
        SELECT e.id, e.first_name, e.last_name, p.title as position_title,
               ou.name as unit_name
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
    """)
    employees = cursor.fetchall()
    
    # Lire les prompts
    with open('prompts/06_feedback_generation.txt', 'r', encoding='utf-8') as f:
        feedback_prompt_template = f.read()
    
    with open('prompts/06_document_generation.txt', 'r', encoding='utf-8') as f:
        document_prompt_template = f.read()
    
    print("Génération des feedback et documents...")
    
    for employee in employees:
        employee_name = f"{employee['first_name']} {employee['last_name']}"
        
        # Générer les feedback
        feedback_prompt = feedback_prompt_template.format(
            employee_name=employee_name,
            position=employee['position_title'] or "Employee",
            unit=employee['unit_name'] or "Unknown",
            culture=company_profile['culture'],
            sector=company_profile['secteur']
        )
        
        response = generate_text(feedback_prompt)
        clean_response = strip_markdown_fences(response)
        
        try:
            feedback_data = json.loads(clean_response)
            
            for feedback in feedback_data['feedback_entries']:
                # Générer une date de feedback dans les 3 derniers mois
                feedback_date = datetime.now() - timedelta(days=random.randint(1, 90))
                
                cursor.execute("""
                    INSERT INTO feedback (from_employee_id, to_employee_id, feedback_type, 
                                        content, feedback_date, context, is_anonymous)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (feedback.get('from_employee_id', employee['id']),
                      employee['id'],
                      feedback['feedback_type'],
                      feedback['content'],
                      feedback_date.strftime('%Y-%m-%d'),
                      feedback['context'],
                      feedback.get('is_anonymous', False)))
            
        except json.JSONDecodeError:
            print(f"Erreur parsing feedback pour {employee_name}")
        
        # Générer les documents
        document_prompt = document_prompt_template.format(
            employee_name=employee_name,
            position=employee['position_title'] or "Employee",
            sector=company_profile['secteur'],
            culture=company_profile['culture']
        )
        
        response = generate_text(document_prompt)
        clean_response = strip_markdown_fences(response)
        
        try:
            document_data = json.loads(clean_response)
            
            for doc in document_data['documents']:
                # Créer le fichier document
                filename = f"emp_{employee['id']}_{doc['document_type'].lower()}.txt"
                filepath = f"data/documents/{filename}"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(doc['content'])
                
                # Enregistrer en base
                cursor.execute("""
                    INSERT INTO document (employee_id, document_type, uri, creation_date)
                    VALUES (?, ?, ?, ?)
                """, (employee['id'], doc['document_type'], 
                      f"file:///{filepath}", datetime.now().strftime('%Y-%m-%d')))
            
        except json.JSONDecodeError:
            print(f"Erreur parsing documents pour {employee_name}")
    
    conn.commit()
    conn.close()
    
    print("✓ Feedback et documents générés")
