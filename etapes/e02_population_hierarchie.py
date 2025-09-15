# =============================================================================
# etapes/e02_population_hierarchie.py mis à jour
# =============================================================================

import json
from database import get_connection
from llm_client import generate_text
from utils_llm import strip_markdown_fences
from config import get_config
from utils.names_generator import NamesGenerator
from datetime import datetime, timedelta
import random

def run():
    """
    Étape 2: Génération de la population et hiérarchie
    Tables: employee, assignment
    """
    print("Étape 2: Génération de la population et hiérarchie")
    
    config = get_config()
    company_profile = config['entreprise']
    
    # Initialiser le générateur de noms
    names_gen = NamesGenerator()
    ratio_hommes = company_profile['contexte_rh']['ratio_hommes']
    domaine_email = company_profile['technique']['domaine_email']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Récupérer les unités et positions existantes
    cursor.execute("SELECT id, name FROM organizational_unit")
    units = cursor.fetchall()
    
    cursor.execute("SELECT id, title FROM position")
    positions = cursor.fetchall()
    
    # Lire le prompt pour la génération d'employés
    with open('prompts/02_employee_generation.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    def create_employee_with_local_name(position_title: str, unit_name: str, is_manager: bool = False, manager_id=None):
        """Crée un employé avec nom local et données LLM"""
        
        # Déterminer le genre selon le ratio
        is_male = random.random() < ratio_hommes
        
        # Générer nom unique
        prenom, nom, email_base = names_gen.generate_unique_name(is_male)
        email = f"{email_base}@{domaine_email}"
        
        # Générer les données contextuelles via LLM
        context_prompt = prompt_template.format(
            position=position_title,
            unit=unit_name,
            sector=company_profile['secteur'],
            culture=company_profile['culture'],
            avg_tenure=company_profile['contexte_rh']['anciennete_moyenne'],
            count=1,
            first_name=prenom,
            last_name=nom,
            email=email
        )
        
        response = generate_text(context_prompt)
        clean_response = strip_markdown_fences(response)
        
        try:
            employee_data = json.loads(clean_response)
            employee_info = employee_data['employees'][0]
            
            # Utiliser les données locales + infos LLM
            hire_date = employee_info.get('hire_date', 
                (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d'))
            
            # Insérer en base
            cursor.execute("""
                INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
                VALUES (?, ?, ?, ?, ?)
            """, (prenom, nom, email, hire_date, manager_id))
            
            return cursor.lastrowid, prenom, nom
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Erreur parsing LLM pour {prenom} {nom}, utilisation des données par défaut")
            
            # Fallback avec données par défaut
            hire_date = (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d')
            
            cursor.execute("""
                INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
                VALUES (?, ?, ?, ?, ?)
            """, (prenom, nom, email, hire_date, manager_id))
            
            return cursor.lastrowid, prenom, nom
    
    try:
        # Créer le DG
        print("Génération du directeur général...")
        ceo_position = next((p for p in positions if "CEO" in p['title'] or "Director" in p['title']), 
                           positions[0] if positions else None)
        
        if ceo_position:
            dg_id, dg_prenom, dg_nom = create_employee_with_local_name(
                ceo_position['title'], 
                "Direction Générale", 
                is_manager=True
            )
            print(f"✓ DG créé: {dg_prenom} {dg_nom}")
        else:
            raise Exception("Aucune position de direction trouvée")
        
        # Créer les managers de département
        managers = {}
        manager_positions = [p for p in positions if "Manager" in p['title'] or "Head" in p['title']]
        
        for unit in units:
            if unit['name'] not in ["Direction Générale", "Executive"]:
                manager_pos = random.choice(manager_positions) if manager_positions else positions[0]
                
                manager_id, manager_prenom, manager_nom = create_employee_with_local_name(
                    manager_pos['title'],
                    unit['name'],
                    is_manager=True,
                    manager_id=dg_id
                )
                
                managers[unit['id']] = manager_id
                print(f"✓ Manager {unit['name']}: {manager_prenom} {manager_nom}")
                
                # Créer l'affectation du manager
                cursor.execute("""
                    INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                    VALUES (?, ?, ?, ?, NULL)
                """, (manager_id, manager_pos['id'], unit['id'], 
                      (datetime.now() - timedelta(days=random.randint(100, 800))).strftime('%Y-%m-%d')))
        
        # Créer les employés restants
        remaining_employees = company_profile['taille'] - len(managers) - 1
        employees_per_unit = max(1, remaining_employees // len(units))
        
        print(f"Génération de {remaining_employees} employés...")
        
        for unit in units:
            if unit['id'] in managers:  # Unités avec managers
                unit_positions = [p for p in positions 
                                if "Manager" not in p['title'] 
                                and "Director" not in p['title'] 
                                and "CEO" not in p['title']]
                
                if not unit_positions:
                    unit_positions = [positions[0]]  # Fallback
                
                for _ in range(employees_per_unit):
                    pos = random.choice(unit_positions)
                    manager_id = managers[unit['id']]
                    
                    emp_id, emp_prenom, emp_nom = create_employee_with_local_name(
                        pos['title'],
                        unit['name'],
                        manager_id=manager_id
                    )
                    
                    # Créer l'affectation
                    cursor.execute("""
                        INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                        VALUES (?, ?, ?, ?, NULL)
                    """, (emp_id, pos['id'], unit['id'], 
                          (datetime.now() - timedelta(days=random.randint(30, 600))).strftime('%Y-%m-%d')))
        
        # Créer l'affectation du DG
        if ceo_position:
            dg_unit = next((u for u in units if "Direction" in u['name'] or "Executive" in u['name']), 
                          units[0] if units else None)
            if dg_unit:
                cursor.execute("""
                    INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                    VALUES (?, ?, ?, ?, NULL)
                """, (dg_id, ceo_position['id'], dg_unit['id'], 
                      (datetime.now() - timedelta(days=random.randint(365, 1500))).strftime('%Y-%m-%d')))
        
        conn.commit()
        
        # Statistiques finales
        cursor.execute("SELECT COUNT(*) FROM employee")
        total_employees = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM employee e JOIN assignment a ON e.id = a.employee_id WHERE a.end_date IS NULL")
        assigned_employees = cursor.fetchone()[0]
        
        print(f"✓ {total_employees} employés créés au total")
        print(f"✓ {assigned_employees} employés avec affectations")
        print(f"✓ Ratio hommes/femmes appliqué: {ratio_hommes*100:.0f}%/{(1-ratio_hommes)*100:.0f}%")
        
    except Exception as e:
        print(f"Erreur lors de la génération: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
