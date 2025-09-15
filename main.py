# main.py (mise à jour)
import sys
import os
import time
import argparse
from pathlib import Path
import shutil

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import load_config
from etapes import e00_initialisation as etape0
from etapes import e01_structure_organisationnelle as etape1
from etapes import e02_population_hierarchie as etape2
from etapes import e03_competences_referentiels as etape3
from etapes import e04_objectifs_performance as etape4
from etapes import e05_formations_developpement as etape5
from etapes import e06_feedback_documents as etape6
from utils.validation import validate_database

def run_all_steps():
    """
    Fonction principale qui orchestre l'exécution de toutes les étapes de génération.
    """
    ap = argparse.ArgumentParser(description="Générateur SIRH de démonstration")
    ap.add_argument("steps", nargs='*', help="Etapes à effectuer (0-6)", default=['0','1','2','3','4','5','6'])
    ap.add_argument("--yaml", required=False, help="Chemin du YAML de configuration", default="config.yaml")
    ap.add_argument("--sql", required=False, help="Chemin du schéma SQL SQLite", default="schema.sql")
    ap.add_argument("--raz", action="store_true", help="Supprimer la base existante avant de créer")
    ap.add_argument("--validate", action="store_true", help="Valider la cohérence après génération")
    args = ap.parse_args()

    if args.raz:
        db_path = Path("db")
        if db_path.exists():
            print(f"[RAZ] Suppression de la base existante: {db_path}")
            shutil.rmtree(db_path)
        data_path = Path("data")
        if data_path.exists() and data_path.is_dir():
            print(f"[RAZ] Suppression du répertoire data/")
            shutil.rmtree(data_path)

    start_time = time.time()
    print("================================================")
    print("= Générateur de Données SIRH Fictif - v2 =")
    print("================================================")

    load_config(config_path=args.yaml)

    steps = {
        '0': etape0.run,     # initialisation de la base
        '1': etape1.run,     # structure organisationnelle
        '2': etape2.run,     # population et hiérarchie
        '3': etape3.run,     # compétences et référentiels
        '4': etape4.run,     # objectifs et performance
        '5': etape5.run,     # formations et développement
        '6': etape6.run      # feedback et documents
    }

    try:
        for step_num in args.steps:
            if step_num == '0':
                print(f"\n================== ÉTAPE {step_num} ==================")
                steps[step_num](schema_path=args.sql)
            else:
                print(f"\n================== ÉTAPE {step_num} ==================")
                steps[step_num]()

        if args.validate:
            print("\n================== VALIDATION ==================")
            validate_database()

    except Exception as e:
        print(f"\nERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()

    end_time = time.time()
    print(f"\nGénération terminée en {end_time - start_time:.2f} secondes.")

if __name__ == "__main__":
    run_all_steps()
