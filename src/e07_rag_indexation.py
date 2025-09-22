# =============================================================================
# src/e07_rag_indexation.py - Version refactorisée
# =============================================================================

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import get_config

def run():
    """
    Étape 7: Indexation RAG des données générées
    """
    print("Étape 7: Indexation RAG des données générées")
    
    from rag.chain import SIRHRAGChain
    from rag.config import RAGConfig
    
    base_config = get_config()
    rag_config = RAGConfig.from_base_config(base_config)
    
    # L'initialisation de SIRHRAGChain déclenche automatiquement l'indexation
    rag_chain = SIRHRAGChain(rag_config)
    
    stats = rag_chain.vectorstore.get_collection_stats()
    print(f"✅ {stats.get('count', 0)} documents indexés")
    print("✅ Système RAG prêt à l'utilisation")

if __name__ == "__main__":
    # Permet de tester l'étape individuellement
    from config import load_config
    
    # Charger la configuration par défaut
    load_config('config.yaml')
    
    # Exécuter l'étape
    run()
    