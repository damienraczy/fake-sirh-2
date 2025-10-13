# rdb2graph/utils/neo4j_client.py (version corrigée et complétée)
from neo4j import GraphDatabase
from pathlib import Path
import yaml

class Neo4jClient:
    """Client Neo4j réutilisable"""
    
    def __init__(self, config_path: str = "graph_sync/config/neo4j_config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
        self.connect() # Connexion directe à l'initialisation
    
    def _load_config(self, config_path: str) -> dict:
        """Charger la configuration Neo4j"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def connect(self):
        """Établir la connexion"""
        if self.driver and self.driver.verify_connectivity():
            return
        
        config = self.config['neo4j']
        
        # Lire le mot de passe
        password_file = Path(config['password_file']).expanduser()
        if not password_file.exists():
            raise FileNotFoundError(f"Le fichier de mot de passe Neo4j est introuvable : {password_file}")
            
        with open(password_file, 'r') as f:
            password = f.read().strip()
        
        try:
            self.driver = GraphDatabase.driver(
                config['uri'],
                auth=(config['user'], password),
                **config.get('pool_config', {})
            )
            self.driver.verify_connectivity()
            print("✅ Connexion Neo4j établie.")
        except Exception as e:
            print(f"❌ Erreur de connexion Neo4j: {e}")
            self.driver = None
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def execute_query(self, query: str, parameters: dict = None):
        """Exécuter une requête"""
        if not self.driver:
            raise ConnectionError("Driver Neo4j non connecté.")
        with self.driver.session(database=self.config['neo4j']['database']) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # --- DEBUT DE LA MODIFICATION ---
    def get_schema_str(self) -> str:
        """
        Introspecte la base de données Neo4j pour générer une représentation textuelle
        du schéma, optimisée pour un prompt LLM.
        """
        if not self.driver:
            return "Schéma Neo4j indisponible (connexion échouée)."
        
        schema_parts = []
        
        with self.driver.session(database=self.config['neo4j']['database']) as session:
            # 1. Obtenir les labels des nœuds et leurs propriétés
            labels_query = "CALL db.labels() YIELD label"
            labels_result = session.run(labels_query).data()
            schema_parts.append("Node labels and properties:")
            for record in labels_result:
                label = record['label']
                props_query = f"MATCH (n:`{label}`) WITH n LIMIT 1 UNWIND keys(n) AS key RETURN collect(DISTINCT key) AS properties"
                props_result = session.run(props_query).single()
                properties = props_result['properties'] if props_result else []
                schema_parts.append(f"- Label: {label}, Properties: {properties}")

            # 2. Obtenir les types de relations et leur structure
            rels_query = "CALL db.schema.visualization()"
            rels_result = session.run(rels_query).data()
            schema_parts.append("\nRelationship types and structure:")
            
            # Formatter les relations pour être plus lisibles pour le LLM
            formatted_rels = set()
            for record in rels_result:
                nodes = record['nodes']
                relationships = record['relationships']
                
                # Assurer que la relation est bien formée
                if len(relationships) > 0 and len(nodes) == 2:
                    start_node_label = list(nodes[0].get('labels'))[0]
                    end_node_label = list(nodes[1].get('labels'))[0]
                    rel_type = relationships[0].get('type')
                    
                    formatted_rels.add(f"- (:`{start_node_label}`)-[:`{rel_type}`]->(:`{end_node_label}`)")

            schema_parts.extend(list(formatted_rels))

        return "\n".join(schema_parts)
    # --- FIN DE LA MODIFICATION ---

    def get_database_stats(self) -> dict:
        """Récupérer les statistiques de la base"""
        if not self.driver:
            return {}
        with self.driver.session(database=self.config['neo4j']['database']) as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            labels_result = session.run("CALL db.labels()")
            labels = [record['label'] for record in labels_result]
            rel_types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record['relationshipType'] for record in rel_types_result]
            
            return {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'node_labels': labels,
                'relationship_types': rel_types
            }