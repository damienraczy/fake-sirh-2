# =============================================================================
# data_generation/steps/e08_neo4j_sync.py
# =============================================================================

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from core.config import get_config
from graph_sync.core.sync_manager import SyncManager

def run():
    """
    Étape 8: Synchronisation Neo4j
    Tables: Toutes -> Neo4j Graph Database
    """
    print("Étape 8: Synchronisation de la base de données vers Neo4j")
    
    config = get_config()
    entreprise = config['entreprise']
    db_path = f"{entreprise['base_de_données']['chemin']}/{entreprise['base_de_données']['nom']}"
    
    if not Path(db_path).exists():
        print(f"❌ Erreur: Base de données introuvable à {db_path}")
        print("   Assurez-vous d'avoir exécuté les étapes précédentes (0-7)")
        return
    
    try:
        print(f"Base de données source: {db_path}")
        print("Configuration Neo4j: graph_sync/config/")
        
        # Initialiser le gestionnaire de synchronisation
        sync_manager = SyncManager(config_dir="graph_sync/config")
        
        # Effectuer la synchronisation complète avec remplacement
        print("\n🔄 Démarrage de la synchronisation complète...")
        sync_manager.sync_full_replace(db_path)
        
        # Afficher les statistiques détaillées
        print("\n" + "="*60)
        stats = sync_manager.get_stats()
        
        print("📊 STATISTIQUES NEO4J")
        print("="*60)
        
        print("\n📦 Nœuds créés:")
        total_nodes = 0
        for label, count in sorted(stats['nodes'].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {label:<25} {count:>6,} nœuds")
            total_nodes += count
        print(f"  {'─'*35}")
        print(f"  {'TOTAL':<25} {total_nodes:>6,} nœuds")
        
        print("\n🔗 Relations créées:")
        total_rels = 0
        for rel_type, count in sorted(stats['relationships'].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {rel_type:<25} {count:>6,} relations")
            total_rels += count
        print(f"  {'─'*35}")
        print(f"  {'TOTAL':<25} {total_rels:>6,} relations")
        
        print("\n" + "="*60)
        print("✅ Synchronisation Neo4j terminée avec succès!")
        print("="*60)
        
        # Informations d'accès
        print("\n🌐 Accès Neo4j Browser:")
        print("   URL: http://localhost:7474")
        print("   Utilisateur: neo4j")
        print("   (Mot de passe configuré dans ~/.neo4j_password)")
        
        print("\n💡 Exemples de requêtes Cypher:")
        print("   // Visualiser la hiérarchie")
        print("   MATCH (e:Employee)-[:MANAGES]->(s:Employee)")
        print("   RETURN e, s LIMIT 25")
        print()
        print("   // Employés par département")
        print("   MATCH (e:Employee)-[:WORKS_IN]->(u:OrganizationalUnit)")
        print("   RETURN u.nom as Département, count(e) as Effectif")
        print("   ORDER BY Effectif DESC")
        
    except FileNotFoundError as e:
        print(f"❌ Erreur de configuration: {e}")
        print("   Vérifiez que les fichiers de configuration Neo4j sont présents:")
        print("   - graph_sync/config/neo4j_config.yaml")
        print("   - graph_sync/config/mapping.yaml")
        print("   - graph_sync/config/constraints.yaml")
        print("   - ~/.neo4j_password")
        raise
        
    except ConnectionError as e:
        print(f"❌ Erreur de connexion Neo4j: {e}")
        print("   Vérifiez que Neo4j est démarré:")
        print("   - Service Neo4j actif (port 7687)")
        print("   - Identifiants corrects dans ~/.neo4j_password")
        raise
        
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation Neo4j: {e}")
        print("\n🔍 Dépannage:")
        print("   1. Vérifier que Neo4j est installé et démarré")
        print("   2. Vérifier le fichier ~/.neo4j_password")
        print("   3. Vérifier les configurations dans graph_sync/config/")
        print("   4. Consulter les logs Neo4j pour plus de détails")
        raise

if __name__ == "__main__":
    # Permet de tester l'étape individuellement
    from core.config import load_config
    
    # Charger la configuration par défaut
    load_config('config.yaml')
    
    # Exécuter l'étape
    run()