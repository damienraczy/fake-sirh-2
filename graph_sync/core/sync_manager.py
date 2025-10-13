import yaml
from pathlib import Path
from .extractor import SQLiteExtractor
from .transformer import DataTransformer
from .loader import Neo4jLoader
from ..utils.validation import GraphValidator

class SyncManager:
    """Gestionnaire de synchronisation SQLite → Neo4j"""
    
    def __init__(self, config_dir: str = "graph_sync/config"):
        self.config_dir = Path(config_dir)
        self.mapping_config = self._load_yaml(self.config_dir / "mapping.yaml")
        self.neo4j_config = self._load_yaml(self.config_dir / "neo4j_config.yaml")
        self.constraints_config = self._load_yaml(self.config_dir / "constraints.yaml")
    
    def _load_yaml(self, file_path: Path) -> dict:
        """Charger un fichier YAML"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def sync_full_replace(self, sqlite_path: str):
        """Synchronisation complète avec remplacement"""
        print("🔄 Synchronisation complète SQLite → Neo4j")
        
        # Mise à jour du chemin SQLite
        self.mapping_config['database']['sqlite_path'] = sqlite_path
        
        # Initialisation des composants
        extractor = SQLiteExtractor(sqlite_path, self.mapping_config)
        transformer = DataTransformer(self.mapping_config)
        loader = Neo4jLoader(self.neo4j_config, self.mapping_config)
        
        try:
            # Connexions
            extractor.connect()
            loader.connect()
            
            # 1. Vider Neo4j
            print("1. Vidage de la base Neo4j...")
            loader.clear_database()
            
            # 2. Créer contraintes et index
            print("2. Création des contraintes et index...")
            loader.create_constraints_and_indexes(self.constraints_config)
            
            # 3. Extraction des données
            print("3. Extraction des données SQLite...")
            entities_data = extractor.extract_entities()
            relationships_data = extractor.extract_relationships()
            
            # 4. Transformation
            print("4. Transformation des données...")
            transformed_entities = transformer.transform_entities(entities_data)
            transformed_relationships = transformer.transform_relationships(relationships_data)
            
            # 5. Chargement
            print("5. Chargement vers Neo4j...")
            loader.load_entities(transformed_entities)
            loader.load_relationships(transformed_relationships)
            
            # 6. Validation (optionnel)
            if self.mapping_config.get('sync_config', {}).get('validation_after_import', False):
                print("6. Validation post-import...")
                validator = GraphValidator(loader.driver, self.mapping_config)
                validator.validate_import()
            
            print("✅ Synchronisation terminée avec succès")
            
        finally:
            extractor.disconnect()
            loader.disconnect()
    
    def get_stats(self) -> dict:
        """Récupérer les statistiques de la base Neo4j"""
        loader = Neo4jLoader(self.neo4j_config, self.mapping_config)
        
        try:
            loader.connect()
            
            with loader.driver.session() as session:
                # Compter les nœuds par label
                node_counts = {}
                for entity_name, entity_config in self.mapping_config['entities'].items():
                    label = entity_config['node_label']
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    node_counts[label] = result.single()['count']
                
                # Compter les relations par type
                rel_counts = {}
                for rel_name, rel_config in self.mapping_config['relationships'].items():
                    rel_type = rel_config['type']
                    result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                    rel_counts[rel_type] = result.single()['count']
                
                return {
                    'nodes': node_counts,
                    'relationships': rel_counts
                }
        
        finally:
            loader.disconnect()