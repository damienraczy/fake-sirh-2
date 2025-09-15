# =============================================================================
# rag/chain.py - Chaîne RAG principale
# =============================================================================

from typing import Dict, Any, List
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
from llm_client import generate_text  # Réutilise le client existant

class SIRHRAGChain:
    """Chaîne RAG principale pour le SIRH"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        # Initialisation des composants
        print("Initialisation de la chaîne RAG...")
        self.embeddings = SIRHEmbeddings(config.embedding_model)
        self.vectorstore = SIRHVectorStore(config, self.embeddings)
        self.sql_retriever = SIRHSQLRetriever(config)
        
        # Charger les prompts
        self.system_prompt = self._load_system_prompt()
        
        # Initialiser la base vectorielle si nécessaire
        self._initialize_vectorstore()
        
        print("✅ Chaîne RAG initialisée")
    
    def _load_system_prompt(self) -> str:
        """Charge le prompt système"""
        return f"""Tu es un assistant RH intelligent pour {self.config.company_name}, une entreprise du secteur "{self.config.company_sector}" basée en Nouvelle-Calédonie.

Tu as accès à toutes les données RH de l'entreprise : profils d'employés, évaluations de performance, formations, compétences, feedback, et documents.

INSTRUCTIONS :
1. Réponds UNIQUEMENT en français
2. Base tes réponses sur les données fournies
3. Si tu n'as pas d'information, dis-le clairement
4. Reste professionnel et bienveillant
5. Respecte la confidentialité (pas de données sensibles)
6. Fournis des réponses structurées et actionables

CONTEXTE ENTREPRISE :
- Nom : {self.config.company_name}
- Secteur : {self.config.company_sector}
- Culture : {self.config.company_culture}
- Localisation : Nouvelle-Calédonie

Utilise le contexte fourni pour répondre à la question de l'utilisateur."""
    
    def _initialize_vectorstore(self):
        """Initialise la base vectorielle avec les documents"""
        # Vérifier si déjà initialisée
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
    
    def query(self, question: str) -> Dict[str, Any]:
        """Traite une question et retourne une réponse enrichie"""
        
        # 1. Déterminer le type de question
        query_type = self._classify_query(question)
        
        # 2. Récupérer le contexte approprié
        context = self._retrieve_context(question, query_type)
        
        # 3. Générer la réponse
        response = self._generate_response(question, context)
        
        # 4. Extraire les sources
        sources = self._extract_sources(context)
        
        return {
            "answer": response,
            "sources": sources,
            "query_type": query_type,
            "context_used": len(context) > 0
        }
    
    def _classify_query(self, question: str) -> str:
        """Classifie le type de question"""
        question_lower = question.lower()
        
        # Mots-clés pour différents types
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
    
    def _retrieve_context(self, question: str, query_type: str) -> List[Dict[str, Any]]:
        """Récupère le contexte pertinent"""
        context = []
        
        # Recherche vectorielle (toujours)
        try:
            vector_results = self.vectorstore.similarity_search(question, k=self.config.top_k_docs)
            context.extend(vector_results)
        except Exception as e:
            print(f"⚠️ Erreur recherche vectorielle: {e}")
        
        # Requêtes SQL spécialisées selon le type
        try:
            if query_type == 'statistical':
                sql_results = self._get_statistical_data(question)
                context.extend(sql_results)
            elif query_type == 'performance':
                sql_results = self.sql_retriever.get_top_performers()
                context.extend([{'content': str(result), 'metadata': {'source': 'sql_performance'}} for result in sql_results])
            elif query_type == 'skills_training':
                sql_results = self.sql_retriever.get_training_summary()
                context.extend([{'content': str(result), 'metadata': {'source': 'sql_training'}} for result in sql_results])
        except Exception as e:
            print(f"⚠️ Erreur requêtes SQL: {e}")
        
        return context[:10]  # Limiter le contexte
    
    def _get_statistical_data(self, question: str) -> List[Dict[str, Any]]:
        """Récupère des données statistiques"""
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
    
    def _generate_response(self, question: str, context: List[Dict[str, Any]]) -> str:
        """Génère la réponse avec le LLM"""
        
        # Construire le contexte
        context_text = ""
        if context:
            context_text = "\nCONTEXTE DISPONIBLE :\n"
            for i, item in enumerate(context, 1):
                source = item['metadata'].get('source', 'unknown')
                content = item['content']
                # Limiter la taille du contexte
                if len(content) > 500:
                    content = content[:500] + "..."
                context_text += f"\n--- Source {i} ({source}) ---\n{content}\n"
        
        # Construire le prompt
        prompt = f"""{self.system_prompt}

{context_text}

QUESTION DE L'UTILISATEUR :
{question}

RÉPONSE (en français, basée sur le contexte fourni) :"""
        
        # Générer la réponse
        try:
            response = generate_text(prompt)
            return response.strip()
        except Exception as e:
            return f"Désolé, je rencontre une difficulté technique pour répondre à votre question. Erreur: {str(e)}"
    
    def _extract_sources(self, context: List[Dict[str, Any]]) -> List[str]:
        """Extrait les sources utilisées"""
        sources = set()
        for item in context:
            source = item['metadata'].get('source', 'unknown')
            if 'employee_name' in item['metadata']:
                source += f" ({item['metadata']['employee_name']})"
            elif 'type' in item['metadata']:
                source += f" ({item['metadata']['type']})"
            sources.add(source)
        
        return list(sources)
    
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
        """Retourne les informations système"""
        try:
            vectorstore_stats = self.vectorstore.get_collection_stats()
            db_summary = self.sql_retriever.get_database_summary()
            
            return {
                "vectorstore": vectorstore_stats,
                "database": db_summary,
                "config": {
                    "embedding_model": self.config.embedding_model,
                    "chunk_size": self.config.chunk_size,
                    "top_k_docs": self.config.top_k_docs
                }
            }
        except Exception as e:
            return {"error": str(e)}