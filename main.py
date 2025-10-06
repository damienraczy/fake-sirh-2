# =============================================================================
# main.py étendu - SIRH + RAG FastAPI (version courte)
# =============================================================================

import sys
import os
import argparse
from pathlib import Path
import shutil
import subprocess

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.config import load_config, get_config
from data_generation.steps import e00_initialisation as etape0
from data_generation.steps import e01_structure_organisationnelle as etape1
from data_generation.steps import e02_population_hierarchie as etape2
from data_generation.steps import e03_competences_referentiels as etape3
from data_generation.steps import e04_objectifs_performance as etape4
from data_generation.steps import e05_formations_developpement as etape5
from data_generation.steps import e06_feedback_documents as etape6
from data_generation.utils.validation import validate_database
from graph_sync.core.sync_manager import SyncManager

def run_graph_sync():
    """Étape 9: Synchronisation vers Neo4j"""
    print("\n=== ÉTAPE 9: Synchronisation Neo4j ===")
    
    try:
        
        # Récupérer le chemin de la base SQLite depuis la config
        config = get_config()
        db_path = f"{config['entreprise']['base_de_données']['chemin']}/{config['entreprise']['base_de_données']['nom']}"
        
        # Synchronisation
        sync_manager = SyncManager()
        sync_manager.sync_full_replace(db_path)
        
        print("✅ Synchronisation Neo4j terminée")
        
    except ImportError:
        print("⚠️ Module rdb2graph non disponible. Installez les dépendances Neo4j.")
    except Exception as e:
        print(f"❌ Erreur synchronisation Neo4j: {e}")


def run_rag_indexation():
    """Étape 7: Indexation RAG"""
    print("Étape 7: Indexation RAG des données")
    try:
        from rag.chain import SIRHRAGChain
        from rag.config import RAGConfig
        
        base_config = get_config()
        rag_config = RAGConfig.from_base_config(base_config)
        rag_chain = SIRHRAGChain(rag_config)
        
        print("✅ Système RAG initialisé et indexé")
        
    except ImportError:
        print("⚠️ Dépendances RAG manquantes. Installez: pip install fastapi uvicorn langchain sentence-transformers chromadb")
    except Exception as e:
        print(f"❌ Erreur indexation RAG: {e}")

def launch_rag_api(port, config_file):
    """Lance l'API RAG"""
    
    os.environ['FAKE_SIRH_2_CONFIG_FILE'] = config_file

    try:
        print(f"🚀 Lancement API RAG sur http://localhost:{port}")
        subprocess.run([sys.executable, "-m", "uvicorn", "rag.api:app", f"--port={port}", "--reload"])
    except Exception as e:
        print(f"❌ Erreur lancement API: {e}")

def main():
    ap = argparse.ArgumentParser(description="Générateur SIRH + RAG")
    # ap.add_argument("steps", nargs='*', help="Étapes (0-7)", default=['0','1','2','3','4','5','6'])
    ap.add_argument("steps", nargs='*', help="Étapes (0-7)")
    ap.add_argument("--yaml", default="config.yaml", help="Config YAML")
    ap.add_argument("--sql", default="schema.sql", help="Schéma SQL") 
    ap.add_argument("--raz", action="store_true", help="Reset base")
    ap.add_argument("--validate", action="store_true", help="Valider")
    ap.add_argument("--start-api", action="store_true", help="Lancer API RAG")
    ap.add_argument("--port", type=int, default=8000, help="Port API")
    
    args = ap.parse_args()

    if args.raz:
        for path in ["db", "data"]:
            if Path(path).exists():
                shutil.rmtree(path)
                print(f"[RAZ] {path} supprimé")

    print("🏢 Générateur SIRH + RAG FastAPI")

    os.environ['FAKE_SIRH_2_CONFIG_FILE'] = args.yaml

    load_config(config_path=args.yaml)

    steps = {
        '0': lambda: etape0.run(schema_path=args.sql, ),
        '1': etape1.run,
        '2': etape2.run,
        '3': etape3.run,
        '4': etape4.run,
        '5': etape5.run,
        '6': etape6.run,
        '7': run_rag_indexation,
        '8': run_graph_sync  # Nouvelle étape
    }

    # Exécution des étapes
    for step in args.steps:
        if step in steps:
            print(f"\n=== ÉTAPE {step} ===")
            steps[step]()

    if args.validate:
        print("\n=== VALIDATION ===")
        validate_database()

    if args.start_api:
        print("\n=== LANCEMENT API ===")
        launch_rag_api(args.port, args.yaml)

if __name__ == "__main__":
    main()