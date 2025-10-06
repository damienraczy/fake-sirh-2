# tests/generate_golden_dataset.py (version dynamique et robuste)
import sqlite3
import json
import os
import sys
import random

# Ajouter le répertoire parent au path pour trouver les modules utils et config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from core.database import get_db_path

def find_employee_with_manager(cursor):
    """
    Trouve un employé (non-manager) au hasard qui a un manager et retourne leurs informations.
    """
    cursor.execute("""
        SELECT 
            e.first_name || ' ' || e.last_name as employee_name,
            m.first_name || ' ' || m.last_name as manager_name
        FROM employee e
        JOIN employee m ON e.manager_id = m.id
        WHERE e.id NOT IN (SELECT DISTINCT manager_id FROM employee WHERE manager_id IS NOT NULL)
        ORDER BY RANDOM()
        LIMIT 1
    """)
    result = cursor.fetchone()
    return (result[0], result[1]) if result else (None, None)

def find_employee_with_review(cursor):
    """
    Trouve un employé au hasard qui a une évaluation de performance et retourne son nom.
    """
    cursor.execute("""
        SELECT e.first_name || ' ' || e.last_name as employee_name
        FROM employee e
        JOIN performance_review pr ON e.id = pr.employee_id
        ORDER BY RANDOM()
        LIMIT 1
    """)
    result = cursor.fetchone()
    return result[0] if result else None

def get_production_employee_count(cursor):
    """Récupère le nombre d'employés dans les départements de production."""
    cursor.execute("""
        SELECT COUNT(DISTINCT a.employee_id)
        FROM assignment a
        JOIN organizational_unit ou ON a.unit_id = ou.id
        WHERE a.end_date IS NULL AND (ou.name LIKE '%Production%' OR ou.name LIKE '%atelier%')
    """)
    result = cursor.fetchone()
    return result[0] if result else 0

def generate_dataset():
    """Génère le golden dataset en découvrant des cas de test dans la base de données."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ Erreur : La base de données n'a pas été trouvée à l'emplacement {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    golden_dataset = []
    print("🔍 Découverte des cas de test dans la base de données...")

    # --- Cas de test 1 : Hiérarchie (GRAPH) ---
    employee_for_graph_test, manager_name = find_employee_with_manager(cursor)
    if employee_for_graph_test and manager_name:
        golden_dataset.append({
            "question_id": "GRAPH_001",
            "question": f"Qui est le manager de {employee_for_graph_test} ?",
            "expected_route": "GRAPH",
            "expected_keywords": manager_name.split()
        })
        print(f"  -> Cas 'GRAPH' trouvé : Le manager de {employee_for_graph_test} est {manager_name}.")
    else:
        print("  -> ⚠️ Impossible de trouver un employé avec un manager pour le test GRAPH.")

    # --- Cas de test 2 : Comptage (SQL) ---
    prod_count = get_production_employee_count(cursor)
    golden_dataset.append({
        "question_id": "SQL_001",
        "question": "Combien d'employés travaillent à la production ?",
        "expected_route": "SQL",
        "expected_keywords": [str(prod_count)]
    })
    print(f"  -> Cas 'SQL' trouvé : {prod_count} employés travaillent à la production.")

    # --- Cas de test 3 : Recherche sémantique (VECTOR) ---
    employee_for_vector_test = find_employee_with_review(cursor)
    if employee_for_vector_test:
        golden_dataset.append({
            "question_id": "VECTOR_001",
            "question": f"Fais-moi un résumé du dernier entretien de performance de {employee_for_vector_test}.",
            "expected_route": "VECTOR",
            "expected_keywords": employee_for_vector_test.split() + ["score", "évaluation", "commentaires"]
        })
        print(f"  -> Cas 'VECTOR' trouvé : Recherche de l'entretien de {employee_for_vector_test}.")
    else:
        print("  -> ⚠️ Impossible de trouver un employé avec une évaluation pour le test VECTOR.")

    conn.close()

    # Sauvegarde du fichier
    output_path = os.path.join(current_dir, 'golden_dataset.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(golden_dataset, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Golden dataset dynamique généré avec succès dans {output_path}")

if __name__ == "__main__":
    # Assurez-vous que la configuration est chargée pour que get_db_path() fonctionne
    sys.path.insert(0, parent_dir)
    from core.config import load_config
    load_config('config.yaml')
    
    generate_dataset()
    