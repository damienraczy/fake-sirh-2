# =============================================================================
# src/e07_rag_indexation.py
# =============================================================================

from rag.document_loader import SIRHDocumentLoader
from rag.vectorstore import SIRHVectorStore
from rag.embeddings import SIRHEmbeddings
from rag.config import RAGConfig
from config import get_config

def run():
    """
    Étape 7: Indexation RAG des données générées
    """
    print("Étape 7: Indexation RAG des données générées")
    
    # Configuration
    base_config = get_config()
    rag_config = RAGConfig.from_base_config(base_config)
    
    # Initialisation des composants RAG
    print("Initialisation des composants RAG...")
    embeddings = SIRHEmbeddings(rag_config.embedding_model)
    vectorstore = SIRHVectorStore(rag_config, embeddings)
    document_loader = SIRHDocumentLoader(rag_config)
    
    # Chargement des documents
    print("Chargement des documents...")
    documents = document_loader.load_all_documents()
    
    if not documents:
        print("⚠️ Aucun document trouvé à indexer")
        return
    
    print(f"📄 {len(documents)} documents trouvés")
    
    # Indexation
    print("Indexation des documents dans la base vectorielle...")
    vectorstore.add_documents(documents)
    
    # Statistiques
    stats = vectorstore.get_collection_stats()
    print(f"✅ Indexation terminée:")
    print(f"   - Documents indexés: {stats['count']}")
    print(f"   - Collection: {stats['name']}")
    print(f"   - Chemin: {rag_config.vector_store_path}")
    
    # Test rapide
    print("\n🧪 Test rapide du système RAG...")
    try:
        test_results = vectorstore.similarity_search("employé développeur", k=3)
        print(f"   - Test réussi: {len(test_results)} résultats trouvés")
    except Exception as e:
        print(f"   - ⚠️ Test échoué: {e}")
    
    print("✅ Système RAG prêt à l'utilisation!")