# =============================================================================
# rag/document_loader.py - Chargement des documents
# =============================================================================

import sqlite3
from pathlib import Path
from typing import List, Dict, Any

class Document:
    """Classe simple pour représenter un document"""
    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

class RecursiveCharacterTextSplitter:
    """Diviseur de texte simple"""
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "! ", "? ", " "]
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Divise les documents en chunks"""
        result = []
        for doc in documents:
            chunks = self._split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                new_doc = Document(
                    page_content=chunk,
                    metadata={**doc.metadata, "chunk_index": i}
                )
                result.append(new_doc)
        return result
    
    def _split_text(self, text: str) -> List[str]:
        """Divise un texte en chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Chercher un bon point de coupure
            best_split = end
            for separator in self.separators:
                pos = text.rfind(separator, start, end)
                if pos > start:
                    best_split = pos + len(separator)
                    break
            
            chunks.append(text[start:best_split])
            start = best_split - self.chunk_overlap
            start = max(start, best_split)
        
        return [chunk.strip() for chunk in chunks if chunk.strip()]

class SIRHDocumentLoader:
    """Chargeur de documents pour le système SIRH"""
    
    def __init__(self, config):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", " "]
        )
    
    def load_all_documents(self) -> List[Document]:
        """Charge tous les documents du système SIRH"""
        documents = []
        
        # 1. Documents physiques générés
        print("Chargement des documents physiques...")
        file_docs = self._load_file_documents()
        documents.extend(file_docs)
        print(f"✅ {len(file_docs)} documents physiques chargés")
        
        # 2. Données extraites de la base
        print("Extraction des données de la base...")
        db_docs = self._load_database_documents()
        documents.extend(db_docs)
        print(f"✅ {len(db_docs)} documents de base générés")
        
        return documents
    
    def _load_file_documents(self) -> List[Document]:
        """Charge les documents physiques"""
        documents = []
        docs_path = Path(self.config.documents_path)
        
        if not docs_path.exists():
            print(f"⚠️ Répertoire {docs_path} n'existe pas")
            return documents
        
        for file_path in docs_path.glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    continue
                
                # Extraire les métadonnées du nom de fichier
                # Format: emp_X_TYPE.txt
                parts = file_path.stem.split('_')
                if len(parts) >= 3:
                    employee_id = parts[1]
                    doc_type = '_'.join(parts[2:])
                else:
                    employee_id = "unknown"
                    doc_type = "unknown"
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": f"file_{file_path.name}",
                        "type": doc_type,
                        "employee_id": employee_id,
                        "file_path": str(file_path)
                    }
                )
                
                # Diviser en chunks
                chunks = self.text_splitter.split_documents([doc])
                documents.extend(chunks)
                
            except Exception as e:
                print(f"❌ Erreur lors du chargement de {file_path}: {e}")
        
        return documents
    
    def _load_database_documents(self) -> List[Document]:
        """Extrait et structure les données de la base SQLite"""
        if not Path(self.config.sirh_db_path).exists():
            print(f"⚠️ Base de données {self.config.sirh_db_path} n'existe pas")
            return []
        
        documents = []
        conn = sqlite3.connect(self.config.sirh_db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Profils d'employés
            documents.extend(self._extract_employee_profiles(conn))
            
            # Évaluations de performance
            documents.extend(self._extract_performance_reviews(conn))
            
            # Feedback
            documents.extend(self._extract_feedback(conn))
            
            # Formations
            documents.extend(self._extract_training_records(conn))
            
            # Compétences
            documents.extend(self._extract_skills_summary(conn))
            
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction de la base: {e}")
        finally:
            conn.close()
        
        return documents
    
    def _extract_employee_profiles(self, conn) -> List[Document]:
        """Crée des profils d'employés textuels"""
        query = """
        SELECT e.id, e.first_name, e.last_name, e.email, e.hire_date,
               p.title as position, ou.name as unit,
               m.first_name as manager_first_name, m.last_name as manager_last_name
        FROM employee e
        LEFT JOIN assignment a ON e.id = a.employee_id AND a.end_date IS NULL
        LEFT JOIN position p ON a.position_id = p.id
        LEFT JOIN organizational_unit ou ON a.unit_id = ou.id
        LEFT JOIN employee m ON e.manager_id = m.id
        """
        
        documents = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            content = f"""Profil employé: {row['first_name']} {row['last_name']}
Email: {row['email']}
Poste: {row['position'] or 'Non défini'}
Département: {row['unit'] or 'Non défini'}
Date d'embauche: {row['hire_date']}"""
            
            if row['manager_first_name']:
                content += f"\nManager: {row['manager_first_name']} {row['manager_last_name']}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "database_employee",
                    "type": "employee_profile",
                    "employee_id": str(row['id']),
                    "employee_name": f"{row['first_name']} {row['last_name']}"
                }
            )
            documents.append(doc)
        
        return documents
    
    def _extract_performance_reviews(self, conn) -> List[Document]:
        """Extrait les évaluations de performance"""
        query = """
        SELECT pr.*, e.first_name, e.last_name,
               r.first_name as reviewer_first_name, r.last_name as reviewer_last_name
        FROM performance_review pr
        JOIN employee e ON pr.employee_id = e.id
        JOIN employee r ON pr.reviewer_id = r.id
        """
        
        documents = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            content = f"""Évaluation de performance - {row['first_name']} {row['last_name']}
Année: {row['evaluation_year']}
Score: {row['score']}/5
Évaluateur: {row['reviewer_first_name']} {row['reviewer_last_name']}

Commentaires:
{row['comments'] or 'Aucun commentaire'}"""
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "database_performance",
                    "type": "performance_review",
                    "employee_id": str(row['employee_id']),
                    "employee_name": f"{row['first_name']} {row['last_name']}",
                    "score": row['score'],
                    "year": row['evaluation_year']
                }
            )
            documents.append(doc)
        
        return documents
    
    def _extract_feedback(self, conn) -> List[Document]:
        """Extrait les feedback"""
        query = """
        SELECT f.*, e.first_name, e.last_name,
               giver.first_name as giver_first_name, giver.last_name as giver_last_name
        FROM feedback f
        JOIN employee e ON f.to_employee_id = e.id
        JOIN employee giver ON f.from_employee_id = giver.id
        """
        
        documents = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            content = f"""Feedback pour {row['first_name']} {row['last_name']}
Type: {row['feedback_type']}
Contexte: {row['context']}
Date: {row['feedback_date']}
De: {row['giver_first_name']} {row['giver_last_name']}
Anonyme: {'Oui' if row['is_anonymous'] else 'Non'}

Contenu:
{row['content']}"""
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "database_feedback",
                    "type": "feedback",
                    "employee_id": str(row['to_employee_id']),
                    "employee_name": f"{row['first_name']} {row['last_name']}",
                    "feedback_type": row['feedback_type']
                }
            )
            documents.append(doc)
        
        return documents
    
    def _extract_training_records(self, conn) -> List[Document]:
        """Extrait les formations"""
        query = """
        SELECT tr.*, e.first_name, e.last_name, tp.name as training_name,
               tp.description, tp.duration_hours
        FROM training_record tr
        JOIN employee e ON tr.employee_id = e.id
        JOIN training_program tp ON tr.training_program_id = tp.id
        """
        
        documents = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            content = f"""Formation suivie par {row['first_name']} {row['last_name']}
Formation: {row['training_name']}
Description: {row['description']}
Durée: {row['duration_hours']} heures
Date de completion: {row['completion_date']}
Score: {row['score'] or 'Non noté'}
Satisfaction: {row['satisfaction_rating']}/5

Commentaires: {row['comments'] or 'Aucun commentaire'}"""
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "database_training",
                    "type": "training_record",
                    "employee_id": str(row['employee_id']),
                    "employee_name": f"{row['first_name']} {row['last_name']}",
                    "training_name": row['training_name']
                }
            )
            documents.append(doc)
        
        return documents
    
    def _extract_skills_summary(self, conn) -> List[Document]:
        """Extrait un résumé des compétences par employé"""
        query = """
        SELECT e.id, e.first_name, e.last_name,
               GROUP_CONCAT(s.name || ' (' || es.level || ')') as skills
        FROM employee e
        JOIN employee_skill es ON e.id = es.employee_id
        JOIN skill s ON es.skill_id = s.id
        GROUP BY e.id, e.first_name, e.last_name
        """
        
        documents = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            if row['skills']:
                content = f"""Compétences de {row['first_name']} {row['last_name']}

Compétences:
{row['skills'].replace(',', chr(10))}"""
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": "database_skills",
                        "type": "skills_summary",
                        "employee_id": str(row['id']),
                        "employee_name": f"{row['first_name']} {row['last_name']}"
                    }
                )
                documents.append(doc)
        
        return documents