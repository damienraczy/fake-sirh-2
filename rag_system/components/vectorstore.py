# =============================================================================
# rag/vectorstore.py - Base de données vectorielle
# =============================================================================

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import uuid
from pathlib import Path

class SIRHVectorStore:
    """Base de données vectorielle pour le SIRH"""
    
    def __init__(self, config, embeddings):
        self.config = config
        self.embeddings = embeddings
        
        # Initialiser ChromaDB
        try:
            print(f"Initialisation de ChromaDB: {config.vector_store_path}")
            self.client = chromadb.PersistentClient(
                path=config.vector_store_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_or_create_collection(
                name="sirh_documents",
                metadata={"description": "Documents SIRH Flow Solutions"}
            )
            print("✅ ChromaDB initialisé")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation de ChromaDB: {e}")
            raise
    
    def add_documents(self, documents: List) -> None:
        """Ajoute des documents à la base vectorielle"""
        if not documents:
            print("Aucun document à ajouter")
            return
        
        try:
            print(f"Ajout de {len(documents)} documents à la base vectorielle...")
            
            # Préparer les données
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            # Générer les embeddings
            print("Génération des embeddings...")
            embeddings = self.embeddings.embed_documents(texts)
            
            # Générer des IDs uniques
            ids = [str(uuid.uuid4()) for _ in documents]
            
            # Ajouter à ChromaDB par batch pour éviter les problèmes de mémoire
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                end_idx = min(i + batch_size, len(documents))
                
                self.collection.add(
                    documents=texts[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    embeddings=embeddings[i:end_idx],
                    ids=ids[i:end_idx]
                )
                print(f"Batch {i//batch_size + 1}: {end_idx - i} documents ajoutés")
            
            print(f"✅ {len(documents)} documents ajoutés à la base vectorielle")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout des documents: {e}")
            raise
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Recherche par similarité"""
        try:
            # Générer l'embedding de la requête
            query_embedding = self.embeddings.embed_query(query)
            
            # Rechercher dans ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            
            # Formatter les résultats
            documents = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {},
                        'score': 1 - results['distances'][0][i] if results.get('distances') and results['distances'][0] else 0.0
                    }
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Statistiques de la collection"""
        try:
            return {
                "count": self.collection.count(),
                "name": self.collection.name
            }
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des stats: {e}")
            return {"count": 0, "name": "unknown"}
    
    def delete_collection(self):
        """Supprime la collection (pour réinitialisation)"""
        try:
            self.client.delete_collection("sirh_documents")
            print("✅ Collection supprimée")
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {e}")
    
    def reset_collection(self):
        """Remet à zéro la collection"""
        try:
            self.delete_collection()
            self.collection = self.client.create_collection(
                name="sirh_documents",
                metadata={"description": "Documents SIRH Flow Solutions"}
            )
            print("✅ Collection réinitialisée")
        except Exception as e:
            print(f"❌ Erreur lors de la réinitialisation: {e}")