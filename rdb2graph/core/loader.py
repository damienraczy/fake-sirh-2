from neo4j import GraphDatabase
from typing import Dict, List, Any
from pathlib import Path
import yaml

class Neo4jLoader:
    """Chargeur de données vers Neo4j"""
    
    def __init__(self, neo4j_config: Dict, mapping_config: Dict):
        self.neo4j_config = neo4j_config
        self.mapping_config = mapping_config
        self.driver = None
    
    def connect(self):
        """Établir la connexion Neo4j"""
        config = self.neo4j_config['neo4j']
        
        # Lire le mot de passe depuis le fichier
        password_file = Path(config['password_file']).expanduser()
        print(f"password_file] = {password_file}")
        # with open(config['password_file'], 'r') as f:
        with open(password_file, 'r') as f:
            password = f.read().strip()
        
        self.driver = GraphDatabase.driver(
            config['uri'],
            auth=(config['user'], password)
        )
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.driver:
            self.driver.close()
    
    def create_constraints_and_indexes(self, constraints_config: Dict):
        """Créer les contraintes et index"""
        with self.driver.session() as session:
            # Contraintes d'unicité
            for constraint in constraints_config.get('constraints', {}).get('uniqueness', []):
                query = f"""
                CREATE CONSTRAINT IF NOT EXISTS 
                FOR (n:{constraint['label']}) 
                REQUIRE n.{constraint['property']} IS UNIQUE
                """
                session.run(query)
                print(f"Contrainte créée: {constraint['label']}.{constraint['property']}")
            
            # Index simples
            for index in constraints_config.get('indexes', {}).get('single_property', []):
                query = f"""
                CREATE INDEX IF NOT EXISTS 
                FOR (n:{index['label']}) 
                ON (n.{index['property']})
                """
                session.run(query)
                print(f"Index créé: {index['label']}.{index['property']}")
    
    def clear_database(self):
        """Vider la base de données (mode full_replace)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Base de données vidée")
    
    def load_entities(self, entities_data: Dict[str, List[Dict]]):
        """Charger toutes les entités"""
        batch_size = self.neo4j_config.get('performance', {}).get('batch_size', 1000)
        
        for entity_name, data in entities_data.items():
            entity_config = self.mapping_config['entities'][entity_name]
            self._load_entity_batch(entity_name, entity_config, data, batch_size)
    
    def _load_entity_batch(self, entity_name: str, entity_config: Dict, data: List[Dict], batch_size: int):
        """Charger une entité par batch"""
        label = entity_config['node_label']
        primary_key_prop = None
        
        # Trouver la propriété clé primaire dans Neo4j
        for prop_config in entity_config['properties']:
            if isinstance(prop_config, dict):
                original_key = list(prop_config.keys())[0]
                if original_key == entity_config['primary_key']:
                    primary_key_prop = prop_config[original_key]['neo4j_property']
                    break
        
        if not primary_key_prop:
            primary_key_prop = entity_config['primary_key']
        
        print(f"Chargement de {len(data)} {entity_name}...")
        
        with self.driver.session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                query = f"""
                UNWIND $batch AS item
                MERGE (n:{label} {{{primary_key_prop}: item.{primary_key_prop}}})
                SET n += item
                """
                
                session.run(query, batch=batch)
                print(f"  Batch {i//batch_size + 1}: {len(batch)} enregistrements")
    
    def load_relationships(self, relationships_data: Dict[str, List[Dict]]):
        """Charger toutes les relations"""
        batch_size = self.neo4j_config.get('performance', {}).get('batch_size', 1000)
        
        for rel_name, data in relationships_data.items():
            rel_config = self.mapping_config['relationships'][rel_name]
            self._load_relationship_batch(rel_name, rel_config, data, batch_size)
    
    def _load_relationship_batch(self, rel_name: str, rel_config: Dict, data: List[Dict], batch_size: int):
        """Charger une relation par batch"""
        rel_type = rel_config['type']
        source_entity = self.mapping_config['entities'][rel_config['source_entity']]
        target_entity = self.mapping_config['entities'][rel_config['target_entity']]
        
        source_label = source_entity['node_label']
        target_label = target_entity['node_label']
        
        # Propriété clé pour la correspondance
        source_key_prop = self._get_neo4j_primary_key(source_entity)
        target_key_prop = self._get_neo4j_primary_key(target_entity)
        
        print(f"Chargement de {len(data)} relations {rel_name}...")
        
        with self.driver.session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                query = f"""
                UNWIND $batch AS item
                MATCH (source:{source_label} {{{source_key_prop}: item.source_id}})
                MATCH (target:{target_label} {{{target_key_prop}: item.target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                SET r += item.properties
                """
                
                session.run(query, batch=batch)
                print(f"  Batch {i//batch_size + 1}: {len(batch)} relations")
    
    def _get_neo4j_primary_key(self, entity_config: Dict) -> str:
        """Récupérer le nom de la propriété clé primaire en Neo4j"""
        for prop_config in entity_config['properties']:
            if isinstance(prop_config, dict):
                original_key = list(prop_config.keys())[0]
                if original_key == entity_config['primary_key']:
                    return prop_config[original_key]['neo4j_property']
        return entity_config['primary_key']