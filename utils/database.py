# database.py (version corrigée)
import sqlite3
import os
import atexit

import sys
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from config import get_config

# Pool de connexions pour éviter les verrous
_connection_pool = []

def get_db_path():
    """Construit le chemin complet vers le fichier de la base de données."""
    cfg = get_config()
    db_dir = cfg['entreprise']['base_de_données']['chemin']
    db_name = cfg['entreprise']['base_de_données']['nom']
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, db_name)

def create_database(schema_path):
    """
    Crée une base de données vide à partir du schéma SQL.
    Supprime l'ancienne base de données si elle existe.
    """
    db_path = get_db_path()
    if os.path.exists(db_path):
        # Fermer toutes les connexions ouvertes
        cleanup_connections()
        os.remove(db_path)
        print(f"Ancienne base de données '{db_path}' supprimée.")

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = sqlite3.connect(db_path, timeout=30.0)
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
    Utilise un timeout pour éviter les verrous.
    """
    db_path = get_db_path()
    try:
        print(f"Connexion à la base de données à l'emplacement : '{db_path}'")
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")  # Améliore la concurrence
        
        # Ajouter au pool pour nettoyage
        _connection_pool.append(conn)
        
        return conn
    except sqlite3.Error as e:
        print(f"Erreur de connexion à la base de données: {e}")
        exit(1)

def close_connection(conn):
    """Ferme proprement une connexion."""
    try:
        if conn in _connection_pool:
            _connection_pool.remove(conn)
        conn.close()
    except Exception as e:
        print(f"Erreur lors de la fermeture de connexion: {e}")

def cleanup_connections():
    """Ferme toutes les connexions ouvertes."""
    global _connection_pool
    for conn in _connection_pool[:]:  # Copie de la liste
        try:
            conn.close()
        except:
            pass
    _connection_pool.clear()

# Nettoyer les connexions à la sortie du programme
atexit.register(cleanup_connections)