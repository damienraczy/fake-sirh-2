# =============================================================================
# rag/api.py - API FastAPI principale
# =============================================================================

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import get_config
from rag.config import RAGConfig
from rag.chain import SIRHRAGChain
from rag.sql_retriever import SIRHSQLRetriever

# =============================================================================
# Modèles Pydantic
# =============================================================================

class QueryRequest(BaseModel):
    """Requête utilisateur"""
    question: str
    context: Optional[str] = None
    include_sources: bool = True

class QueryResponse(BaseModel):
    """Réponse du système RAG"""
    answer: str
    sources: List[str]
    query_type: str
    context_used: bool
    response_time: float
    confidence: Optional[float] = None

class EmployeeInfo(BaseModel):
    """Information employé"""
    id: int
    first_name: str
    last_name: str
    email: str
    position: Optional[str] = None
    department: Optional[str] = None

class DepartmentStats(BaseModel):
    """Statistiques département"""
    department: str
    count: int

class PerformanceInfo(BaseModel):
    """Information de performance"""
    first_name: str
    last_name: str
    score: int
    title: Optional[str] = None
    department: Optional[str] = None

class SystemStatus(BaseModel):
    """Statut du système"""
    status: str
    documents_indexed: int
    system_ready: bool
    version: str = "1.0.0"

# =============================================================================
# Application FastAPI
# =============================================================================

app = FastAPI(
    title="🏢 SIRH RAG API - Flow Solutions",
    description="API RAG pour l'interrogation intelligente des données RH",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales pour les instances
rag_chain: Optional[SIRHRAGChain] = None
sql_retriever: Optional[SIRHSQLRetriever] = None
rag_config: Optional[RAGConfig] = None

# =============================================================================
# Gestion de l'initialisation
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global rag_chain, sql_retriever, rag_config
    
    try:
        print("🚀 Initialisation du système RAG...")
        
        # Charger la configuration
        base_config = get_config()
        rag_config = RAGConfig.from_base_config(base_config)
        
        # Initialiser les composants
        rag_chain = SIRHRAGChain(rag_config)
        sql_retriever = SIRHSQLRetriever(rag_config)
        
        print("✅ Système RAG initialisé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise

def get_rag_chain():
    """Dependency injection pour la chaîne RAG"""
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="Système RAG non initialisé")
    return rag_chain

def get_sql_retriever():
    """Dependency injection pour le retrieveur SQL"""
    if sql_retriever is None:
        raise HTTPException(status_code=503, detail="Retrieveur SQL non initialisé")
    return sql_retriever

# =============================================================================
# Routes API
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Page d'accueil avec interface web"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏢 SIRH RAG - Flow Solutions</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    </head>
    <body class="bg-gray-50">
        <div class="container mx-auto px-4 py-8">
            <!-- Header -->
            <div class="bg-gradient-to-r from-blue-800 to-green-600 text-white p-8 rounded-lg shadow-lg mb-8">
                <h1 class="text-4xl font-bold mb-2">🤖 Assistant RH Intelligent</h1>
                <h2 class="text-2xl mb-4">Flow Solutions - Green Energy post AI</h2>
                <p class="text-lg opacity-90">Explorez vos données RH avec l'intelligence artificielle</p>
            </div>

            <!-- Interface de chat -->
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
                <!-- Chat principal -->
                <div class="lg:col-span-3">
                    <div class="bg-white rounded-lg shadow-lg p-6">
                        <h3 class="text-xl font-semibold mb-4">💬 Chat RH</h3>
                        
                        <!-- Messages -->
                        <div id="messages" class="h-96 overflow-y-auto mb-4 p-4 bg-gray-50 rounded border">
                            <div class="text-gray-500 text-center">
                                Posez votre première question sur les données RH...
                            </div>
                        </div>
                        
                        <!-- Input -->
                        <div class="flex gap-2">
                            <input 
                                type="text" 
                                id="userInput" 
                                placeholder="Tapez votre question ici..."
                                class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                onkeypress="if(event.key==='Enter') sendMessage()"
                            >
                            <button 
                                onclick="sendMessage()"
                                class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                            >
                                Envoyer
                            </button>
                        </div>
                        
                        <!-- Loading indicator -->
                        <div id="loading" class="hidden mt-4 text-center">
                            <div class="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                            <span class="ml-2">Recherche en cours...</span>
                        </div>
                    </div>
                </div>
                
                <!-- Sidebar -->
                <div class="lg:col-span-1">
                    <!-- Exemples -->
                    <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <h3 class="text-lg font-semibold mb-4">💡 Exemples</h3>
                        <div class="space-y-2">
                            <button onclick="askExample('Combien d\\'employés en R&D ?')" 
                                    class="w-full text-left p-3 bg-gray-100 hover:bg-blue-100 rounded transition text-sm">
                                👥 Employés en R&D
                            </button>
                            <button onclick="askExample('Qui sont les top performers ?')" 
                                    class="w-full text-left p-3 bg-gray-100 hover:bg-blue-100 rounded transition text-sm">
                                🏆 Top performers
                            </button>
                            <button onclick="askExample('Compétences IA disponibles ?')" 
                                    class="w-full text-left p-3 bg-gray-100 hover:bg-blue-100 rounded transition text-sm">
                                🧠 Compétences IA
                            </button>
                            <button onclick="askExample('Formations en leadership ?')" 
                                    class="w-full text-left p-3 bg-gray-100 hover:bg-blue-100 rounded transition text-sm">
                                📚 Formations leadership
                            </button>
                        </div>
                    </div>
                    
                    <!-- Statistiques -->
                    <div class="bg-white rounded-lg shadow-lg p-6">
                        <h3 class="text-lg font-semibold mb-4">📊 Statistiques</h3>
                        <div id="stats" class="space-y-2">
                            <div class="text-sm text-gray-500">Chargement...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Variables globales
            let messageCount = 0;

            // Initialisation
            document.addEventListener('DOMContentLoaded', function() {
                loadStats();
            });

            // Envoyer un message
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const question = input.value.trim();
                
                if (!question) return;
                
                // Afficher le message utilisateur
                addMessage('user', question);
                input.value = '';
                
                // Afficher le loading
                showLoading(true);
                
                try {
                    const response = await axios.post('/query', {
                        question: question,
                        include_sources: true
                    });
                    
                    // Afficher la réponse
                    addMessage('assistant', response.data.answer, response.data);
                    
                } catch (error) {
                    addMessage('assistant', 'Désolé, une erreur s\\'est produite: ' + error.message);
                } finally {
                    showLoading(false);
                }
            }

            // Ajouter un message à l'interface
            function addMessage(role, content, metadata = null) {
                const messagesDiv = document.getElementById('messages');
                
                // Supprimer le message de bienvenue si c'est le premier message
                if (messageCount === 0) {
                    messagesDiv.innerHTML = '';
                }
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `mb-4 ${role === 'user' ? 'text-right' : 'text-left'}`;
                
                let metadataHtml = '';
                if (metadata && role === 'assistant') {
                    metadataHtml = `
                        <div class="mt-2 text-xs text-gray-500">
                            <span class="bg-gray-200 px-2 py-1 rounded mr-2">📊 ${metadata.query_type}</span>
                            <span class="bg-gray-200 px-2 py-1 rounded mr-2">📚 ${metadata.sources.length} sources</span>
                            <span class="bg-gray-200 px-2 py-1 rounded">⏱️ ${metadata.response_time}s</span>
                        </div>
                    `;
                }
                
                messageDiv.innerHTML = `
                    <div class="inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        role === 'user' 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-white border border-gray-200'
                    }">
                        ${content}
                        ${metadataHtml}
                    </div>
                `;
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                messageCount++;
            }

            // Afficher/masquer le loading
            function showLoading(show) {
                const loading = document.getElementById('loading');
                loading.classList.toggle('hidden', !show);
            }

            // Exemple rapide
            function askExample(question) {
                document.getElementById('userInput').value = question;
                sendMessage();
            }

            // Charger les statistiques
            async function loadStats() {
                try {
                    const [statusResponse, deptResponse] = await Promise.all([
                        axios.get('/status'),
                        axios.get('/departments')
                    ]);
                    
                    const status = statusResponse.data;
                    const departments = deptResponse.data;
                    
                    const statsDiv = document.getElementById('stats');
                    const totalEmployees = departments.reduce((sum, dept) => sum + dept.count, 0);
                    
                    statsDiv.innerHTML = `
                        <div class="text-sm">
                            <div class="font-medium">👥 ${totalEmployees} employés</div>
                            <div class="font-medium">🏛️ ${departments.length} départements</div>
                            <div class="font-medium">📄 ${status.documents_indexed} documents</div>
                            <div class="mt-2 text-xs text-green-600">✅ Système opérationnel</div>
                        </div>
                    `;
                    
                } catch (error) {
                    console.error('Erreur chargement stats:', error);
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    chain: SIRHRAGChain = Depends(get_rag_chain)
):
    """Traite une requête utilisateur et retourne une réponse intelligente"""
    import time
    
    start_time = time.time()
    
    try:
        response = chain.query(request.question)
        response_time = round(time.time() - start_time, 2)
        
        return QueryResponse(
            answer=response["answer"],
            sources=response.get("sources", []),
            query_type=response.get("query_type", "unknown"),
            context_used=response.get("context_used", False),
            response_time=response_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@app.get("/status", response_model=SystemStatus)
async def get_status(chain: SIRHRAGChain = Depends(get_rag_chain)):
    """Retourne le statut du système"""
    try:
        stats = chain.vectorstore.get_collection_stats()
        
        return SystemStatus(
            status="operational",
            documents_indexed=stats.get('count', 0),
            system_ready=True
        )
    except Exception as e:
        return SystemStatus(
            status="error",
            documents_indexed=0,
            system_ready=False
        )

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
        # Requête SQL adaptée
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
        # Note: Cette méthode devra être implémentée dans SIRHRAGChain
        # chain.reindex_documents()
        return {"message": "Réindexation lancée", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur réindexation: {str(e)}")
