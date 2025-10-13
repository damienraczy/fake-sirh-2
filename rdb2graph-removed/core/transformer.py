from typing import Dict, List, Any
from datetime import datetime

class DataTransformer:
    """Transformateur de données pour Neo4j"""
    
    def __init__(self, mapping_config: Dict):
        self.mapping_config = mapping_config
    
    def transform_entities(self, entities_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Transformer toutes les entités pour Neo4j"""
        transformed = {}
        
        for entity_name, data in entities_data.items():
            entity_config = self.mapping_config['entities'][entity_name]
            transformed[entity_name] = [
                self._transform_entity_record(record, entity_config) 
                for record in data
            ]
        
        return transformed
    
    def _transform_entity_record(self, record: Dict, entity_config: Dict) -> Dict:
        """Transformer un enregistrement d'entité"""
        transformed = {}
        
        for prop_config in entity_config['properties']:
            if isinstance(prop_config, dict):
                original_key = list(prop_config.keys())[0]
                prop_details = prop_config[original_key]
                neo4j_key = prop_details['neo4j_property']
                prop_type = prop_details['type']
                
                if original_key in record:
                    transformed[neo4j_key] = self._convert_type(record[original_key], prop_type)
            else:
                # Propriété simple (string)
                if prop_config in record:
                    transformed[prop_config] = record[prop_config]
        
        return transformed
    
    def transform_relationships(self, relationships_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Transformer toutes les relations pour Neo4j"""
        transformed = {}
        
        for rel_name, data in relationships_data.items():
            rel_config = self.mapping_config['relationships'][rel_name]
            transformed[rel_name] = [
                self._transform_relationship_record(record, rel_config)
                for record in data
            ]
        
        return transformed
    
    def _transform_relationship_record(self, record: Dict, rel_config: Dict) -> Dict:
        """Transformer un enregistrement de relation"""
        transformed = {Bis
            'source_id': record['source_id'],
            'target_id': record['target_id'],
            'properties': {}
        }
        
        if 'properties' in rel_config:
            for prop_config in rel_config['properties']:
                if isinstance(prop_config, dict):
                    original_key = list(prop_config.keys())[0]
                    prop_details = prop_config[original_key]
                    neo4j_key = prop_details['neo4j_property']
                    prop_type = prop_details['type']
                    
                    if original_key in record:
                        transformed['properties'][neo4j_key] = self._convert_type(record[original_key], prop_type)
        
        return transformed
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convertir un type de données"""
        if value is None:
            return None
        
        if target_type == 'integer':
            return int(value)
        elif target_type == 'float':
            return float(value)
        elif target_type == 'boolean':
            return bool(value)
        elif target_type == 'date':
            if isinstance(value, str):
                return datetime.strptime(value, '%Y-%m-%d').date()
            return value
        else:  # string par défaut
            return str(value)