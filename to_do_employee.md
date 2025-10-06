Absolument. Voici une proposition complète pour intégrer le profil employé à 5 dimensions dans votre projet.

J'ai structuré cela comme vous l'avez demandé : modifications du schéma de BDD, nouveaux prompts, scripts Python, et un fichier récapitulatif `to_do_employee.md`.

-----

## 📝 to_do_employee.md

Voici le plan d'action détaillé pour implémenter cette nouvelle fonctionnalité.

### 1. Mettre à jour le Schéma de la Base de Données

  - **Fichier à modifier** : `schema.sql`
  - **Action** : Ajouter une nouvelle table `employee_profile` pour stocker les 5 dimensions de performance intrinsèques de chaque employé. Cette table sera liée à la table `employee` par une clé étrangère.

### 2. Créer les Nouveaux Prompts Déclaratifs

  - **Nouveau fichier** : `prompts/02b_employee_profile_generation.txt`
      - **Objectif** : Générer le profil de performance intrinsèque d'un employé selon les 5 dimensions, en respectant la distribution de performance souhaitée (super/moyen/sous-performant).
  - **Nouveau fichier** : `prompts/04_performance_review_v2.txt`
      - **Objectif** : Générer une évaluation de performance annuelle **structurée et détaillée**. Ce prompt utilisera le profil de l'employé (ex: "high_performer") comme contexte pour générer des commentaires cohérents, des axes d'amélioration pertinents et un score aligné.

### 3. Développer le Script de Génération des Profils

  - **Nouveau fichier** : `src/e02b_employee_profiles.py`
  - **Actions** :
    1.  Lire tous les employés de la base de données.
    2.  Définir la distribution des profils (ex: 10% "high_performer", 80% "average_performer", 10% "struggling_performer").
    3.  Pour chaque employé, assigner un profil de performance.
    4.  Utiliser le prompt `02b_employee_profile_generation.txt` pour générer les scores des 5 dimensions.
    5.  Insérer ces profils dans la nouvelle table `employee_profile`.

### 4. Adapter le Script des Évaluations de Performance

  - **Fichier à modifier** : `src/e04_objectifs_performance.py`
  - **Actions** :
    1.  Au début du script, charger les profils de performance depuis la table `employee_profile`.
    2.  Lors de la génération de l'évaluation pour un employé, passer son profil de performance (`performance_profile` et `score_range`) au nouveau prompt `04_performance_review_v2.txt`.
    3.  Remplacer la génération de l'ancien `comments` textuel par le nouveau `structured_review_json`.
    4.  Modifier la table `performance_review` pour stocker ce JSON structuré.

### 5. Mettre à jour le `main.py`

  - **Fichier à modifier** : `main.py`
  - **Action** : Insérer l'appel au nouveau script `e02b_employee_profiles.py` dans la séquence d'exécution, juste après la création des employés.

-----

## perubahan skema BDD

### `schema.sql`

Ajoutez la nouvelle table `employee_profile` à la fin de votre fichier `schema.sql`. La table `performance_review` est aussi modifiée pour stocker le JSON de l'évaluation structurée.

```sql
-- ... (autres tables)

CREATE TABLE IF NOT EXISTS employee_profile (
    employee_id INTEGER PRIMARY KEY,
    performance_profile TEXT NOT NULL, -- "high_performer", "average_performer", "struggling_performer"
    technical_performance INTEGER NOT NULL,
    contextual_performance INTEGER NOT NULL,
    adaptive_performance INTEGER NOT NULL,
    behavioral_stability INTEGER NOT NULL,
    professional_integrity INTEGER NOT NULL,
    score_range_min INTEGER NOT NULL,
    score_range_max INTEGER NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(id)
);

-- Modifier la table performance_review pour stocker l'évaluation structurée
-- (Supprimez l'ancienne définition de performance_review si elle existe)
DROP TABLE IF EXISTS performance_review;
CREATE TABLE IF NOT EXISTS performance_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    evaluation_year INTEGER NOT NULL,
    overall_score INTEGER NOT NULL,
    structured_review_json TEXT, -- Stocke le JSON complet de l'évaluation
    FOREIGN KEY (employee_id) REFERENCES employee(id),
    FOREIGN KEY (reviewer_id) REFERENCES employee(id)
);


-- ... (index existants)
```

-----

## 🐍 Scripts Python

### `src/e02b_employee_profiles.py` (Nouveau)

Ce script crée les profils de performance pour chaque employé.

```python
# src/e02b_employee_profiles.py
import random
from utils.database import get_connection
from utils.llm_client import generate_json, LLMError
from config import get_config

def run():
    """
    Étape 2b: Génération des profils de performance intrinsèques des employés.
    """
    print("Étape 2b: Génération des profils de performance")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, first_name, last_name FROM employee")
    employees = cursor.fetchall()
    
    if not employees:
        print("Aucun employé trouvé.")
        return

    # Définir la distribution des profils
    total_employees = len(employees)
    high_performers_count = int(total_employees * 0.10)
    struggling_performers_count = int(total_employees * 0.10)
    average_performers_count = total_employees - high_performers_count - struggling_performers_count
    
    profiles = (["high_performer"] * high_performers_count +
                ["struggling_performer"] * struggling_performers_count +
                ["average_performer"] * average_performers_count)
    random.shuffle(profiles)

    with open('prompts/02b_employee_profile_generation.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    for i, employee in enumerate(employees):
        profile_type = profiles[i]
        
        prompt = prompt_template.format(
            employee_name=f"{employee['first_name']} {employee['last_name']}",
            performance_profile=profile_type
        )
        
        try:
            profile_data = generate_json(prompt)
            
            cursor.execute("""
                INSERT INTO employee_profile (
                    employee_id, performance_profile, 
                    technical_performance, contextual_performance, adaptive_performance, 
                    behavioral_stability, professional_integrity, 
                    score_range_min, score_range_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee['id'], profile_type,
                profile_data['technical_performance'],
                profile_data['contextual_performance'],
                profile_data['adaptive_performance'],
                profile_data['behavioral_stability'],
                profile_data['professional_integrity'],
                profile_data['score_range_min'],
                profile_data['score_range_max']
            ))
            print(f"✓ Profil créé pour {employee['first_name']} {employee['last_name']}: {profile_type}")

        except LLMError as e:
            print(f"⚠ Échec de la génération du profil pour {employee['first_name']} {employee['last_name']}: {e}")
            continue

    conn.commit()
    conn.close()
    print("✓ Profils de performance générés pour tous les employés.")
```

### `src/e04_objectifs_performance.py` (Modifications)

Ce fichier doit être mis à jour pour utiliser les profils générés.

```python
# src/e04_objectifs_performance.py (extraits des modifications)
import json # Assurez-vous d'importer json

# ... (début du fichier)

def run():
    """
    Étape 4: Génération des objectifs et évaluations de performance structurées.
    """
    print("Étape 4: Génération des objectifs et évaluations de performance")
    
    config = get_config()
    company_profile = config['entreprise']
    current_year = datetime.now().year
    
    conn = get_connection()
    cursor = conn.cursor()

    # Charger les profils de performance
    cursor.execute("SELECT * FROM employee_profile")
    profiles = {row['employee_id']: dict(row) for row in cursor.fetchall()}

    # ... (récupération des employés comme avant)

    # Lire les nouveaux prompts
    with open('prompts/04_goals_generation.txt', 'r', encoding='utf-8') as f:
        goals_prompt_template = f.read()
    
    with open('prompts/04_performance_review_v2.txt', 'r', encoding='utf-8') as f:
        review_prompt_template = f.read()
        
    # ... (boucle sur les employés et les années)
    
            # ... (génération des objectifs, inchangée)

            # Générer l'évaluation de performance structurée
            employee_profile = profiles.get(employee['id'])
            if not employee_profile:
                print(f"    ⚠ Profil manquant pour {employee_name}, évaluation ignorée.")
                continue

            review_prompt = review_prompt_template.format(
                employee_name=employee_name,
                position=employee['position_title'] or "Employee",
                unit=employee['unit_name'] or "Unknown",
                year=eval_year,
                culture=company_profile['culture'],
                language=company_profile['language'],
                sector=company_profile['secteur'],
                location=company_profile['location'],
                region_culture=company_profile['region_culture'],
                performance_profile=employee_profile['performance_profile'],
                score_range=f"{employee_profile['score_range_min']}-{employee_profile['score_range_max']}"
            )
            
            try:
                review_data = generate_json(review_prompt)
                
                reviewer_id = employee['manager_id'] or 1
                
                cursor.execute("""
                    INSERT INTO performance_review (employee_id, reviewer_id, evaluation_year, overall_score, structured_review_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee['id'], reviewer_id, eval_year, 
                      review_data['overall_score'], json.dumps(review_data)))
                reviews_created += 1
                
            except LLMError as e:
                print(f"    ⚠ Échec évaluation pour {employee_name} ({eval_year}): {e}")

    # ... (fin du fichier)
```

-----

## 🤖 Prompts

### `prompts/02b_employee_profile_generation.txt` (Nouveau)

````
You are an HR data scientist creating an intrinsic performance profile for an employee.

Generate a 5-dimensional performance profile for:
- Employee: {employee_name}
- Performance Profile: {performance_profile}

The profile consists of 5 dimensions, each scored from 1 to 100.
The distribution of profiles is:
- "high_performer": Scores consistently between 80-100.
- "average_performer": Scores consistently between 40-79.
- "struggling_performer": Scores consistently between 10-39.

Based on the `{performance_profile}`, generate scores for the 5 dimensions and define a realistic score range (1-5) for their annual reviews.

**Output Format (JSON only):**
```json
{{
  "technical_performance": [Score 1-100],
  "contextual_performance": [Score 1-100],
  "adaptive_performance": [Score 1-100],
  "behavioral_stability": [Score 1-100],
  "professional_integrity": [Score 1-100],
  "score_range_min": [Min score 1-5],
  "score_range_max": [Max score 1-5]
}}
````

Output only valid JSON.

```

### `prompts/04_performance_review_v2.txt` (Nouveau)

```

You are an HR manager writing a structured, fair, and detailed performance review.

Generate a comprehensive review for:

  - Employee: {employee_name}
  - Position: {position}
  - Unit: {unit}
  - Evaluation Year: {year}
  - Culture: {culture}
  - Sector: {sector}
  - Location: {location}
  - Regional culture: {region_culture}

**IMPORTANT EMPLOYEE CONTEXT:**

  - Performance Profile: **{performance_profile}**
  - Expected Score Range (1-5): **{score_range}**

**INSTRUCTIONS:**

  - The overall score must be consistent with the employee's profile and fall within the `{score_range}`.
  - For a "struggling_performer", focus on identifying specific skill gaps and suggesting clear support actions (training, mentoring).
  - For a "high_performer", highlight their positive impact on the team and suggest challenges for their continued growth.
  - For an "average_performer", provide a balanced view of achievements and areas for improvement.
  - All comments, evidence, and recommendations must be concrete, constructive, and avoid generic statements.
  - The language must be professional and adapted to the company culture.
  - The entire output must be a single, valid JSON object.

**OUTPUT JSON STRUCTURE:**
{{
"overall_score": "[Global score from 1-5, consistent with the profile]",
"context_analysis": {{
"work_environment": "Analysis of the work context for the year {year}",
"key_challenges": "Main challenges encountered by the employee",
"support_received": "Support and resources available to the employee"
}},
"dimensional_assessment": {{
"technical": {{
"score": "[Score 1-5]",
"evidence": "Concrete examples of technical performance (successes or difficulties)",
"evolution": "Evolution compared to the previous year (e.g., 'Improved', 'Stable', 'Needs attention')"
}},
"contextual": {{
"score": "[Score 1-5]",
"evidence": "Examples of collaboration, teamwork, and initiative",
"evolution": "Progress in pro-social and supportive behaviors"
}},
"adaptive": {{
"score": "[Score 1-5]",
"evidence": "How the employee handled changes, new tasks, or learning opportunities",
"evolution": "Development of flexibility and resilience"
}},
"stability": {{
"score": "[Score 1-5]",
"evidence": "Consistency in performance, stress management, reliability",
"evolution": "Behavioral reliability and emotional regulation"
}},
"integrity": {{
"score": "[Score 1-5]",
"evidence": "Adherence to company values, ethics, and transparency",
"evolution": "Ethical development and trustworthiness"
}}
}},
"achievements": {{
"major_accomplishments": ["3-4 key achievements of the year {year}"],
"exceeded_expectations": ["Areas where the employee went above and beyond"],
"learning_highlights": ["New skills or knowledge acquired during the year"]
}},
"areas_for_improvement": {{
"immediate_priorities": ["2-3 priority areas for development"],
"skill_gaps": ["Specific skills to develop (technical or soft)"],
"behavioral_adjustments": ["Behavioral adjustments to consider"]
}},
"recommendations": {{
"training_needs": ["Recommended training programs"],
"mentoring_support": "Suggested mentoring or coaching",
"career_development": "Potential next steps and career progression",
"performance_monitoring": "How performance will be tracked going forward"
}},
"development_plan": {{
"short_term_goals": ["SMART goals for the next 3-6 months"],
"medium_term_objectives": ["Objectives for the next performance cycle"],
"success_metrics": ["How success for these goals will be measured"],
"support_resources": ["Resources needed to achieve these goals"]
}},
"manager_comments": "A synthetic summary from the manager (100-150 words), concluding the review."
}}

Output only valid JSON.

```
```