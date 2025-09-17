# TO_DO.md - Évolution vers GraphRAG avec Neo4j et Haystack

"Fake-SIRH-2" est une base de travail solide avec un générateur de données structurées et une première version de RAG. C'est le point de départ parfait pour évoluer vers une architecture GraphRAG moderne.

La partie RAG actuelle est fonctionnelle mais limitée : elle utilise la recherche vectorielle sur des documents textuels et quelques requêtes SQL pré-définies, mais ne tire pas parti de la richesse des **relations structurelles** présentes dans les données RH.

## 🎯 Objectif : GraphRAG Multi-Modal avec Neo4j + Haystack 2.0

Implémenter une stratégie RAG multi-modale exploitant un graphe de connaissances, en s'intégrant à la structure existante et utilisant les **outils natifs modernes**.

### 📈 Avantages attendus

1. **Puissance d'expression** : Répondre à des questions relationnelles impossibles avant : 
   - *"Quelles sont les compétences communes des employés managés par Jean Dupont ?"*
   - *"Trouve-moi des experts en Python qui n'ont pas suivi de formation de management"*
   
2. **Précision** : Le contexte structuré du graphe réduit les hallucinations du LLM

3. **Explicabilité** : Traçabilité des relations utilisées dans la réponse

4. **Modularité** : Architecture pipeline explicite et extensible

---

## 🚀 Plan d'action optimisé (5-7 jours)

### Phase 1 : Construction du Graphe de Connaissances (2-3 jours)

#### 1. Installation des dépendances modernes

```bash
# Nouvelles dépendances (versions les plus récentes)
pip install neo4j-graphrag-python==0.1.0
pip install neo4j-haystack
pip install haystack-ai>=2.0
```

#### 2. Étape 8 : Construction automatisée du graphe

**Créer `src/e08_build_knowledge_graph.py`** utilisant les outils natifs Neo4j :

```python
from neo4j_graphrag.experimental.kg_construction import GraphKnowledgeConstructor
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from database import get_connection
import sqlite3

def run():
    """
    Étape 8: Construction automatisée du Graphe de Connaissances
    """
    print("Étape 8: Construction du Graphe de Connaissances (version moderne)")
    
    # Configuration Neo4j (via variables d'environnement ou config)
    neo4j_config = get_neo4j_config()  # À implémenter
    driver = GraphDatabase.driver(neo4j_config['uri'], auth=(neo4j_config['user'], neo4j_config['password']))
    
    # Extracteur automatique depuis SQLite
    sqlite_conn = sqlite3.connect(get_db_path())
    
    # Utiliser le constructeur natif Neo4j
    embeddings = OpenAIEmbeddings()
    constructor = GraphKnowledgeConstructor(driver, embeddings)
    
    # Auto-construction depuis les données relationnelles
    constructor.from_relational_data(
        sqlite_conn,
        entity_mappings={
            'employee': {'id': 'employee_id', 'properties': ['first_name', 'last_name', 'email']},
            'organizational_unit': {'id': 'unit_id', 'properties': ['name', 'description']},
            'skill': {'id': 'skill_id', 'properties': ['name', 'category']}
        },
        relationship_mappings={
            'MANAGES': ('employee', 'manager_id', 'employee', 'id'),
            'WORKS_IN': ('assignment', 'employee_id', 'organizational_unit', 'unit_id'),
            'HAS_SKILL': ('employee_skill', 'employee_id', 'skill', 'skill_id', {'level': 'level'})
        }
    )
    
    print("✅ Graphe de connaissances construit automatiquement")
```

#### 3. Intégration dans `main.py`

```python
# Ajouter l'étape 8
from src import e08_build_knowledge_graph as etape8

steps = {
    # ... étapes existantes
    '7': run_rag_indexation,
    '8': etape8.run  # Construction graphe
}
```

**Commande complète :**
```bash
python main.py 0 1 2 3 4 5 6 7 8 --raz  # Génération complète + graphe
```

---

### Phase 2 : Pipeline GraphRAG avec Haystack 2.0 (3-4 jours)

#### 1. Nouveau `rag/graphrag_pipeline.py`

Remplacer `rag/chain.py` par une architecture moderne basée sur les composants natifs :

```python
from haystack import Pipeline
from haystack.components.routers import ConditionalRouter
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator

# Composants Neo4j natifs
from neo4j_graphrag.retrievers import VectorRetriever, VectorCypherRetriever
from neo4j_graphrag.llm import OpenAILLM

class ModernSIRHGraphRAG:
    """Pipeline GraphRAG moderne avec Haystack 2.0"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.driver = self._connect_neo4j()
        
        # Pipeline principal
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self):
        """Construction du pipeline multi-stratégies"""
        
        # Classificateur de requêtes (amélioré)
        query_classifier = ConditionalRouter(routes=[
            {
                "condition": "{{ 'manager' in query or 'hiérarchie' in query or 'équipe' in query }}",
                "output": "{{query}}",
                "output_name": "graph_traversal_query",
                "output_type": str
            },
            {
                "condition": "{{ 'combien' in query or 'statistique' in query or 'total' in query }}",
                "output": "{{query}}",
                "output_name": "sql_aggregation_query", 
                "output_type": str
            },
            {
                "condition": "{{ True }}",  # Default case
                "output": "{{query}}",
                "output_name": "vector_search_query",
                "output_type": str
            }
        ])
        
        # Retrievers spécialisés (composants natifs)
        vector_retriever = VectorRetriever(
            driver=self.driver,
            index_name="employee_embeddings",
            embedder=OpenAIEmbeddings()
        )
        
        graph_traversal = VectorCypherRetriever(
            driver=self.driver,
            index_name="employee_embeddings", 
            embedder=OpenAIEmbeddings(),
            retrieval_query="""
            // Requête Cypher pour exploration hiérarchique
            MATCH (emp:Employee)-[:MANAGES*1..2]-(colleague:Employee)
            MATCH (colleague)-[:HAS_SKILL]->(skill:Skill)
            WHERE emp.name CONTAINS $query
            RETURN colleague.name, skill.name, skill.level
            """
        )
        
        sql_aggregator = self._create_sql_component()  # Wrapper SQL existant
        
        # LLM et prompt
        prompt_builder = PromptBuilder(template=self._get_system_prompt())
        llm = OpenAIGenerator(model="gpt-4o")
        
        # Construction du pipeline
        pipeline = Pipeline()
        pipeline.add_component("classifier", query_classifier)
        pipeline.add_component("vector_retriever", vector_retriever)
        pipeline.add_component("graph_traversal", graph_traversal)
        pipeline.add_component("sql_aggregator", sql_aggregator)
        pipeline.add_component("prompt_builder", prompt_builder)
        pipeline.add_component("llm", llm)
        
        # Connexions intelligentes
        pipeline.connect("classifier.graph_traversal_query", "graph_traversal.query_text")
        pipeline.connect("classifier.vector_search_query", "vector_retriever.query_text")
        pipeline.connect("classifier.sql_aggregation_query", "sql_aggregator.query")
        
        # Toutes les sorties vers le prompt builder
        pipeline.connect("vector_retriever.documents", "prompt_builder.documents")
        pipeline.connect("graph_traversal.documents", "prompt_builder.documents")  
        pipeline.connect("sql_aggregator.documents", "prompt_builder.documents")
        
        pipeline.connect("prompt_builder", "llm")
        
        return pipeline
    
    def query(self, question: str, session_id: str = None) -> dict:
        """Exécution du pipeline moderne"""
        
        result = self.pipeline.run({
            "classifier": {"query": question},
            "prompt_builder": {"question": question}
        })
        
        return {
            "answer": result["llm"]["replies"][0].content,
            "sources": self._extract_sources(result),
            "query_type": "graphrag_multi_modal",
            "session_id": session_id,
            "pipeline_trace": result.get("_debug", {})  # Traçabilité
        }
```

#### 2. Mise à jour `rag/api.py`

```python
# Remplacer SIRHRAGChain par ModernSIRHGraphRAG
from rag.graphrag_pipeline import ModernSIRHGraphRAG

@app.on_event("startup") 
async def startup_event():
    global rag_system
    
    config_path = os.getenv('FAKE_SIRH_2_CONFIG_FILE')
    load_config(config_path)
    
    base_config = get_config()
    rag_config = RAGConfig.from_base_config(base_config)
    
    # Nouveau système GraphRAG
    rag_system = ModernSIRHGraphRAG(rag_config)
    
    print("✅ Système GraphRAG moderne initialisé!")

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """API mise à jour avec GraphRAG"""
    
    response = rag_system.query(
        question=request.question, 
        session_id=request.session_id
    )
    
    return QueryResponse(**response)
```

---

## 🧪 Tests et Validation

### Queries de test GraphRAG

```python
# Tests pour valider les capacités GraphRAG
test_queries = [
    # Relations hiérarchiques
    "Qui sont les collègues directs de Marie Dubois ?",
    "Combien d'employés manages Jean Martin ?",
    
    # Compétences croisées  
    "Quels managers ont des compétences techniques ?",
    "Trouve les experts Python dans l'équipe de Sophie Bernard",
    
    # Analyses complexes
    "Quelles compétences manquent dans le département R&D ?",
    "Employés avec formations leadership mais sans équipe ?",
    
    # Agrégations (via SQL)
    "Répartition des scores de performance par département",
    "Budget formation total par unité organisationnelle"
]
```

---

## 🔧 Configuration et Déploiement

### Variables d'environnement étendues

```yaml
# config.yaml étendu
neo4j:
  uri: "neo4j://localhost:7687"
  user: "neo4j"
  password: "${NEO4J_PASSWORD}"
  database: "sirh"

graphrag:
  auto_sync: true  # Synchronisation auto SQLite → Neo4j
  retrieval_strategies: ["vector", "graph_traversal", "sql_aggregation"]
  embedding_model: "text-embedding-3-large"
  graph_traversal_depth: 2
```

### Commandes de gestion

```bash
# Génération complète avec GraphRAG
python main.py 0 1 2 3 4 5 6 7 8 --yaml=config.yaml --raz

# Synchronisation incrémentale
python main.py 8 --sync-only

# Démarrage API GraphRAG
python main.py --start-graphrag-api --port 8000

# Tests de validation
python -m pytest tests/test_graphrag.py -v
```

---

## 🎯 Livrables finaux

1. **Architecture GraphRAG moderne** avec Neo4j + Haystack 2.0
2. **Pipeline multi-stratégies** (vectoriel + graphe + SQL)
3. **API enrichie** avec traçabilité des requêtes
4. **Tests complets** couvrant les cas d'usage RH complexes
5. **Documentation** et guide de déploiement

**Temps estimé total : 5-7 jours** grâce aux outils natifs modernes.

Cette architecture positionnera Fake-SIRH-2 comme **référence GraphRAG dans le domaine RH** ! 🚀