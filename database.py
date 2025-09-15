# database.py
import sqlite3
import os
from config import get_config

def get_db_path():
    """Construit le chemin complet vers le fichier de la base de données."""
    cfg = get_config()
    db_dir = cfg['entreprise']['base_de_données']['chemin']
    db_name = cfg['entreprise']['base_de_données']['nom']
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, db_name)

def create_database(schema_path='IOD_Core_FR_schema.sql'):
    """
    Crée une base de données vide à partir du schéma SQL.
    Supprime l'ancienne base de données si elle existe.
    """
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Ancienne base de données '{db_path}' supprimée.")

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()
        print(f"Base de données créée avec succès à l'emplacement : '{db_path}'.")
    except FileNotFoundError:
        print(f"Erreur : Le fichier de schéma '{schema_path}' est introuvable.")
        exit(1)
    except sqlite3.Error as e:
        print(f"Erreur SQLite lors de la création de la base de données: {e}")
        exit(1)

def get_connection():
    """
    Retourne une connexion à la base de données avec les clés étrangères activées.
    """
    db_path = get_db_path()
    try:
        print(f"Connexion à la base de données à l'emplacement : '{db_path}'")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Erreur de connexion à la base de données: {e}")
        exit(1)