# =============================================================================
# src/e00_initialisation.py
# =============================================================================

from database import create_database

def run(schema_path):
    """
    Étape 0: Initialisation de la base de données
    """
    print("Étape 0: Initialisation de la base de données")
    create_database(schema_path)
    print("✓ Base de données initialisée")
