# =============================================================================
# rag/sql_retriever.py - Interface SQL intelligente
# =============================================================================

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
from data_generation.utils.llm_client import generate_text # Assurez-vous que generate_text est importé

class SIRHSQLRetriever:
    def __init__(self, config):
        self.config = config
        self.schema_info = self._get_schema_info()
        self.sql_prompt_template = self._load_sql_prompt()

    def _load_sql_prompt(self) -> str:
        """Charge le prompt de conversion texte vers SQL."""
        # Ce prompt pourrait être dans un fichier "prompts/text_to_sql.txt"
        sql_prompt = ""
        with open('rag_system/prompts/load_sql_prompt.txt', 'r', encoding='utf-8') as f:
            sql_prompt = f.read()
        return sql_prompt

    def get_context(self, question: str) -> List[Dict[str, Any]]:
        """Convertit une question en SQL, l'exécute et retourne le contexte."""
        print(f"Génération de la requête SQL pour : '{question}'")
        
        # 1. Générer la requête SQL avec le LLM
        prompt = self.sql_prompt_template.format(schema=self.schema_info, question=question)
        sql_query = generate_text(prompt).strip()

        if not self._is_safe_query(sql_query):
            print(f"⚠️ Requête SQL générée non sécurisée et rejetée : {sql_query}")
            return [{"content": "La question a été interprétée comme une requête non autorisée.", 'metadata': {'source': 'sql_generator_error'}}]
            
        print(f"  -> Requête SQL générée : {sql_query}")
        
        # 2. Exécuter la requête
        results = self.execute_query(sql_query)
        
        if not results:
            return [{"content": "Aucun résultat trouvé dans la base de données pour cette question.", 'metadata': {'source': 'sql_query_empty'}}]
            
        # 3. Formatter les résultats en contexte
        content = f"Résultat de la requête '{question}':\n" + "\n".join([str(dict(row)) for row in results])
        return [{'content': content, 'metadata': {'source': 'sql_query', 'query': sql_query}}]

    
    def _get_schema_info(self) -> Dict[str, List[str]]:
        """Récupère l'information sur le schéma de la base"""
        if not Path(self.config.sirh_db_path).exists():
            print(f"⚠️ Base de données {self.config.sirh_db_path} n'existe pas")
            return {}
        
        try:
            conn = sqlite3.connect(self.config.sirh_db_path)
            cursor = conn.cursor()
            
            # Récupérer les tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                schema[table] = columns
            
            conn.close()
            print(f"✅ Schéma de base chargé: {len(tables)} tables")
            return schema
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement du schéma: {e}")
            return {}
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Exécute une requête SQL de manière sécurisée"""
        # Validation basique
        if not self._is_safe_query(query):
            print(f"⚠️ Requête non sécurisée rejetée: {query[:100]}...")
            return []
        
        try:
            conn = sqlite3.connect(self.config.sirh_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"❌ Erreur SQL: {e}")
            return []
    
    def _is_safe_query(self, query: str) -> bool:
        """Validation de sécurité des requêtes"""
        query_upper = query.upper().strip()
        
        # Autoriser seulement SELECT
        if not query_upper.startswith('SELECT'):
            return False
        
        # Interdire les mots-clés dangereux
        forbidden = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'EXEC', 'EXECUTE']
        for keyword in forbidden:
            if keyword in query_upper:
                return False
        
        return True
    
    def get_employee_count_by_department(self) -> List[Dict[str, Any]]:
        """Compte les employés par département"""
        query = """
        SELECT ou.name as department, COUNT(e.id) as count
        FROM employee e
        JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        JOIN organizational_unit ou ON a.unit_id = ou.id
        GROUP BY ou.name
        ORDER BY count DESC
        """
        return self.execute_query(query)
    
    def get_top_performers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Récupère les meilleurs performeurs"""
        query = f"""
        SELECT e.first_name, e.last_name, pr.score, p.title, ou.name as department
        FROM performance_review pr
        JOIN employee e ON pr.employee_id = e.id
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        WHERE pr.evaluation_year = (SELECT MAX(evaluation_year) FROM performance_review)
        ORDER BY pr.score DESC
        LIMIT {limit}
        """
        return self.execute_query(query)
    
    def search_employees_by_skill(self, skill_name: str) -> List[Dict[str, Any]]:
        """Recherche d'employés par compétence"""
        query = """
        SELECT e.first_name, e.last_name, es.level, p.title, ou.name as department
        FROM employee e
        JOIN employee_skill es ON e.id = es.employee_id
        JOIN skill s ON es.skill_id = s.id
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        WHERE s.name LIKE ?
        ORDER BY 
            CASE es.level
                WHEN 'Expert' THEN 4
                WHEN 'Advanced' THEN 3
                WHEN 'Intermediate' THEN 2
                WHEN 'Beginner' THEN 1
                ELSE 0
            END DESC
        """
        
        try:
            conn = sqlite3.connect(self.config.sirh_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query, (f'%{skill_name}%',))
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
        except Exception as e:
            print(f"❌ Erreur lors de la recherche par compétence: {e}")
            return []
    
    def get_training_summary(self) -> List[Dict[str, Any]]:
        """Résumé des formations"""
        query = """
        SELECT tp.name, COUNT(tr.id) as completions, 
               AVG(tr.satisfaction_rating) as avg_satisfaction,
               AVG(tr.score) as avg_score
        FROM training_program tp
        LEFT JOIN training_record tr ON tp.id = tr.training_program_id
        GROUP BY tp.id, tp.name
        ORDER BY completions DESC
        """
        return self.execute_query(query)
    
    def get_feedback_summary_by_type(self) -> List[Dict[str, Any]]:
        """Résumé des feedback par type"""
        query = """
        SELECT feedback_type, COUNT(*) as count,
               AVG(LENGTH(content)) as avg_length
        FROM feedback
        GROUP BY feedback_type
        ORDER BY count DESC
        """
        return self.execute_query(query)
    
    def search_employees_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Recherche d'employés par nom"""
        query = """
        SELECT e.first_name, e.last_name, e.email, p.title, ou.name as department
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        WHERE e.first_name LIKE ? OR e.last_name LIKE ?
        ORDER BY e.last_name, e.first_name
        LIMIT 20
        """
        
        try:
            conn = sqlite3.connect(self.config.sirh_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            search_term = f'%{name}%'
            cursor.execute(query, (search_term, search_term))
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
        except Exception as e:
            print(f"❌ Erreur lors de la recherche par nom: {e}")
            return []
    
    def get_hierarchy_info(self) -> Dict[str, Any]:
        """Informations sur la hiérarchie"""
        queries = {
            "total_employees": "SELECT COUNT(*) as count FROM employee",
            "managers_count": "SELECT COUNT(DISTINCT manager_id) as count FROM employee WHERE manager_id IS NOT NULL",
            "ceo_count": "SELECT COUNT(*) as count FROM employee WHERE manager_id IS NULL",
            "departments_count": "SELECT COUNT(*) as count FROM organizational_unit",
            "positions_count": "SELECT COUNT(*) as count FROM position"
        }
        
        result = {}
        for key, query in queries.items():
            data = self.execute_query(query)
            result[key] = data[0]['count'] if data else 0
        
        return result
    
    def get_performance_distribution(self) -> List[Dict[str, Any]]:
        """Distribution des scores de performance"""
        query = """
        SELECT score, COUNT(*) as count
        FROM performance_review
        WHERE evaluation_year = (SELECT MAX(evaluation_year) FROM performance_review)
        GROUP BY score
        ORDER BY score
        """
        return self.execute_query(query)
    
    def get_skills_by_category(self) -> List[Dict[str, Any]]:
        """Compétences regroupées par catégorie"""
        query = """
        SELECT category, COUNT(*) as skill_count,
               COUNT(DISTINCT es.employee_id) as employees_with_skills
        FROM skill s
        LEFT JOIN employee_skill es ON s.id = es.skill_id
        GROUP BY category
        ORDER BY skill_count DESC
        """
        return self.execute_query(query)