# src/e02_population_hierarchie.py (version réécrite)
from utils.database import get_connection, close_connection
from utils.llm_client import generate_json, LLMError
from config import get_config
from utils.names_generator import NamesGenerator
from datetime import datetime, timedelta
import random
import sqlite3

# La fonction _create_employee reste quasi identique à la version précédente

def _fetch_position_hierarchy(cursor: sqlite3.Cursor) -> dict:
    """Récupère l'arbre complet des positions depuis la base de données."""
    cursor.execute("SELECT p.id, p.title, p.level, p.reports_to_position_id, u.name as unit_name FROM position p JOIN organizational_unit u ON p.unit_id = u.id")
    positions = {row['id']: dict(row) for row in cursor.fetchall()}
    
    if not positions:
        raise ValueError("Aucun poste trouvé dans la base de données. Exécutez l'étape 1.")
        
    # Construire l'arbre pour la traversée
    tree = {}
    for pos_id, pos_data in positions.items():
        parent_id = pos_data['reports_to_position_id']
        if parent_id is None: # Racine (CEO)
            tree[pos_id] = pos_data
        else:
            if 'children' not in positions[parent_id]:
                positions[parent_id]['children'] = []
            positions[parent_id]['children'].append(pos_data)
            
    return tree, positions

def _populate_initial_structure(cursor: sqlite3.Cursor, tree: dict, names_gen: NamesGenerator, config: dict, prompt_template: str):
    """Peuple la structure en créant un employé par poste (traversée descendante)."""
    print("Phase 2a: Initialisation de la structure (1 employé par poste)...")
    
    employee_map = {}  # position_id -> employee_id
    manager_map = {}  # position_id -> manager_employee_id
    
    queue = [(node_id, None) for node_id in tree.keys()] # (position_id, manager_employee_id)
    
    while queue:
        pos_id, manager_id = queue.pop(0)
        
        pos_data = next(p for p in cursor.execute("SELECT * FROM position WHERE id = ?", (pos_id,)).fetchall())
        unit_name = cursor.execute("SELECT name FROM organizational_unit WHERE id = ?", (pos_data['unit_id'],)).fetchone()['name']

        # Utiliser la fonction _create_employee existante
        # (supposée définie dans ce fichier, comme dans la version précédente)
        emp_id, _, _ = _create_employee(
            cursor, names_gen, config, prompt_template,
            pos_data['title'], unit_name, manager_id
        )
        employee_map[pos_id] = emp_id
        
        # Si ce poste a des subordonnés, ajouter les enfants à la file
        children_query = "SELECT id FROM position WHERE reports_to_position_id = ?"
        children = [row['id'] for row in cursor.execute(children_query, (pos_id,)).fetchall()]
        for child_id in children:
            queue.append((child_id, emp_id))
            
    print(f"✓ {len(employee_map)} employés initiaux créés.")
    return employee_map

def _populate_remaining_employees(cursor: sqlite3.Cursor, config: dict, employee_map: dict, all_positions: dict, names_gen: NamesGenerator, prompt_template: str):
    """Peuple le reste des employés avec une répartition pondérée."""
    target_size = config['entreprise']['taille']
    remaining_to_create = target_size - len(employee_map)
    
    if remaining_to_create <= 0:
        print("La taille cible est déjà atteinte ou dépassée.")
        return

    print(f"\nPhase 2b: Création des {remaining_to_create} employés restants...")
    
    # Créer une liste pondérée de postes à pourvoir (favorisant les niveaux bas)
    level_weights = {
        "Junior": 10,
        "Individual Contributor": 8,
        "Senior Individual Contributor": 3,
        "Manager": 0, # Ne pas ajouter de managers supplémentaires
        "Executive": 0
    }
    
    positions_to_fill = []
    weights = []
    for pos_id, pos_data in all_positions.items():
        weight = level_weights.get(pos_data['level'], 1)
        if weight > 0:
            positions_to_fill.append(pos_data)
            weights.append(weight)

    if not positions_to_fill:
        print("⚠ Aucun poste de niveau subalterne à pourvoir.")
        return

    for i in range(remaining_to_create):
        # Choisir un poste à pourvoir en fonction des poids
        chosen_pos = random.choices(positions_to_fill, weights=weights, k=1)[0]
        
        # Trouver le manager pour ce poste
        manager_pos_id = chosen_pos['reports_to_position_id']
        manager_id = employee_map.get(manager_pos_id)
        
        if not manager_id:
            print(f"⚠ Manager non trouvé pour le poste {chosen_pos['title']}, impossible de créer l'employé.")
            continue
            
        _create_employee(
            cursor, names_gen, config, prompt_template,
            chosen_pos['title'], chosen_pos['unit_name'], manager_id
        )
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{remaining_to_create} créés")

def run():
    """
    Étape 2: Peuplement de la hiérarchie basée sur le blueprint existant.
    """
    print("Étape 2: Démarrage du peuplement de la hiérarchie")
    config = get_config()
    names_gen = NamesGenerator()
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        with open('prompts/02_employee_generation.txt', 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        _, all_positions = _fetch_position_hierarchy(cursor)
        
        # Phase 1: Créer 1 employé par poste
        initial_employee_map = _populate_initial_structure(cursor, tree, names_gen, config, prompt_template)
        
        # Phase 2: Remplir jusqu'à la taille cible
        _populate_remaining_employees(cursor, config, initial_employee_map, all_positions, names_gen, prompt_template)
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM employee")
        total_employees = cursor.fetchone()[0]
        print(f"\n✓ Peuplement terminé. Total de {total_employees} employés dans la base.")

    except Exception as e:
        print(f"\nErreur critique lors du peuplement: {e}")
        conn.rollback()
        raise
    finally:
        close_connection(conn)