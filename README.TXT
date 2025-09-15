## **🏗️ Architecture du projet**

**Structure des fichiers :**
```
fake-sirh-2/
├── main.py                          # Point d'entrée principal
├── config.py                        # Gestion configuration 
├── config.yaml                      # Configuration entreprise
├── llm_client.py                    # Client Ollama (déjà existant)
├── database.py                      # Gestion BDD (déjà existant)
├── utils_llm.py                     # Utilitaires LLM (déjà existant)
├── schema.sql                       # Schéma BDD complet 12 tables
├── etapes/
│   ├── e00_initialisation.py        # Étape 0 (existante)
│   ├── e01_structure_organisationnelle.py
│   ├── e02_population_hierarchie.py
│   ├── e03_competences_referentiels.py
│   ├── e04_objectifs_performance.py
│   ├── e05_formations_developpement.py
│   └── e06_feedback_documents.py
├── utils/
│   └── validation.py                # Validation cohérence
├── prompts/                         # Prompts séparés en anglais
│   ├── 01_organizational_structure.txt
│   ├── 02_employee_generation.txt
│   ├── 03_skills_generation.txt
│   ├── 03_employee_skills_assignment.txt
│   ├── 04_goals_generation.txt
│   ├── 04_performance_review.txt
│   ├── 05_training_catalog.txt
│   ├── 05_training_assignment.txt
│   ├── 06_feedback_generation.txt
│   └── 06_document_generation.txt
└── data/
    └── documents/                   # Documents générés
```

## **🎯 Points clés de l'implémentation**

### **Conformité aux spécifications :**
- **Prompts en anglais** dans des fichiers `.txt` séparés
- **API Ollama.com** (pas local) via `llm_client.py` existant
- **Génération progressive** en 6 étapes (+ initialisation)
- **Validation automatique** de la cohérence
- **Documents physiques** créés pour le RAG

### **Utilisation :**
```bash
# Génération complète
python main.py 0 1 2 3 4 5 6 --yaml=config.yaml --raz

# Génération par étapes
python main.py 1 2 --yaml=config.yaml
python main.py 3 4 5 --continue

# Avec validation
python main.py 0 1 2 3 4 5 6 --validate
```

### **Configuration entreprise :**
Le fichier `config.yaml` permet de paramétrer entièrement l'entreprise simulée (secteur, taille, culture, défis, etc.).

### **Cohérence garantie :**
- Génération **séquentielle** (chaque étape utilise les précédentes)
- **Validation automatique** après génération
- **Prompts contextualisés** avec profil d'entreprise
- **Documents physiques** pour enrichir le RAG

Cette architecture vous permet de générer une entreprise complète et cohérente en **15-20 minutes** avec des données parfaitement structurées pour votre démo RAG !

