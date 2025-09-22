# Instruction (à coller dans ChatGPT)

Tu es chargé de générer une application minimaliste de gestion de données en **FastAPI + SQLAlchemy + Jinja2**, basée sur le paradigme suivant :

**2. Paradigme CRUD généré à partir du schéma relationnel**

* Mapping direct **tables ↔ écrans**.
* **Vue “liste”** = tabulaire multi-enregistrements (sélection + tri + pagination + recherche simple).
* **Vue “fiche”** = détaillée d’un enregistrement (affichage + création + édition + suppression).
* Implémentation conforme au modèle **Entité-Relation (E-R)** : chaque **entité (table)** dispose de deux représentations :

  1. **vue agrégée (liste)**, 2) **vue individuelle (fiche)**.

## Hypothèses et variables à paramétrer

* Base de données : `{{DB_URL}}` (ex. `sqlite:///./app.db` ou `postgresql+psycopg://user:pwd@host/db`).
* Tables ciblées : `{{TABLES}}` (ex. `["employee", "department"]`).
* Clé primaire standard `id` (entier, auto-incrément).
* Champs texte/date/nombre booléen classiques.
* Contrainte : code **sobre, lisible, structuré**, sans dépendances exotiques.

## Livrables attendus

1. **Arborescence de projet** :

```
.
├─ app/
│  ├─ main.py                 # point d’entrée FastAPI + routes
│  ├─ db.py                   # session, Base, moteur
│  ├─ models.py               # SQLAlchemy (tables ciblées)
│  ├─ schemas.py              # Pydantic (Create/Update/Read)
│  ├─ crud.py                 # opérations CRUD par modèle
│  ├─ deps.py                 # dépendances (session, pagination…)
│  ├─ templates/
│  │  ├─ base.html
│  │  ├─ {{table}}_list.html  # vue “liste”
│  │  └─ {{table}}_detail.html# vue “fiche”
│  └─ static/
│     └─ style.css            # style minimal
└─ requirements.txt
```

2. **Fonctionnalités obligatoires (pour chaque table de `{{TABLES}}`)**

* **Liste** (`GET /{{table}}`) :

  * tableau des enregistrements (colonnes principales),
  * **tri** sur au moins une colonne,
  * **pagination** (page, page\_size),
  * **recherche** plein-texte simple sur 1–2 champs,
  * lien “nouveau”, lien vers chaque **fiche**.
* **Fiche**

  * **Affichage** (`GET /{{table}}/{id}`)
  * **Création** (`GET /{{table}}/new`, `POST /{{table}}`) avec formulaire HTML, validation Pydantic côté serveur
  * **Édition** (`GET /{{table}}/{id}/edit`, `POST /{{table}}/{id}`)
  * **Suppression** (`POST /{{table}}/{id}/delete`) avec confirmation.
* **Gestion d’erreurs** : 404 si id inexistant, messages d’erreur simples dans les templates.
* **Sécurité minimale** :

  * protection CSRF **non requise** (démo),
  * mais vérification basique des entrées via Pydantic.
* **Performances minimales** : requêtes paginées, `selectinload` pour relations simples s’il y en a.

3. **Détails d’implémentation**

* **FastAPI** pour les routes et la validation.
* **SQLAlchemy ORM** (2.x) pour les modèles et requêtes.
* **Jinja2** pour le rendu des pages HTML.
* **Uvicorn** pour l’exécution locale.
* **requirements.txt** minimal (fastapi, uvicorn, sqlalchemy, jinja2, pydantic, python-multipart).
* **Style** : un `style.css` simple (table lisible, formulaires propres).

4. **Modèles d’exemple (si `{{TABLES}}` n’est pas fourni)**

* `department(id, name)`
* `employee(id, first_name, last_name, email, hire_date, is_active, department_id -> department.id)`
  Inclure la relation One-to-Many (department → employees) et afficher le nom du département dans la **liste** et la **fiche** employee.

5. **Code prêt à exécuter**

* Fournir l’intégralité des fichiers listés, avec commentaires concis.
* Inclure un bloc **“Comment lancer”** :

  * création/migration simple (si SQLite, création auto via `Base.metadata.create_all(engine)`),
  * commande `uvicorn app.main:app --reload`,
  * URL à tester (ex. `/employee`, `/department`).
* Générer **de la donnée d’exemple** (semences) si SQLite pour démonstration.

6. **Qualité**

* Respect de la séparation **models / schemas / crud / routes / templates**.
* Noms de routes et de templates **cohérents**.
* Messages d’erreurs et validations **explicites**.
* **Aucun code mort**.
* Commentaires brefs expliquant les points clés (pagination, tri, recherche, formulaires).

7. **Extension optionnelle (si temps)**

* **Export CSV** depuis la vue liste.
* **Filtrage** par champ (ex. département, actif/inactif).
* **Tri multi-colonnes** basique via query params.

Rends la réponse sous forme de **blocs de code par fichier**, suivis d’une section “Comment lancer”. Utilise des **chemins relatifs** cohérents avec l’arborescence proposée.

---

Remplace `{{DB_URL}}` et `{{TABLES}}` par mes valeurs si je les fournis ; sinon, pars sur l’exemple SQLite + tables `department` et `employee`.
