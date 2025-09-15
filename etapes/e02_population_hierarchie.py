# =============================================================================
# etapes/e02_population_hierarchie.py (version complète)
# =============================================================================

from database import get_connection
from llm_client import generate_json, LLMError
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
    
    if not units or not positions:
        print("Erreur: Aucune unité ou position trouvée. Exécutez d'abord l'étape 1.")
        return
    
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
        
        # Tentative avec LLM (avec retry automatique)
        try:
            employee_data = generate_json(context_prompt)
            
            if 'employees' in employee_data and len(employee_data['employees']) > 0:
                employee_info = employee_data['employees'][0]
                hire_date = employee_info.get('hire_date', 
                    (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d'))
                print(f"✓ Contexte LLM généré pour {prenom} {nom}")
            else:
                raise Exception("Structure JSON invalide")
                
        except (LLMError, Exception) as e:
            print(f"⚠ Fallback pour {prenom} {nom}: {e}")
            # Fallback avec données par défaut
            hire_date = (datetime.now() - timedelta(days=random.randint(30, 1000))).strftime('%Y-%m-%d')
        
        # Insérer en base
        cursor.execute("""
            INSERT INTO employee (first_name, last_name, email, hire_date, manager_id)
            VALUES (?, ?, ?, ?, ?)
        """, (prenom, nom, email, hire_date, manager_id))
        
        return cursor.lastrowid, prenom, nom
    
    try:
        # Générer le directeur général d'abord
        print("Génération du directeur général...")
        
        # Trouver une position de direction
        ceo_position = next((p for p in positions if any(word in p['title'].upper() 
                           for word in ['CEO', 'DIRECTOR', 'GENERAL', 'CHIEF'])), None)
        
        if not ceo_position:
            # Fallback: prendre la première position
            ceo_position = positions[0]
            print(f"Aucune position de direction trouvée, utilisation de: {ceo_position['title']}")
        
        dg_id, dg_prenom, dg_nom = create_employee_with_local_name(
            ceo_position['title'], 
            "Direction Générale",
            is_manager=True
        )
        print(f"✓ DG créé: {dg_prenom} {dg_nom}")
        
        # Générer les managers de département
        print("Génération des managers de département...")
        managers = {}
        manager_positions = [p for p in positions if any(word in p['title'].upper() 
                           for word in ['MANAGER', 'HEAD', 'LEAD', 'SUPERVISOR'])]
        
        if not manager_positions:
            # Fallback: utiliser des positions génériques
            manager_positions = [p for p in positions if p['id'] != ceo_position['id']][:5]
        
        units_with_managers = [u for u in units if u['name'] not in ["Direction Générale", "Executive"]]
        
        for unit in units_with_managers:
            if manager_positions:
                manager_pos = random.choice(manager_positions)
            else:
                manager_pos = random.choice(positions)
            
            manager_id, manager_prenom, manager_nom = create_employee_with_local_name(
                manager_pos['title'],
                unit['name'],
                is_manager=True,
                manager_id=dg_id
            )
            
            managers[unit['id']] = manager_id
            print(f"✓ Manager {unit['name']}: {manager_prenom} {manager_nom}")
            
            # Créer l'affectation du manager
            manager_hire_date = (datetime.now() - timedelta(days=random.randint(100, 800))).strftime('%Y-%m-%d')
            cursor.execute("""
                INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                VALUES (?, ?, ?, ?, NULL)
            """, (manager_id, manager_pos['id'], unit['id'], manager_hire_date))
        
        # Générer les employés restants
        print("Génération des employés...")
        total_target = company_profile['taille']
        current_count = len(managers) + 1  # +1 pour le DG
        remaining_employees = max(0, total_target - current_count)
        
        if remaining_employees > 0:
            # Répartir les employés entre les unités qui ont des managers
            employees_per_unit = max(1, remaining_employees // len(managers)) if managers else 0
            
            print(f"Génération de {remaining_employees} employés restants...")
            
            for unit in units_with_managers:
                if unit['id'] in managers:
                    # Positions pour les employés (pas de managers)
                    unit_positions = [p for p in positions 
                                    if not any(word in p['title'].upper() 
                                             for word in ['MANAGER', 'DIRECTOR', 'CEO', 'HEAD', 'CHIEF'])]
                    
                    if not unit_positions:
                        # Fallback: utiliser toutes les positions sauf celle du DG
                        unit_positions = [p for p in positions if p['id'] != ceo_position['id']]
                    
                    manager_id = managers[unit['id']]
                    
                    # Créer les employés pour cette unité
                    employees_for_this_unit = min(employees_per_unit, remaining_employees)
                    
                    for i in range(employees_for_this_unit):
                        if unit_positions:
                            pos = random.choice(unit_positions)
                        else:
                            pos = random.choice(positions)
                        
                        emp_id, emp_prenom, emp_nom = create_employee_with_local_name(
                            pos['title'],
                            unit['name'],
                            manager_id=manager_id
                        )
                        
                        # Créer l'affectation
                        emp_hire_date = (datetime.now() - timedelta(days=random.randint(30, 600))).strftime('%Y-%m-%d')
                        cursor.execute("""
                            INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
                            VALUES (?, ?, ?, ?, NULL)
                        """, (emp_id, pos['id'], unit['id'], emp_hire_date))
                        
                        remaining_employees -= 1
                        if remaining_employees <= 0:
                            break
                
                if remaining_employees <= 0:
                    break
        
        # Créer l'affectation du DG
        print("Affectation du directeur général...")
        dg_unit = next((u for u in units if any(word in u['name'].upper() 
                       for word in ['DIRECTION', 'EXECUTIVE', 'GENERAL'])), units[0])
        
        dg_hire_date = (datetime.now() - timedelta(days=random.randint(365, 1500))).strftime('%Y-%m-%d')
        cursor.execute("""
            INSERT INTO assignment (employee_id, position_id, unit_id, start_date, end_date)
            VALUES (?, ?, ?, ?, NULL)
        """, (dg_id, ceo_position['id'], dg_unit['id'], dg_hire_date))
        
        conn.commit()
        
        # Statistiques finales
        cursor.execute("SELECT COUNT(*) FROM employee")
        total_employees = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM employee e 
            JOIN assignment a ON e.id = a.employee_id 
            WHERE a.end_date IS NULL
        """)
        assigned_employees = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM employee 
            WHERE manager_id IS NULL
        """)
        ceo_count = cursor.fetchone()[0]
        
        print(f"\n=== STATISTIQUES ===")
        print(f"✓ {total_employees} employés créés au total")
        print(f"✓ {assigned_employees} employés avec affectations actives")
        print(f"✓ {ceo_count} directeur général (manager_id = NULL)")
        print(f"✓ {len(managers)} managers de département")
        print(f"✓ Ratio hommes/femmes appliqué: {ratio_hommes*100:.0f}%/{(1-ratio_hommes)*100:.0f}%")
        print(f"✓ Domaine email: @{domaine_email}")
        
        # Vérification hiérarchique
        cursor.execute("""
            SELECT COUNT(*) FROM employee 
            WHERE manager_id IS NOT NULL
        """)
        employees_with_manager = cursor.fetchone()[0]
        print(f"✓ {employees_with_manager} employés avec un manager")
        
    except Exception as e:
        print(f"Erreur lors de la génération: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()