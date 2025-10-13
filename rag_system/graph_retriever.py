# rag/graph_retriever.py
from typing import List, Dict, Any
from data_generation.utils.llm_client import generate_text
# Importer votre client Neo4j
from graph_sync.utils.neo4j_client import Neo4jClient

class SIRHGraphRetriever:
    def __init__(self, config):
        self.config = config
        self.neo4j_client = Neo4jClient()
        self.graph_schema = self._get_graph_schema()
        self.cypher_prompt_template = self._load_cypher_prompt()
        print("✓ Graph Retriever initialisé.")

    def _load_cypher_prompt(self) -> str:
        # Idéalement, ce prompt serait dans un fichier "prompts/text_to_cypher.txt"
        cypher_prompt = ""
        with open('rag_system/prompts/load_cypher_prompt.txt', 'r', encoding='utf-8') as f:
            cypher_prompt = f.read()
        return cypher_prompt

    def _get_graph_schema(self) -> str:
        """Récupère le schéma du graphe Neo4j."""
        # Cette fonction exécute des requêtes pour introspecter le schéma
        # et le formater en texte pour le prompt.
        try:
            return self.neo4j_client.get_schema_str()
        except Exception as e:
            print(f"Erreur lors de la récupération du schéma Neo4j: {e}")
            return "Schéma indisponible."

    def get_context(self, question: str) -> List[Dict[str, Any]]:
        """Convertit une question en Cypher, l'exécute et retourne le contexte."""
        print(f"Génération de la requête Cypher pour : '{question}'")

        # 1. Générer la requête Cypher
        prompt = self.cypher_prompt_template.format(schema=self.graph_schema, question=question)
        cypher_query = generate_text(prompt).strip()
        print(f"  -> Requête Cypher générée : {cypher_query}")

        # 2. Exécuter la requête
        results = self.neo4j_client.execute_query(cypher_query)

        if not results:
            return [{'content': "Aucun résultat trouvé dans le graphe pour cette question.", 'metadata': {'source': 'graph_query_empty'}}]

        # 3. Formatter les résultats
        content = f"Résultat de la recherche sur le graphe pour '{question}':\n" + "\n".join([str(record) for record in results])
        return [{'content': content, 'metadata': {'source': 'graph_query', 'query': cypher_query}}]