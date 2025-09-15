# =============================================================================
# rag/config.py - Configuration RAG
# =============================================================================

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

@dataclass
class RAGConfig:
    """Configuration pour le système RAG SIRH"""
    
    # Chemins de base (hérite de la config principale)
    sirh_db_path: str
    documents_path: str
    vector_store_path: str
    
    # Configuration LLM (hérite de la config principale) 
    llm_model: str
    ollama_api_url: str
    
    # Configuration Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Paramètres RAG
    top_k_docs: int = 5
    temperature: float = 0.1
    max_tokens: int = 1000
    
    # Configuration interface
    interface_title: str = "🏢 SIRH RAG"
    interface_port: int = 8000
    
    # Données entreprise (hérite de la config principale)
    company_name: str = ""
    company_sector: str = ""
    company_culture: str = ""
    
    @classmethod
    def from_base_config(cls, base_config: Dict[str, Any]) -> 'RAGConfig':
        """Crée une config RAG à partir de la config de base"""
        
        entreprise = base_config.get('entreprise',{})
        rag_config = base_config.get('rag', {})
        
        return cls(
            # Chemins (hérite de la base)
            sirh_db_path=f"{entreprise['base_de_données']['chemin']}/{entreprise['base_de_données']['nom']}",
            documents_path="data/documents",
            vector_store_path=rag_config.get('vector_store_path', 'data/vector_store'),
            
            # LLM (hérite du système existant)
            llm_model="gpt-oss:20b",  # Reprend votre config
            ollama_api_url="https://ollama.com/api/generate",
            
            # RAG spécifique
            embedding_model=rag_config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
            chunk_size=rag_config.get('chunk_size', 1000),
            chunk_overlap=rag_config.get('chunk_overlap', 200),
            top_k_docs=rag_config.get('top_k_docs', 5),
            temperature=rag_config.get('temperature', 0.1),
            max_tokens=rag_config.get('max_tokens', 1000),
            
            # Interface
            interface_title=rag_config.get('interface', {}).get('title', f"🏢 SIRH RAG - {entreprise['nom']}"),
            interface_port=rag_config.get('interface', {}).get('port', 8000),
            
            # Entreprise
            company_name=entreprise['nom'],
            company_sector=entreprise['secteur'],
            company_culture=entreprise['culture']
        )
    
    def __post_init__(self):
        """Validation et création des répertoires"""
        for path in [self.documents_path, self.vector_store_path]:
            Path(path).mkdir(parents=True, exist_ok=True)