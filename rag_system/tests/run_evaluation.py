# tests/run_evaluation.py
import json
import os
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path pour que les imports fonctionnent
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
grand_parent_dir = os.path.dirname(parent_dir)
sys.path.insert(0, grand_parent_dir)

from core.config import load_config, get_config
from rag.chain import SIRHRAGChain
from rag.config import RAGConfig

# --- Fonctions de validation ---

def check_route(test_case, result):
    """Vérifie si la route choisie est la bonne."""
    expected = test_case['expected_route']
    actual = result['route']
    # Gérer les cas de fallback (ex: "SQL_FALLBACK_VECTOR" commence par "SQL")
    return actual.startswith(expected)

def check_keywords(test_case: str, result: list):
    """
    Vérifie si la réponse contient les éléments attendus.
    Pour les tests VECTOR, on est plus flexible : on vérifie si au moins
    les mots-clés principaux (noms propres) sont présents.
    """
    answer = result['answer'].lower()
    keywords = [str(k).lower() for k in test_case['expected_keywords']]

    # Pour les tests non-VECTOR, tous les mots-clés doivent être présents
    if test_case['expected_route'] != 'VECTOR':
        return all(keyword in answer for keyword in keywords)
    
    # Pour les tests VECTOR, la réponse peut être formulée de diverses manières.
    # On vérifie seulement la présence des noms propres pour s'assurer que le bon document a été trouvé.
    # Ici, on considère que les deux premiers mots-clés sont le prénom et le nom.
    if len(keywords) >= 2:
        return keywords[0] in answer and keywords[1] in answer
    
    return False

# --- Script principal ---

def run_tests():
    """Charge le dataset, initialise le RAG et lance les tests."""
    print("🚀 Démarrage de l'évaluation automatisée du RAG...")

    # 1. Charger la configuration
    config_path = os.path.join(grand_parent_dir, 'config.yaml')
    load_config(config_path)
    base_config = get_config()
    rag_config = RAGConfig.from_base_config(base_config)

    # 2. Charger le Golden Dataset
    dataset_path = os.path.join(current_dir, 'golden_dataset.json')
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        print(f"✅ Golden Dataset chargé avec {len(dataset)} cas de test.")
    except FileNotFoundError:
        print(f"❌ Erreur : Fichier 'golden_dataset.json' introuvable.")
        print("   Veuillez d'abord le générer avec 'python tests/generate_golden_dataset.py'")
        return

    # 3. Initialiser la chaîne RAG
    print("\nINITIALISATION DE LA CHAINE RAG...")
    rag_chain = SIRHRAGChain(rag_config)
    print("...CHAINE RAG INITIALISÉE.\n")

    # 4. Exécuter les tests
    results = []
    total_tests = len(dataset)
    passed_tests = 0

    print("--- LANCEMENT DES TESTS ---")
    for i, test_case in enumerate(dataset):
        print(f"\n🧪 Test {i + 1}/{total_tests} : ID = {test_case['question_id']}")
        print(f"   Question : \"{test_case['question']}\"")
        
        start_time = time.time()
        rag_result = rag_chain.query(test_case['question'])
        latency = time.time() - start_time

        # Évaluation
        route_ok = check_route(test_case, rag_result)
        keywords_ok = check_keywords(test_case, rag_result)
        test_passed = route_ok and keywords_ok

        if test_passed:
            passed_tests += 1
            print(f"   ➡️ Résultat : ✅ PASS")
        else:
            print(f"   ➡️ Résultat : ❌ FAIL")

        # Affichage des détails en cas d'échec
        if not route_ok:
            print(f"     - Erreur de routage : Attendu='{test_case['expected_route']}', Obtenu='{rag_result['route']}'")
        if not keywords_ok:
            print(f"     - Mots-clés manquants. Attendu : {test_case['expected_keywords']}")
            print(f"     - Réponse obtenue : \"{rag_result['answer'][:150]}...\"")

        results.append({
            "id": test_case['question_id'],
            "passed": test_passed,
            "latency": f"{latency:.2f}s"
        })
    
    # 5. Afficher le rapport final
    print("\n\n--- RAPPORT D'ÉVALUATION ---")
    print(f"Total des tests : {total_tests}")
    print(f"Tests réussis   : {passed_tests} ({(passed_tests/total_tests)*100:.2f}%)")
    print(f"Tests échoués   : {total_tests - passed_tests}")
    print("----------------------------")
    for res in results:
        status = "✅ PASS" if res['passed'] else "❌ FAIL"
        print(f"- {res['id']:<15} | Statut: {status:<7} | Latence: {res['latency']}")
    print("----------------------------")
    
    if total_tests != passed_tests:
        # Permet de signaler un échec à une CI/CD
        sys.exit(1)

if __name__ == "__main__":
    run_tests()