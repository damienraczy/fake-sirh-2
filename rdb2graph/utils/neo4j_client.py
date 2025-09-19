### `rdb2graph/utils/neo4j_client.py`
from neo4j import GraphDatabase
from pathlib import Path
import yaml

class Neo4jClient:
    """Client Neo4j réutilisable"""
    
    def __init__(self, config_path: str = "rdb2graph/config/neo4j_config.yaml"):
        self.config = self._load_config(config_path)
        self.driver = None
    
    def _load_config(self, config_path: str) -> dict:
        """Charger la configuration Neo4j"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def connect(self):
        """Établir la connexion"""
        if self.driver:
            return
        
        config = self.config['neo4j']
        
        # Lire le mot de passe
        print(f"password_file = {password_file}")
        password_file = Path(config['password_file']).expanduser()
        print(f"password_file expanded = {password_file}")
        with open(password_file, 'r') as f:
            password = f.read().strip()
        
        self.driver = GraphDatabase.driver(
            config['uri'],
            auth=(config['user'], password),
            **config.get('pool_config', {})
        )
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def execute_query(self, query: str, parameters: dict = None):
        """Exécuter une requête"""
        with self.driver.session() as session:
            return session.run(query, parameters or {})
    
    def get_database_stats(self) -> dict:
        """Récupérer les statistiques de la base"""
        with self.driver.session() as session:
            # Compter tous les nœuds
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            
            # Compter toutes les relations
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            # Labels disponibles
            labels_result = session.run("CALL db.labels()")
            labels = [record['label'] for record in labels_result]
            
            # Types de relations
            rel_types_result = session.run("CALL db.relationshipTypes()")
            rel_types = [record['relationshipType'] for record in rel_types_result]
            
            return {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'node_labels': labels,
                'relationship_types': rel_types
            }