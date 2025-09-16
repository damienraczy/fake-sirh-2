# =============================================================================
# rag/api.py - API FastAPI avec support de sessions conversationnelles
# =============================================================================

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import get_config, load_config
from rag.config import RAGConfig
from rag.chain import SIRHRAGChain
from rag.sql_retriever import SIRHSQLRetriever

# =============================================================================
# Configuration FastAPI
# =============================================================================

app = FastAPI(
    title="🏢 SIRH RAG API avec Mémoire",
    description="API RAG pour l'interrogation intelligente des données RH avec mémoire conversationnelle",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration des templates et fichiers statiques
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Modèles Pydantic mis à jour
# =============================================================================

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # Nouveau : ID de session
    context: Optional[str] = None
    include_sources: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    query_type: str
    context_used: bool
    response_time: float
    confidence: Optional[float] = None
    session_id: str  # Nouveau : ID de session retourné
    conversation_length: int  # Nouveau : Longueur de la conversation

class ConversationHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int

class MemoryStatsResponse(BaseModel):
    total_sessions: int
    total_messages: int
    active_sessions_24h: int
    db_size_mb: float
    retention_days: int

class SystemStatus(BaseModel):
    status: str
    documents_indexed: int
    system_ready: bool
    memory_enabled: bool = True  # Nouveau
    version: str = "2.0.0"

# Modèles existants inchangés
class EmployeeInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    position: Optional[str] = None
    department: Optional[str] = None

class DepartmentStats(BaseModel):
    department: str
    count: int

class PerformanceInfo(BaseModel):
    first_name: str
    last_name: str
    score: int
    title: Optional[str] = None
    department: Optional[str] = None

# Variables globales
rag_chain: Optional[SIRHRAGChain] = None
sql_retriever: Optional[SIRHSQLRetriever] = None
rag_config: Optional[RAGConfig] = None

# =============================================================================
# Initialisation
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage avec mémoire"""
    global rag_chain, sql_retriever, rag_config
    
    try:
        print("🚀 Initialisation du système RAG avec mémoire...")
        
        config_path = os.getenv('FAKE_SIRH_2_CONFIG_FILE')
        load_config(config_path)

        base_config = get_config()
        rag_config = RAGConfig.from_base_config(base_config)
        
        rag_chain = SIRHRAGChain(rag_config)
        sql_retriever = SIRHSQLRetriever(rag_config)
        
        print("✅ Système RAG avec mémoire initialisé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise

def get_rag_chain():
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="Système RAG non initialisé")
    return rag_chain

def get_sql_retriever():
    if sql_retriever is None:
        raise HTTPException(status_code=503, detail="Retrieveur SQL non initialisé")
    return sql_retriever

def get_template_config():
    """Prépare la configuration pour les templates"""
    base_config = get_config()
    rag_cfg = base_config.get('rag', {})
    interface_cfg = rag_cfg.get('interface', {})
    
    return {
        'title': interface_cfg.get('title', 'SIRH RAG'),
        'subtitle': interface_cfg.get('subtitle', 'Assistant RH Intelligent'),
        'company_name': base_config['entreprise']['nom'],
        'company_sector': base_config['entreprise']['secteur'],
        'examples': interface_cfg.get('examples', [
            "Combien d'employés en R&D ?",
            "Qui sont les top performers ?",
            "Compétences IA disponibles ?",
            "Formations en leadership ?"
        ])
    }

# =============================================================================
# Routes Web (Templates) - inchangées
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Page d'accueil avec interface web"""
    config = get_template_config()
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "config": config}
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    """Page d'administration"""
    config = get_template_config()
    return templates.TemplateResponse(
        "admin.html", 
        {"request": request, "config": config}
    )

# =============================================================================
# Routes API principales avec mémoire
# =============================================================================

@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    chain: SIRHRAGChain = Depends(get_rag_chain)
):
    """Traite une requête utilisateur avec mémoire conversationnelle"""
    import time
    
    start_time = time.time()
    
    try:
        response = chain.query(request.question, session_id=request.session_id)
        response_time = round(time.time() - start_time, 2)
        
        return QueryResponse(
            answer=response["answer"],
            sources=response.get("sources", []),
            query_type=response.get("query_type", "unknown"),
            context_used=response.get("context_used", False),
            session_id=response["session_id"],
            conversation_length=response.get("conversation_length", 0),
            response_time=response_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@app.get("/status", response_model=SystemStatus)
async def get_status(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Retourne le statut du système avec info mémoire"""
    try:
        stats = chain.vectorstore.get_collection_stats()
        memory_stats = chain.get_memory_stats()
        
        return SystemStatus(
            status="operational",
            documents_indexed=stats.get('count', 0),
            system_ready=True,
            memory_enabled=True
        )
    except Exception as e:
        return SystemStatus(
            status="error",
            documents_indexed=0,
            system_ready=False,
            memory_enabled=False
        )

# =============================================================================
# Nouvelles routes pour la gestion de mémoire
# =============================================================================

@app.get("/conversations/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    chain: SIRHRAGChain = Depends(get_rag_chain)
):
    """Récupère l'historique d'une conversation"""
    try:
        messages = chain.get_conversation_history(session_id)
        
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/conversations/search/{query}")
async def search_conversations(
    query: str,
    limit: int = 10,
    chain: SIRHRAGChain = Depends(get_rag_chain)
):
    """Recherche dans l'historique des conversations"""
    try:
        results = chain.search_conversations(query)
        return {"query": query, "results": results[:limit]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Statistiques de la mémoire conversationnelle"""
    try:
        stats = chain.get_memory_stats()
        
        return MemoryStatsResponse(
            total_sessions=stats['total_sessions'],
            total_messages=stats['total_messages'],
            active_sessions_24h=stats['active_sessions_24h'],
            db_size_mb=round(stats['db_size_bytes'] / 1024 / 1024, 2),
            retention_days=stats['retention_days']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/memory/cleanup")
async def cleanup_memory(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Nettoie les anciennes conversations"""
    try:
        chain.cleanup_memory()
        return {"message": "Nettoyage de la mémoire effectué", "status": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# =============================================================================
# Routes API existantes (inchangées)
# =============================================================================

@app.get("/departments", response_model=List[DepartmentStats])
async def get_departments(retriever: SIRHSQLRetriever = Depends(get_sql_retriever)):
    """Retourne les statistiques par département"""
    try:
        data = retriever.get_employee_count_by_department()
        return [DepartmentStats(**item) for item in data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur base de données: {str(e)}")

@app.get("/employees", response_model=List[EmployeeInfo])
async def get_employees(
    limit: int = 50,
    department: Optional[str] = None,
    retriever: SIRHSQLRetriever = Depends(get_sql_retriever)
):
    """Retourne la liste des employés"""
    try:
        if department:
            query = f"""
            SELECT e.id, e.first_name, e.last_name, e.email, 
                   p.title as position, ou.name as department
            FROM employee e
            LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
            LEFT JOIN position p ON a.position_id = p.id
            LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
            WHERE ou.name = '{department}'
            LIMIT {limit}
            """
        else:
            query = f"""
            SELECT e.id, e.first_name, e.last_name, e.email, 
                   p.title as position, ou.name as department
            FROM employee e
            LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
            LEFT JOIN position p ON a.position_id = p.id
            LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
            LIMIT {limit}
            """
        
        data = retriever.execute_query(query)
        return [EmployeeInfo(**item) for item in data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/top-performers", response_model=List[PerformanceInfo])
async def get_top_performers(
    limit: int = 10,
    retriever: SIRHSQLRetriever = Depends(get_sql_retriever)
):
    """Retourne les meilleurs performeurs"""
    try:
        data = retriever.get_top_performers(limit)
        return [PerformanceInfo(**item) for item in data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/search/employees")
async def search_employees(
    skill: Optional[str] = None,
    name: Optional[str] = None,
    retriever: SIRHSQLRetriever = Depends(get_sql_retriever)
):
    """Recherche d'employés par compétence ou nom"""
    try:
        if skill:
            data = retriever.search_employees_by_skill(skill)
            return data
        elif name:
            query = f"""
            SELECT e.first_name, e.last_name, e.email, p.title, ou.name as department
            FROM employee e
            LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
            LEFT JOIN position p ON a.position_id = p.id
            LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
            WHERE e.first_name LIKE '%{name}%' OR e.last_name LIKE '%{name}%'
            LIMIT 20
            """
            data = retriever.execute_query(query)
            return data
        else:
            raise HTTPException(status_code=400, detail="Paramètre 'skill' ou 'name' requis")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/reindex")
async def reindex_documents(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Réindexe tous les documents"""
    try:
        chain.reindex_documents()
        return {"message": "Réindexation terminée", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur réindexation: {str(e)}")

# =============================================================================
# Routes utilitaires
# =============================================================================

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {"status": "healthy", "timestamp": "2025-01-15T10:30:00Z", "memory_enabled": True}

@app.get("/system/info")
async def get_system_info(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Informations complètes du système"""
    try:
        return chain.get_system_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)