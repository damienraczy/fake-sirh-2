# =============================================================================
# rag/chain.py - Chaîne RAG avec mémoire conversationnelle
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

class SIRHRAGChain:
    """Chaîne RAG principale avec mémoire conversationnelle"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        # Initialisation des composants
        print("Initialisation de la chaîne RAG avec mémoire...")
        self.embeddings = SIRHEmbeddings(config.embedding_model)
        self.vectorstore = SIRHVectorStore(config, self.embeddings)
        self.sql_retriever = SIRHSQLRetriever(config)
        
        # Nouveau : Système de mémoire
        self.memory = ConversationMemory()
        
        # Charger les prompts
        self.system_prompt = self._load_system_prompt()
        
        # Initialiser la base vectorielle si nécessaire
        self._initialize_vectorstore()
        
        # Nettoyer les anciennes conversations au démarrage
        self.memory.cleanup_old_conversations()
        
        print("✅ Chaîne RAG avec mémoire initialisée")
    
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
        """Traite une question avec mémoire conversationnelle"""
        
        # Créer une session si nécessaire
        if session_id is None:
            session_id = self.memory.create_session({'company': self.config.company_name})
        
        # Ajouter la question utilisateur à la mémoire
        self.memory.add_message(session_id, 'user', question)
        
        # 1. Déterminer le type de question
        query_type = self._classify_query(question)
        
        # 2. Récupérer le contexte (données + historique)
        context = self._retrieve_context_with_memory(question, query_type, session_id)
        
        # 3. Générer la réponse
        response = self._generate_response_with_memory(question, context, session_id)
        
        # 4. Extraire les sources
        sources = self._extract_sources(context['documents'])
        
        # 5. Sauvegarder la réponse dans la mémoire
        response_metadata = {
            'query_type': query_type,
            'sources': sources,
            'session_id': session_id
        }
        self.memory.add_message(session_id, 'assistant', response, response_metadata)
        
        return {
            "answer": response,
            "sources": sources,
            "query_type": query_type,
            "context_used": len(context['documents']) > 0,
            "session_id": session_id,
            "conversation_length": len(self.memory.get_conversation_history(session_id))
        }
    
    def _classify_query(self, question: str) -> str:
        """Classifie le type de question (inchangé)"""
        question_lower = question.lower()
        
        # Détection de références conversationnelles
        if any(word in question_lower for word in ['précédent', 'avant', 'plus tôt', 'dernier', 'dit']):
            return 'conversational_reference'
        
        # Classifications existantes
        if any(word in question_lower for word in ['combien', 'nombre', 'statistique', 'total', 'compter']):
            return 'statistical'
        elif any(word in question_lower for word in ['qui', 'quel employé', 'liste', 'trouve', 'cherche']):
            return 'search'
        elif any(word in question_lower for word in ['performance', 'évaluation', 'score', 'meilleur', 'top']):
            return 'performance'
        elif any(word in question_lower for word in ['formation', 'compétence', 'skill', 'apprentissage']):
            return 'skills_training'
        elif any(word in question_lower for word in ['feedback', 'retour', 'commentaire', 'avis']):
            return 'feedback'
        elif any(word in question_lower for word in ['manager', 'hiérarchie', 'équipe', 'département']):
            return 'organizational'
        else:
            return 'general'
    
    def _retrieve_context_with_memory(self, question: str, query_type: str, session_id: str) -> Dict[str, Any]:
        """Récupère le contexte avec mémoire conversationnelle"""
        context = {
            'documents': [],
            'conversation_history': ""
        }
        
        # Récupérer l'historique conversationnel
        context['conversation_history'] = self.memory.get_context_for_query(session_id, question)
        
        # Recherche vectorielle (toujours)
        try:
            vector_results = self.vectorstore.similarity_search(question, k=self.config.top_k_docs)
            context['documents'].extend(vector_results)
        except Exception as e:
            print(f"⚠️ Erreur recherche vectorielle: {e}")
        
        # Requêtes SQL spécialisées selon le type
        try:
            if query_type == 'statistical':
                sql_results = self._get_statistical_data(question)
                context['documents'].extend(sql_results)
            elif query_type == 'performance':
                sql_results = self.sql_retriever.get_top_performers()
                context['documents'].extend([{'content': str(result), 'metadata': {'source': 'sql_performance'}} for result in sql_results])
            elif query_type == 'skills_training':
                sql_results = self.sql_retriever.get_training_summary()
                context['documents'].extend([{'content': str(result), 'metadata': {'source': 'sql_training'}} for result in sql_results])
            elif query_type == 'conversational_reference':
                # Pour les références conversationnelles, privilégier l'historique
                pass
        except Exception as e:
            print(f"⚠️ Erreur requêtes SQL: {e}")
        
        return context
    
    def _generate_response_with_memory(self, question: str, context: Dict[str, Any], session_id: str) -> str:
        """Génère la réponse avec le contexte conversationnel"""
        
        # Construire le contexte combiné
        full_context = ""
        
        # Ajouter l'historique conversationnel si disponible
        if context['conversation_history']:
            full_context += context['conversation_history'] + "\n\n"
        
        # Ajouter les documents trouvés
        if context['documents']:
            full_context += "=== DONNÉES DISPONIBLES ===\n"
            for i, item in enumerate(context['documents'], 1):
                source = item['metadata'].get('source', 'unknown')
                content = item['content']
                # Limiter la taille du contexte
                if len(content) > 500:
                    content = content[:500] + "..."
                full_context += f"\n--- Source {i} ({source}) ---\n{content}\n"
        
        # Construire le prompt final
        prompt = f"""{self.system_prompt}

{full_context}

QUESTION DE L'UTILISATEUR :
{question}

RÉPONSE (en français, utilise le contexte conversationnel et les données) :"""
        
        # Générer la réponse
        try:
            response = generate_text(prompt)
            return response.strip()
        except Exception as e:
            return f"Désolé, je rencontre une difficulté technique pour répondre à votre question. Erreur: {str(e)}"
    
    def _get_statistical_data(self, question: str) -> List[Dict[str, Any]]:
        """Récupère des données statistiques (inchangé)"""
        results = []
        
        try:
            # Compter les employés par département
            dept_data = self.sql_retriever.get_employee_count_by_department()
            if dept_data:
                content = "Répartition des employés par département:\n"
                total = 0
                for dept in dept_data:
                    content += f"- {dept['department']}: {dept['count']} employés\n"
                    total += dept['count']
                content += f"Total: {total} employés"
                
                results.append({
                    'content': content,
                    'metadata': {'source': 'sql_statistics', 'type': 'department_count'}
                })
            
            # Distribution des performances
            perf_data = self.sql_retriever.get_performance_distribution()
            if perf_data:
                content = "Distribution des scores de performance:\n"
                for perf in perf_data:
                    content += f"- Score {perf['score']}/5: {perf['count']} employés\n"
                
                results.append({
                    'content': content,
                    'metadata': {'source': 'sql_statistics', 'type': 'performance_distribution'}
                })
        
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des statistiques: {e}")
        
        return results
    
    def _extract_sources(self, context: List[Dict[str, Any]]) -> List[str]:
        """Extrait les sources utilisées (inchangé)"""
        sources = set()
        for item in context:
            source = item['metadata'].get('source', 'unknown')
            if 'employee_name' in item['metadata']:
                source += f" ({item['metadata']['employee_name']})"
            elif 'type' in item['metadata']:
                source += f" ({item['metadata']['type']})"
            sources.add(source)
        
        return list(sources)
    
    # Nouvelles méthodes pour la gestion de mémoire
    
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
    
    # Méthodes existantes inchangées
    
    def reindex_documents(self):
        """Réindexe tous les documents (pour mise à jour)"""
        print("Réindexation des documents...")
        try:
            # Supprimer l'ancienne collection
            self.vectorstore.reset_collection()
            
            # Recharger les documents
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