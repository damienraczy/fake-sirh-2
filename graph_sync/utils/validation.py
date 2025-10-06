from neo4j import Driver
from typing import Dict, List

class GraphValidator:
    """Validateur pour vérifier la cohérence du graphe"""
    
    def __init__(self, driver: Driver, mapping_config: Dict):
        self.driver = driver
        self.mapping_config = mapping_config
    
    def validate_import(self) -> bool:
        """Valider l'import complet"""
        print("🔍 Validation du graphe Neo4j...")
        
        checks = [
            self._check_node_counts(),
            self._check_relationship_counts(),
            self._check_data_integrity(),
            self._check_hierarchical_consistency()
        ]
        
        all_passed = all(checks)
        
        if all_passed:
            print("✅ Toutes les validations sont réussies")
        else:
            print("⚠️ Certaines validations ont échoué")
        
        return all_passed
    
    def _check_node_counts(self) -> bool:
        """Vérifier que les nœuds ont été créés"""
        print("\n📊 Vérification des comptes de nœuds...")
        passed = True
        
        with self.driver.session() as session:
            for entity_name, entity_config in self.mapping_config['entities'].items():
                label = entity_config['node_label']
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                count = result.single()['count']
                
                if count > 0:
                    print(f"  ✓ {label}: {count:,} nœuds")
                else:
                    print(f"  ✗ {label}: Aucun nœud trouvé")
                    passed = False
        
        return passed
    
    def _check_relationship_counts(self) -> bool:
        """Vérifier que les relations ont été créées"""
        print("\n🔗 Vérification des comptes de relations...")
        passed = True
        
        with self.driver.session() as session:
            for rel_name, rel_config in self.mapping_config['relationships'].items():
                rel_type = rel_config['type']
                result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                count = result.single()['count']
                
                if count > 0:
                    print(f"  ✓ {rel_type}: {count:,} relations")
                else:
                    print(f"  ✗ {rel_type}: Aucune relation trouvée")
                    passed = False
        
        return passed
    
    def _check_data_integrity(self) -> bool:
        """Vérifier l'intégrité des données"""
        print("\n🔐 Vérification de l'intégrité des données...")
        passed = True
        
        with self.driver.session() as session:
            # Vérifier les nœuds orphelins
            orphan_employees = session.run("""
                MATCH (e:Employee)
                WHERE NOT (e)-[:WORKS_IN]->()
                RETURN count(e) as count
            """).single()['count']
            
            if orphan_employees > 0:
                print(f"  ⚠️ {orphan_employees} employés sans affectation")
                passed = False
            else:
                print("  ✓ Tous les employés ont une affectation")
            
            # Vérifier les emails uniques
            duplicate_emails = session.run("""
                MATCH (e:Employee)
                WHERE e.email IS NOT NULL
                WITH e.email as email, count(e) as count
                WHERE count > 1
                RETURN count(*) as duplicates
            """).single()['duplicates']
            
            if duplicate_emails > 0:
                print(f"  ✗ {duplicate_emails} emails dupliqués")
                passed = False
            else:
                print("  ✓ Tous les emails sont uniques")
        
        return passed
    
    def _check_hierarchical_consistency(self) -> bool:
        """Vérifier la cohérence hiérarchique"""
        print("\n👥 Vérification de la hiérarchie...")
        passed = True
        
        with self.driver.session() as session:
            # Vérifier les cycles hiérarchiques
            cycles = session.run("""
                MATCH path = (e:Employee)-[:MANAGES*]->(e)
                RETURN count(path) as cycles
            """).single()['cycles']
            
            if cycles > 0:
                print(f"  ✗ {cycles} cycles hiérarchiques détectés")
                passed = False
            else:
                print("  ✓ Aucun cycle hiérarchique")
            
            # Vérifier l'existence d'un directeur général
            ceo_count = session.run("""
                MATCH (e:Employee)
                WHERE NOT (e)<-[:MANAGES]-()
                RETURN count(e) as ceo_count
            """).single()['ceo_count']
            
            if ceo_count == 1:
                print("  ✓ Un seul directeur général")
            elif ceo_count == 0:
                print("  ✗ Aucun directeur général trouvé")
                passed = False
            else:
                print(f"  ⚠️ {ceo_count} directeurs généraux (attendu: 1)")
        
        return passed
    

