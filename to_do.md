"Fake-SIRH-2" est une base de travail avec un générateur de données structurées et une première version de RAG. C'est le point de départ pour évoluer vers une architecture plus sophistiquée comme le GraphRAG.

La partie RAG actuelle est une "preview". Elle fait ce qu'elle fait (recherche vectorielle sur des documents textuels et quelques requêtes SQL pré-définies), mais elle ne tire pas parti de la richesse des relations* implicites dans les données existantes.

On peut faire évoluer le projet pour implémenter une stratégie RAG multi-modale exploitant un graphe de connaissances, en s'intégrant à la structure existante et en utilisant **Haystack**.

### Plan d'action en 2 phases

1.  **Phase 1 : Création du Graphe de Connaissances (ETL)**. Ajouter une nouvelle étape au générateur pour synchroniser les données de SQLite vers Neo4j.
2.  **Phase 2 : Refonte du RAG avec Haystack**. Remplacer la logique de `rag/chain.py` par un pipeline Haystack qui orchestre intelligemment les différentes stratégies de recherche (Graphe, Vecteur, SQL).

### Phase 1 : Créer le Graphe de Connaissances (ETL depuis SQLite)

Créer une nouvelle étape, `e08_build_knowledge_graph.py`, qui s'exécutera après la génération complète de la base SQLite.

#### 1. Nouvelles dépendances

Ajouts `requirements.txt` :

```bash
# pip install neo4j haystack-ai neo4j-haystack
```

#### 2. Script `src/e08_build_knowledge_graph.py`

Ce script se connectera à  SQLite et peuplera Neo4j.

**Modélisation du graphe :**

  * **Nœuds** : `:Employe`, `:UniteOrga`, `:Poste`, `:Competence`, `:Formation`, `:Document`.
  * **Propriétés** : Les colonnes des tables SQL (ex: `first_name`, `email` sur le nœud `:Employe`).
  * **Relations** : 
      * `employee.manager_id` → `(:Employe)-[:MANAGE]->(:Employe)`
      * `assignment` → `(:Employe)-[:OCCUPE]->(:Poste)`, `(:Employe)-[:EST_AFFECTE_A]->(:UniteOrga)`
      * `employee_skill` → `(:Employe)-[:POSSEDE_COMPETENCE]->(:Competence)`
      * `training_record` → `(:Employe)-[:A_SUIVI]->(:Formation)`

**Exemple de code pour `e08_build_knowledge_graph.py` :**

```python
# src/e08_build_knowledge_graph.py
import sqlite3
from neo4j import GraphDatabase
from database import get_db_path # Vous avez déjà cette fonction

# --- Mettre vos identifiants Neo4j ici ou dans un .env ---
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "mot_de_passe"

def run():
    """
    Étape 8: Construction du Graphe de Connaissances Neo4j depuis SQLite.
    """
    print("Étape 8: Construction du Graphe de Connaissances")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    sqlite_conn = sqlite3.connect(get_db_path())
    sqlite_conn.row_factory = sqlite3.Row

    with driver.session() as session:
        # Nettoyer le graphe pour une reconstruction complète
        session.run("MATCH (n) DETACH DELETE n")
        print("Ancien graphe nettoyé.")

        # 1. Créer les nœuds :Employe
        employees = sqlite_conn.execute("SELECT id, first_name, last_name, email, hire_date FROM employee").fetchall()
        for emp in employees:
            session.run("""
                MERGE (e:Employe {sqlite_id: $id})
                SET e.prenom = $first_name, e.nom = $last_name, e.email = $email, e.date_embauche = $hire_date
            """, dict(emp))
        print(f"✓ {len(employees)} nœuds :Employe créés.")

        # 2. Créer les nœuds :Competence, :UniteOrga, etc. (même logique)
        # ... (code pour les autres types de nœuds)

        # 3. Créer les relations hiérarchiques
        managers = sqlite_conn.execute("SELECT id, manager_id FROM employee WHERE manager_id IS NOT NULL").fetchall()
        for emp in managers:
            session.run("""
                MATCH (e:Employe {sqlite_id: $emp_id})
                MATCH (m:Employe {sqlite_id: $manager_id})
                MERGE (m)-[:MANAGE]->(e)
            """, emp_id=emp['id'], manager_id=emp['manager_id'])
        print(f"✓ {len(managers)} relations :MANAGE créées.")

        # 4. Créer les relations d'affectation
        assignments = sqlite_conn.execute("SELECT employee_id, position_id, unit_id FROM assignment WHERE end_date IS NULL").fetchall()
        # ... (code pour créer les relations :OCCUPE et :EST_AFFECTE_A)

        # ... (code pour les autres relations :POSSEDE_COMPETENCE, etc.)

    driver.close()
    sqlite_conn.close()
    print("✅ Graphe de connaissances construit avec succès.")

```

#### 3. Mettre à jour `main.py`

Ajouter l'étape 8 à `main.py`.

```python
# dans main.py
from src import e08_build_knowledge_graph as etape8

def main():
    # ...
    steps = {
        # ...
        '7': run_rag_indexation,
        '8': etape8.run  # Nouvelle étape
    }
    # ...
```

Maintenant, après avoir généré vos données, vous pouvez lancer `python main.py 8` pour peupler Neo4j.

-----

### Phase 2 : Refondre le RAG avec un Pipeline Haystack Multi-Stratégies

Remplacer `rag/chain.py` par une nouvelle logique plus puissante.
`_classify_query` était une excellente intuition ; formaliser dans un pipeline Haystack.

Le pipeline aura un **routeur** qui choisira la meilleure stratégie pour répondre à la question.

#### 1. Le nouveau `rag/pipeline.py` (remplace `chain.py`)

```python
# rag/pipeline.py
from haystack import Pipeline
from haystack.components.routers import ConditionalRouter
from haystack.components.generators.chat import OpenAIChatGenerator # Ou autre LLM
from haystack.components.builders import PromptBuilder
# ... autres imports Haystack et Neo4j

# --- Composants personnalisés ---
# Vous allez créer ces classes, qui sont le coeur de la logique.

class QueryClassifier(BaseComponent):
    """Décide quelle est la meilleure stratégie pour la question."""
    def run(self, query: str):
        # Logique pour classifier la question (peut utiliser un LLM ou des mots-clés)
        # Ex: 'qui est le manager de X ?' -> 'graph_query'
        # Ex: 'résume la performance de Y' -> 'vector_search'
        # Ex: 'combien d'employés par département ?' -> 'sql_query'
        
        if "manager de" in query or "collègues de" in query:  # condition trop basique à remplacer par une logique plus puissante
            return {"graph_query": query}
        elif "combien" in query or "statistique" in query:    # condition trop basique à remplacer par une logique plus puissante
             return {"sql_query": query}
        else:
            return {"vector_search": query}

class TextToCypherRetriever(BaseComponent):
    """Prend une question et la transforme en requête Cypher."""
    def run(self, query: str):
        # Utilise un LLM avec un prompt spécifique pour générer du Cypher
        # Exécute la requête sur Neo4j
        # Retourne les résultats sous forme de documents
        # on va le faire réaliser par gpt oss 20b par ollama pro
        # ...
        return {"documents": cypher_results_as_docs}

class VectorGraphRetriever(BaseComponent):
    """Combine recherche vectorielle et expansion de graphe."""
    def run(self, query: str):
        # 1. Utiliser Neo4jEmbeddingRetriever pour trouver les nœuds de départ
        initial_nodes = neo4j_vector_retriever.run(query)
        
        # 2. Pour chaque nœud trouvé, exécuter une requête Cypher pour explorer le voisinage
        #    MATCH (n)-[*1..2]-(m) WHERE id(n) = <id_noeud> RETURN m
        #    C'est l'expansion de graphe
        # ...
        
        # 3. Formater les résultats en documents pour le LLM
        return {"documents": combined_results_as_docs}

class SQLRetrieverComponent(BaseComponent):
    """Wrapper pour SIRHSQLRetriever existant."""
    def run(self, query: str):
        # Appelle SIRHSQLRetriever pour exécuter une requête SQL
        ...
        return {"documents": sql_results_as_docs}


# --- Le Pipeline Principal ---
# Initialisation des composants
query_classifier = QueryClassifier()
text_to_cypher = TextToCypherRetriever()
vector_graph_retriever = VectorGraphRetriever()
sql_retriever_component = SQLRetrieverComponent()

# Le routeur qui aiguille la requête
router = ConditionalRouter(
    routes=[
        {"condition": "{{'graph_query' in inputs}}", "output": "{{inputs['graph_query']}}", "next_node": "text_to_cypher"},
        {"condition": "{{'sql_query' in inputs}}", "output": "{{inputs['sql_query']}}", "next_node": "sql_retriever"},
        {"condition": "{{'vector_search' in inputs}}", "output": "{{inputs['vector_search']}}", "next_node": "vector_graph_retriever"},
    ]
)

# Le reste du pipeline (commun à toutes les branches)
prompt_builder = PromptBuilder(template="...")
llm = OpenAIChatGenerator()

# Construction du pipeline
rag_pipeline = Pipeline()
rag_pipeline.add_component("classifier", query_classifier)
rag_pipeline.add_component("router", router)
rag_pipeline.add_component("text_to_cypher", text_to_cypher)
rag_pipeline.add_component("vector_graph_retriever", vector_graph_retriever)
rag_pipeline.add_component("sql_retriever", sql_retriever_component)

rag_pipeline.add_component("prompt_builder", prompt_builder)
rag_pipeline.add_component("llm", llm)

# Connexions
rag_pipeline.connect("classifier", "router")
rag_pipeline.connect("router.text_to_cypher", "text_to_cypher.query")
rag_pipeline.connect("router.vector_graph_retriever", "vector_graph_retriever.query")
rag_pipeline.connect("router.sql_retriever", "sql_retriever.query")

# On connecte la sortie de tous les retrievers au prompt_builder
rag_pipeline.connect("text_to_cypher.documents", "prompt_builder.documents")
rag_pipeline.connect("vector_graph_retriever.documents", "prompt_builder.documents")
rag_pipeline.connect("sql_retriever.documents", "prompt_builder.documents")

rag_pipeline.connect("prompt_builder.prompt", "llm.prompt")
```

#### 2. Mettre à jour `rag/api.py`

L'API FastAPI n'appellera plus `SIRHRAGChain`, mais exécutera le pipeline Haystack.

```python
# rag/api.py (extrait)
from rag.pipeline import rag_pipeline # Importer le pipeline

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    # ...
    try:
        # Exécuter le pipeline Haystack
        response = rag_pipeline.run({
            "classifier": {"query": request.question},
            "prompt_builder": {"question": request.question}
        })
        
        # Formater la réponse pour le modèle Pydantic
        answer = response["llm"]["replies"][0]
        # ...
        
        return QueryResponse(...)

    except Exception as e:
        # ...
```

### Avantages de cette nouvelle architecture

1.  **Puissance d'expression** : Vous pouvez répondre à des questions relationnelles impossibles avant : "Quelles sont les compétences communes des employés managés par Jean Dupont ?" ou "Trouve-moi des experts en Python qui n'ont pas suivi de formation de management".
2.  **Précision** : En récupérant un sous-graphe, le contexte fourni au LLM est structuré et moins ambigu, réduisant les hallucinations.
3.  **Modularité (Haystack)** : Le pipeline est explicite. Vous pouvez facilement ajouter une nouvelle stratégie de recherche (par exemple, une recherche hybride) en ajoutant une branche au routeur, sans toucher au reste.
4.  **Réutilisation** : Vous conservez le générateur de données et vous réutilisez même la logique de `SIRHSQLRetriever` à l'intérieur d'un composant Haystack.

C'est un travail de refonte significatif, mais il capitalise sur la base existante pour construire un système RAG véritablement "intelligent" et capable de raisonner sur les relations complexes de vos données RH.