# Fake-SIRH-2 : Simulateur de Données RH et Moteur RAG

Ce projet génère une base de données SIRH (Système d'Information des Ressources Humaines) réaliste et l'exploite via une API conversationnelle (RAG) pour répondre à des questions sur les données générées.

## 🏗️ Architecture

Le projet est divisé en deux parties principales :

1.  **Générateur de Données** : Un ensemble de scripts Python (`src/`) qui utilisent un LLM pour peupler une base de données SQLite en se basant sur une configuration (`config.yaml`).
2.  **Moteur RAG** : Une API FastAPI (`rag/`) qui indexe les données générées et expose une interface de chat pour les interroger en langage naturel.

La structure des fichiers clés est la suivante :
```

fake-sirh-2/
├── main.py                          # Point d'entrée pour la génération et le lancement
├── config.yaml                      # Fichier de configuration principal
├── schema.sql                       # Schéma de la base de données
├── src/                             # Scripts de génération par étapes
├── prompts/                         # Prompts utilisés par le LLM
├── rag/                             # Logique du RAG et de l'API
└── templates/                       # Interface web du chat

```

## 🚀 Utilisation

Assurez-vous d'avoir installé les dépendances requises :
```bash
pip install -r requirements.txt
```

### 1. Génération des Données

Vous pouvez générer les données en une seule fois ou étape par étape.

**Génération complète (recommandé)** :
Cette commande supprime les anciennes données, initialise la base, exécute toutes les étapes de génération et indexe les données pour le RAG.

```bash
python main.py 0 1 2 3 4 5 6 7 --raz
```

**Génération par étapes** :

```bash
# Initialiser et créer la structure
python main.py 0 1 --yaml=config.yaml

# Ajouter la population et les compétences
python main.py 2 3

# Valider la cohérence des données
python main.py --validate
```

### 2. Démarrage de l'API RAG

Une fois les données générées et l'étape 7 (indexation) terminée, lancez l'API :

```bash
python main.py --start-api --port 8000
```

  * **Interface de chat** : [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000)
  * **Documentation de l'API** : [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)

## 🔧 Configuration

L'ensemble de l'entreprise simulée (nom, secteur, taille, culture, etc.) peut être personnalisé dans le fichier `config.yaml`.