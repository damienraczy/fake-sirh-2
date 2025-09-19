# Utilisation

```bash
# Créer le fichier de mot de passe Neo4j
echo "votre_mot_de_passe" > ~/.neo4j_password
chmod 600 ~/.neo4j_password

# Configurer Neo4j si nécessaire
# Adapter rdb2graph/config/neo4j_config.yaml selon votre installation
```

# Utilisation

```bash
# Génération complète avec synchronisation Neo4j
python main.py 0 1 2 3 4 5 6 7 8 --yaml=config.yaml --raz

# Synchronisation uniquement
python -m rdb2graph.cli sync --sqlite-path db/experts_bois.sqlite

# Statistiques du graphe
python -m rdb2graph.cli stats

# Validation du graphe
python -m rdb2graph.cli validate

# Resynchronisation après modification des données
python main.py 8 --yaml=config.yaml
```

