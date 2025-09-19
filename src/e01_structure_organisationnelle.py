# src/e01_structure_organisationnelle.py (simplifié)
from utils.database import get_connection, close_connection
from config import get_config

def run():
    """
    Étape 1: Crée les unités organisationnelles vides.
    """
    print("Étape 1: Création des unités organisationnelles")
    config = get_config()
    company_profile = config['entreprise']
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Insérer uniquement les départements
        depts = company_profile['structure_organisationnelle']['departements']
        for dept_name in depts:
            cursor.execute(
                "INSERT INTO organizational_unit (name, description) VALUES (?, ?)",
                (dept_name, f"Département {dept_name}")
            )
        
        conn.commit()
        print(f"✓ {len(depts)} unités organisationnelles créées.")
        
    except Exception as e:
        print(f"Erreur lors de la création des unités: {e}")
        conn.rollback()
    finally:
        close_connection(conn)