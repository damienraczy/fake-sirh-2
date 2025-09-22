# Guide d'Utilisation et de Sécurité - SIRH Augmenté

Ce document décrit le fonctionnement du système de "RAG" (Retrieval Augmented Generation)
de ce projet, ses principes de décision et les mesures de sécurité mises en place pour
garantir une utilisation fiable et sécurisée.

---

## 1. Architecture du Système

Notre système est un **RAG multi-sources avancé**. Il ne se contente pas de chercher dans
des documents, il interroge plusieurs types de bases de données pour fournir la réponse la
plus précise possible.

Les trois sources de données principales sont :
1.  **Base de Données Relationnelle (SQL)** : Contient les données structurées (employés,
départements, postes). Idéale pour les comptages et les listes.
2.  **Base de Données Graphe (Neo4j)** : Modélise les relations et la hiérarchie au sein
de l'entreprise. Parfaite pour comprendre "qui manage qui" ou la structure des équipes.
3.  **Base de Données Vectorielle (ChromaDB)** : Contient les informations textuelles non
structurées (CV, évaluations de performance, certifications). Optimale pour la recherche
sémantique et les questions ouvertes.

---

## 2. Le Cerveau : Le Routeur Sémantique

Le cœur de notre système est un **routeur sémantique intelligent**. Son rôle n'est pas de
répondre à la question, mais de comprendre l'**intention** de l'utilisateur pour choisir
l'expert (la source de données) le plus qualifié.

### Comment fonctionne-t-il ?
1.  **Analyse de l'Intention** : Lorsqu'une question est posée, le routeur la compare à
une série d'exemples prédéfinis (`rag/router_config.yaml`).
2.  **Prise de Décision** :
    * Si la question ressemble fortement à une demande de comptage ou de liste (ex:
"Combien...", "Liste tous les..."), elle est dirigée vers la source **SQL**.
    * Si elle concerne la hiérarchie ou les relations (ex: "Qui est le manager de..."),
elle est envoyée vers la source **GRAPH**.
    * Pour toutes les autres questions, notamment les questions ouvertes (ex: "Fais-moi un
résumé de..."), la source **VECTOR** est utilisée par défaut.
3.  **Robustesse** : Si un expert spécialisé (`SQL` ou `GRAPH`) échoue ou ne trouve aucune
information, le système bascule automatiquement sur la recherche `VECTOR` comme filet de
sécurité.

---

## 3. Mesures de Sécurité et Confidentialité

La sécurité et la confidentialité des données RH sont notre priorité absolue. Plusieurs
mécanismes sont en place pour les garantir.

### a. Isolation des Données
Le système fonctionne en circuit fermé. Le Large Language Model (LLM) **n'a pas accès à
Internet**. Il ne peut formuler des réponses qu'en se basant **uniquement** sur les
informations que les *retrievers* lui fournissent à partir des bases de données internes
du projet.

### b. Prévention des Injections SQL
Toutes les requêtes SQL générées par le LLM sont validées avant exécution. La méthode
`_is_safe_query` dans le `SQLRetriever` (`rag/sql_retriever.py`) assure que **seules les
requêtes de lecture (`SELECT`) sont autorisées**. Toute tentative d'écriture, de
modification ou de suppression de données (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.) est
systématiquement bloquée.

### c. Prévention des Modifications du Graphe
De la même manière, le prompt de génération des requêtes Cypher
(`rag/prompts/load_cypher_prompt.txt`) instruit explicitement le LLM de n'utiliser que des
commandes de lecture (`MATCH`). De plus, une vérification dans le code du `GraphRetriever`
(`rag/graph_retriever.py`) bloque toute requête contenant des mots-clés de modification
(`CREATE`, `MERGE`, `DELETE`).

### d. Pas de Persistance des Données Sensibles
La mémoire conversationnelle ne stocke que l'historique des échanges pour une session
donnée. Aucune donnée personnelle issue des bases de données n'est stockée de manière
persistante en dehors des sources de données contrôlées.

---

## 4. Limites Connues

* **Précision des Prompts** : La qualité des requêtes générées (SQL et Cypher) dépend de
la clarté des prompts. Une amélioration continue de ces derniers est nécessaire pour
couvrir tous les cas de figure.
* **Ambiguïté du Langage** : Pour des questions très ambiguës, le routeur sémantique
pourrait choisir une route sous-optimale. Dans ce cas, la logique de *fallback* vers la
recherche vectorielle permet souvent de fournir tout de même une réponse pertinente.