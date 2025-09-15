# =============================================================================
# rag/embeddings.py - Gestion des embeddings
# =============================================================================

from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class SIRHEmbeddings:
    """Gestionnaire d'embeddings pour le SIRH"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle d'embeddings"""
        try:
            print(f"Chargement du modèle d'embeddings: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print("✅ Modèle d'embeddings chargé")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du modèle: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Génère les embeddings pour une liste de documents"""
        if not self.model:
            raise RuntimeError("Modèle d'embeddings non initialisé")
        
        if not texts:
            return []
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=len(texts) > 10)
            return embeddings.tolist()
        except Exception as e:
            print(f"Erreur lors de la génération des embeddings: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Génère l'embedding pour une requête"""
        if not self.model:
            raise RuntimeError("Modèle d'embeddings non initialisé")
        
        try:
            embedding = self.model.encode([text], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            print(f"Erreur lors de la génération de l'embedding de requête: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Retourne les informations sur le modèle"""
        return {
            "model_name": self.model_name,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown'),
            "embedding_dimension": getattr(self.model, 'get_sentence_embedding_dimension', lambda: 'unknown')()
        }