# =============================================================================
# rag/chain.py - Chaîne RAG avec routage sémantique
# =============================================================================

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from rag.config import RAGConfig
from rag.embeddings import SIRHEmbeddings
from rag.vectorstore import SIRHVectorStore
from rag.document_loader import SIRHDocumentLoader
from rag.sql_retriever import SIRHSQLRetriever
from rag.memory import ConversationMemory
from utils.llm_client import generate_text

# NOUVEAUX IMPORTS
from rag.router import SemanticRouter
from rag.graph_retriever import SIRHGraphRetriever

class SIRHRAGChain:
    """Chaîne RAG principale avec routage sémantique et mémoire"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        print("Initialisation de la chaîne RAG avec routage...")
        self.embeddings = SIRHEmbeddings(config.embedding_model)
        
        # NOUVEAU: Initialisation du routeur
        router_config_path = current_dir / 'router_config.yaml'
        self.router = SemanticRouter(str(router_config_path))
        
        # Initialisation des retrievers
        self.vectorstore = SIRHVectorStore(config, self.embeddings)
        self.sql_retriever = SIRHSQLRetriever(config)
        self.graph_retriever = SIRHGraphRetriever(config) # Nouveau
        
        self.memory = ConversationMemory()
        self.system_prompt = self._load_system_prompt()
        self._initialize_vectorstore()
        self.memory.cleanup_old_conversations()
        
        print("✅ Chaîne RAG avec routage initialisée")
    
    # ... (les méthodes _load_system_prompt et _initialize_vectorstore restent les mêmes) ...

    def _load_system_prompt(self) -> str:
        """Charge le prompt système avec instructions de mémoire"""
        return f"""Tu es un assistant RH intelligent pour {self.config.company_name}, une entreprise du secteur "{self.config.company_sector}" basée en Nouvelle-Calédonie.
        Tu as accès à toutes les données RH de l'entreprise ET à l'historique de cette conversation.
        INSTRUCTIONS :
        1. Réponds UNIQUEMENT en français
        2. Base tes réponses sur les données fournies ET le contexte conversationnel
        3. Utilise l'historique pour maintenir la cohérence et faire des références
        4. Si l'utilisateur fait référence à une question précédente, utilise le contexte
        5. Reste professionnel et bienveillant
        6. Respecte la confidentialité (pas de données sensibles)
        7. Fournis des réponses structurées et actionables
        CONTEXTE ENTREPRISE :
        - Nom : {self.config.company_name}
        - Secteur : {self.config.company_sector}
        - Culture : {self.config.company_culture}
        - Localisation : Nouvelle-Calédonie
        Utilise le contexte conversationnel ET les données pour répondre de façon cohérente."""

    def _initialize_vectorstore(self):
        """Initialise la base vectorielle avec les documents"""
        stats = self.vectorstore.get_collection_stats()
        if stats['count'] > 0:
            print(f"Base vectorielle déjà initialisée avec {stats['count']} documents")
            return
        
        print("Initialisation de la base vectorielle...")
        try:
            loader = SIRHDocumentLoader(self.config)
            documents = loader.load_all_documents()
            
            if documents:
                self.vectorstore.add_documents(documents)
                print(f"✅ {len(documents)} documents indexés")
            else:
                print("⚠️ Aucun document trouvé à indexer")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation de la base vectorielle: {e}")

    def query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Traite une question avec routage et mémoire"""
        
        if session_id is None:
            session_id = self.memory.create_session({'company': self.config.company_name})
        
        self.memory.add_message(session_id, 'user', question)
        
        # 1. Déterminer la route à utiliser
        route = self.router.route(question)
        
        # 2. Récupérer le contexte
        context = self._retrieve_context(question, route, session_id)
        
        # 3. Générer la réponse
        response = self._generate_response_with_memory(question, context, session_id)
        
        # 4. Extraire les sources
        sources = self._extract_sources(context.get('documents', []))
        
        # 5. Sauvegarder la réponse dans la mémoire
        response_metadata = {'route': route, 'sources': sources, 'session_id': session_id}
        self.memory.add_message(session_id, 'assistant', response, response_metadata)
        
        return {
            "answer": response,
            "sources": sources,
            "route": route,
            "session_id": session_id,
            # Ajout pour la compatibilité avec l'ancienne API
            "query_type": route,
            "context_used": len(sources) > 0,
            "conversation_length": len(self.memory.get_conversation_history(session_id))
        }
        
    def _retrieve_context(self, question: str, route: str, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte en fonction de la route déterminée."""
        context = {
            'documents': [],
            'conversation_history': self.memory.get_context_for_query(session_id, question)
        }
        
        retrieved_docs = []
        try:
            if route == "SQL":
                # À affiner: pour l'instant, on utilise une méthode générique
                retrieved_docs = self.sql_retriever.get_context(question)
            elif route == "GRAPH":
                retrieved_docs = self.graph_retriever.get_context(question)
            else: # VECTOR ou par défaut
                retrieved_docs = self.vectorstore.similarity_search(question, k=self.config.top_k_docs)
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération via la route '{route}': {e}")

        context['documents'].extend(retrieved_docs)
        return context

    # ... (les méthodes _generate_response_with_memory, _extract_sources et les méthodes de gestion de mémoire restent majoritairement les mêmes) ...

    def _generate_response_with_memory(self, question: str, context: Dict[str, Any], session_id: str) -> str:
        """Génère la réponse avec le contexte conversationnel"""
        
        full_context = ""
        
        if context['conversation_history']:
            full_context += context['conversation_history'] + "\n\n"
        
        if context.get('documents'):
            full_context += "=== DONNÉES DISPONIBLES ===\n"
            for i, item in enumerate(context['documents'], 1):
                source = item['metadata'].get('source', 'unknown')
                content = item['content']
                if len(content) > 500:
                    content = content[:500] + "..."
                full_context += f"\n--- Source {i} ({source}) ---\n{content}\n"
        
        prompt = f"""{self.system_prompt}

{full_context}

QUESTION DE L'UTILISATEUR :
{question}

RÉPONSE (en français, utilise le contexte conversationnel et les données) :"""
        
        try:
            response = generate_text(prompt)
            return response.strip()
        except Exception as e:
            return f"Désolé, je rencontre une difficulté technique pour répondre à votre question. Erreur: {str(e)}"
    
    def _extract_sources(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Extrait les sources utilisées"""
        if not documents:
            return []
        sources = set()
        for item in documents:
            source = item['metadata'].get('source', 'unknown')
            sources.add(source)
        return list(sources)

    # ... (les autres méthodes comme get_conversation_history, reindex_documents, etc. restent les mêmes) ...
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Récupère l'historique d'une conversation"""
        return self.memory.get_conversation_history(session_id)
    def search_conversations(self, query: str) -> List[Dict[str, Any]]:
        """Recherche dans l'historique des conversations"""
        return self.memory.search_conversations(query)
    def get_memory_stats(self) -> Dict[str, Any]:
        """Statistiques de la mémoire conversationnelle"""
        return self.memory.get_memory_stats()
    def cleanup_memory(self):
        """Nettoie la mémoire"""
        self.memory.cleanup_old_conversations()
    def reindex_documents(self):
        """Réindexe tous les documents (pour mise à jour)"""
        print("Réindexation des documents...")
        try:
            self.vectorstore.reset_collection()
            loader = SIRHDocumentLoader(self.config)
            documents = loader.load_all_documents()
            
            if documents:
                self.vectorstore.add_documents(documents)
                print(f"✅ {len(documents)} documents réindexés")
            else:
                print("⚠️ Aucun document trouvé à réindexer")
        except Exception as e:
            print(f"❌ Erreur lors de la réindexation: {e}")
            raise
    def get_system_info(self) -> Dict[str, Any]:
        """Retourne les informations système avec mémoire"""
        try:
            vectorstore_stats = self.vectorstore.get_collection_stats()
            db_summary = self.sql_retriever.get_database_summary()
            memory_stats = self.get_memory_stats()
            
            return {
                "vectorstore": vectorstore_stats,
                "database": db_summary,
                "memory": memory_stats,
                "config": {
                    "embedding_model": self.config.embedding_model,
                    "chunk_size": self.config.chunk_size,
                    "top_k_docs": self.config.top_k_docs
                }
            }
        except Exception as e:
            return {"error": str(e)}