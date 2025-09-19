import sqlite3
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

class SQLiteExtractor:
    """Extracteur de données depuis SQLite"""
    
    def __init__(self, sqlite_path: str, mapping_config: Dict):
        self.sqlite_path = sqlite_path
        self.mapping_config = mapping_config
        self.connection = None
    
    def connect(self):
        """Établir la connexion SQLite"""
        self.connection = sqlite3.connect(self.sqlite_path)
        self.connection.row_factory = sqlite3.Row
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.connection:
            self.connection.close()
    
    def extract_entities(self) -> Dict[str, List[Dict]]:
        """Extraire toutes les entités définies dans le mapping"""
        entities_data = {}
        
        for entity_name, entity_config in self.mapping_config['entities'].items():
            print(f"Extraction de l'entité: {entity_name}")
            print(f"entity_config = {entity_config}")
            ret = self._extract_entity(entity_config)
            entities_data[entity_name] = ret
        
        return entities_data
    
    def _extract_entity(self, entity_config: Dict) -> List[Dict]:
        """Extraire une entité spécifique"""
        table_name = entity_config['table']
        print(f"table_name = {table_name}")
        # Construire la requête SELECT
        # columns = [prop for prop in entity_config['properties']]
        columns = [list(prop.keys())[0] for prop in entity_config['properties']]
        print(f"columns = {columns}")

        query = f"SELECT {', '.join(columns)} FROM {table_name}"
        print(f"query = {query}")
        
        cursor = self.connection.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def extract_relationships(self) -> Dict[str, List[Dict]]:
        """Extraire toutes les relations"""
        relationships_data = {}
        
        for rel_name, rel_config in self.mapping_config['relationships'].items():
            print(f"Extraction de la relation: {rel_name}")
            relationships_data[rel_name] = self._extract_relationship(rel_config)
        
        return relationships_data
    
    def _extract_relationship(self, rel_config: Dict) -> List[Dict]:
        """Extraire une relation spécifique"""
        if 'via_table' in rel_config:
            return self._extract_via_table_relationship(rel_config)
        else:
            return self._extract_direct_relationship(rel_config)
    
    def _extract_direct_relationship(self, rel_config: Dict) -> List[Dict]:
        """Relations directes via FK"""
        source_entity = self.mapping_config['entities'][rel_config['source_entity']]
        target_entity = self.mapping_config['entities'][rel_config['target_entity']]
        
        # La source de la relation est la table 'target' (ex: le manager)
        # La cible de la relation est la table 'source' (ex: l'employé)
        query = f"""
        SELECT t.{target_entity['primary_key']} as source_id,
               s.{source_entity['primary_key']} as target_id
        FROM {source_entity['table']} s
        JOIN {target_entity['table']} t ON s.{rel_config['source_key']} = t.{rel_config['target_key']}
        WHERE s.{rel_config['source_key']} IS NOT NULL
        """
        
        cursor = self.connection.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def _extract_via_table_relationship(self, rel_config: Dict) -> List[Dict]:
        """Relations via table de liaison"""
        via_table = rel_config['via_table']
        source_key = rel_config['source_key']
        target_key = rel_config['target_key']
        
        # Colonnes à sélectionner
        select_columns = [f"{source_key} as source_id", f"{target_key} as target_id"]
        
        # Ajouter les propriétés de la relation
        if 'properties' in rel_config:
            for prop in rel_config['properties']:
                if isinstance(prop, dict):
                    col_name = list(prop.keys())[0]
                    select_columns.append(col_name)
                else:
                    select_columns.append(prop)
        
        query = f"SELECT {', '.join(select_columns)} FROM {via_table}"
        
        # Ajouter condition si spécifiée
        if 'condition' in rel_config:
            query += f" WHERE {rel_config['condition']}"
        
        cursor = self.connection.execute(query)
        return [dict(row) for row in cursor.fetchall()]