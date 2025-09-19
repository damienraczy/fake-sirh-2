import argparse
import sys
from pathlib import Path
from .core.sync_manager import SyncManager

def main():
    """Interface en ligne de commande pour RDB2Graph"""
    parser = argparse.ArgumentParser(description="Synchronisation SQLite vers Neo4j")
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande sync
    sync_parser = subparsers.add_parser('sync', help='Synchroniser les données')
    sync_parser.add_argument('--sqlite-path', required=True, help='Chemin vers la base SQLite')
    sync_parser.add_argument('--mode', choices=['full', 'incremental'], default='full')
    sync_parser.add_argument('--config-dir', default='rdb2graph/config', help='Répertoire de configuration')
    
    # Commande stats
    stats_parser = subparsers.add_parser('stats', help='Afficher les statistiques')
    stats_parser.add_argument('--config-dir', default='rdb2graph/config')
    
    # Commande validate
    validate_parser = subparsers.add_parser('validate', help='Valider le graphe')
    validate_parser.add_argument('--config-dir', default='rdb2graph/config')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        sync_manager = SyncManager(args.config_dir)
        
        if args.command == 'sync':
            if args.mode == 'full':
                sync_manager.sync_full_replace(args.sqlite_path)
            else:
                print("Mode incrémental pas encore implémenté")
                sys.exit(1)
        
        elif args.command == 'stats':
            stats = sync_manager.get_stats()
            print("\n📊 Statistiques Neo4j:")
            print("\nNœuds:")
            for label, count in stats['nodes'].items():
                print(f"  {label}: {count:,}")
            print("\nRelations:")
            for rel_type, count in stats['relationships'].items():
                print(f"  {rel_type}: {count:,}")
        
        elif args.command == 'validate':
            from .utils.validation import GraphValidator
            loader = Neo4jLoader(sync_manager.neo4j_config, sync_manager.mapping_config)
            loader.connect()
            try:
                validator = GraphValidator(loader.driver, sync_manager.mapping_config)
                validator.validate_import()
            finally:
                loader.disconnect()
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()