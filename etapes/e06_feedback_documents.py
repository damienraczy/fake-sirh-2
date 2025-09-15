# =============================================================================
# etapes/e06_feedback_documents.py (version complète)
# =============================================================================

import os
from database import get_connection
from llm_client import generate_json, LLMError
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
    
    if not employees:
        print("Aucun employé trouvé. Assurez-vous d'avoir exécuté l'étape 2.")
        return
    
    # Lire les prompts
    with open('prompts/06_feedback_generation.txt', 'r', encoding='utf-8') as f:
        feedback_prompt_template = f.read()
    
    with open('prompts/06_document_generation.txt', 'r', encoding='utf-8') as f:
        document_prompt_template = f.read()
    
    print("Génération des feedback et documents...")
    
    total_feedback = 0
    total_documents = 0
    
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
        
        try:
            feedback_data = generate_json(feedback_prompt)
            
            feedback_count = 0
            if 'feedback_entries' in feedback_data:
                for feedback in feedback_data['feedback_entries']:
                    if 'feedback_type' in feedback and 'content' in feedback:
                        # Générer une date de feedback dans les 3 derniers mois
                        feedback_date = datetime.now() - timedelta(days=random.randint(1, 90))
                        
                        cursor.execute("""
                            INSERT INTO feedback (from_employee_id, to_employee_id, feedback_type, 
                                                content, feedback_date, context, is_anonymous)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (feedback.get('from_employee_id') or random.randint(1, len(employees)),
                              employee['id'],
                              feedback['feedback_type'],
                              feedback['content'],
                              feedback_date.strftime('%Y-%m-%d'),
                              feedback.get('context', 'Daily Work'),
                              feedback.get('is_anonymous', False)))
                        feedback_count += 1
            
            total_feedback += feedback_count
            print(f"✓ {feedback_count} feedback → {employee_name}")
            
        except LLMError:
            print(f"⚠ Échec feedback pour {employee_name}")
        
        # Générer les documents
        document_prompt = document_prompt_template.format(
            employee_name=employee_name,
            position=employee['position_title'] or "Employee",
            sector=company_profile['secteur'],
            culture=company_profile['culture']
        )
        
        try:
            document_data = generate_json(document_prompt)
            
            document_count = 0
            if 'documents' in document_data:
                for doc in document_data['documents']:
                    if 'document_type' in doc and 'content' in doc:
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
                        document_count += 1
            
            total_documents += document_count
            print(f"✓ {document_count} documents → {employee_name}")
            
        except LLMError:
            print(f"⚠ Échec documents pour {employee_name}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ {total_feedback} feedback créés")
    print(f"✓ {total_documents} documents créés")
