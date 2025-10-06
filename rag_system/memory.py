# =============================================================================
# rag/memory.py - Système de mémoire conversationnelle
# =============================================================================

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

class ConversationMemory:
    """Gestionnaire de mémoire conversationnelle pour le RAG"""
    
    def __init__(self, memory_db_path: str = "data/conversation_memory.db"):
        self.memory_db_path = memory_db_path
        self.max_history_length = 10  # Nombre max de messages dans le contexte
        self.memory_retention_days = 30  # Garder les conversations 30 jours
        
        # Créer le répertoire si nécessaire
        Path(memory_db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialiser la base de données
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données de mémoire"""
        conn = sqlite3.connect(self.memory_db_path)
        cursor = conn.cursor()
        
        # Table des sessions de conversation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT  -- JSON pour stocker des infos additionnelles
            )
        """)
        
        # Table des messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- 'user' ou 'assistant'
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON pour query_type, sources, etc.
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
            )
        """)
        
        # Index pour les performances
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp 
            ON conversation_messages (session_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, metadata: Dict[str, Any] = None) -> str:
        """Crée une nouvelle session de conversation"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.memory_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_sessions (session_id, metadata)
            VALUES (?, ?)
        """, (session_id, json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Nouvelle session créée: {session_id}")
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Ajoute un message à la conversation"""
        conn = sqlite3.connect(self.memory_db_path)
        cursor = conn.cursor()
        
        # Vérifier que la session existe
        cursor.execute("SELECT 1 FROM conversation_sessions WHERE session_id = ?", (session_id,))
        if not cursor.fetchone():
            # Créer la session si elle n'existe pas
            cursor.execute("""
                INSERT INTO conversation_sessions (session_id, metadata)
                VALUES (?, ?)
            """, (session_id, "{}"))
        
        # Ajouter le message
        cursor.execute("""
            INSERT INTO conversation_messages (session_id, role, content, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, json.dumps(metadata or {})))
        
        # Mettre à jour l'activité de la session
        cursor.execute("""
            UPDATE conversation_sessions 
            SET last_activity = CURRENT_TIMESTAMP 
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Récupère l'historique d'une conversation"""
        if limit is None:
            limit = self.max_history_length
        
        conn = sqlite3.connect(self.memory_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, metadata, timestamp
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            message = {
                'role': row['role'],
                'content': row['content'],
                'timestamp': row['timestamp']
            }
            
            # Décoder les métadonnées JSON
            if row['metadata']:
                try:
                    message['metadata'] = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    message['metadata'] = {}
            
            messages.append(message)
        
        conn.close()
        
        # Retourner dans l'ordre chronologique
        return list(reversed(messages))
    
    def get_context_for_query(self, session_id: str, current_question: str) -> str:
        """Génère un contexte conversationnel pour la requête actuelle"""
        history = self.get_conversation_history(session_id, limit=6)  # 3 derniers échanges
        
        if not history:
            return ""
        
        context_parts = ["=== CONTEXTE CONVERSATIONNEL ==="]
        
        for message in history:
            role_label = "👤 Utilisateur" if message['role'] == 'user' else "🤖 Assistant"
            context_parts.append(f"{role_label}: {message['content'][:200]}...")
        
        context_parts.append("=== QUESTION ACTUELLE ===")
        context_parts.append(f"👤 Utilisateur: {current_question}")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def cleanup_old_conversations(self):
        """Nettoie les anciennes conversations"""
        cutoff_date = datetime.now() - timedelta(days=self.memory_retention_days)
        
        conn = sqlite3.connect(self.memory_db_path)
        cursor = conn.cursor()
        
        # Supprimer les anciens messages
        cursor.execute("""
            DELETE FROM conversation_messages 
            WHERE session_id IN (
                SELECT session_id FROM conversation_sessions 
                WHERE last_activity < ?
            )
        """, (cutoff_date,))
        
        # Supprimer les anciennes sessions
        cursor.execute("""
            DELETE FROM conversation_sessions 
            WHERE last_activity < ?
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"🧹 {deleted_count} anciennes conversations supprimées")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Récupère les statistiques d'une session"""
        conn = sqlite3.connect(self.memory_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as message_count,
                MIN(timestamp) as first_message,
                MAX(timestamp) as last_message
            FROM conversation_messages
            WHERE session_id = ?
        """, (session_id,))
        
        stats = dict(cursor.fetchone() or {})
        conn.close()
        
        return stats
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche dans l'historique des conversations"""
        conn = sqlite3.connect(self.memory_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT session_id, content, timestamp, role
            FROM conversation_messages
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Statistiques générales de la mémoire"""
        conn = sqlite3.connect(self.memory_db_path)
        cursor = conn.cursor()
        
        # Nombre total de sessions
        cursor.execute("SELECT COUNT(*) FROM conversation_sessions")
        total_sessions = cursor.fetchone()[0]
        
        # Nombre total de messages
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        total_messages = cursor.fetchone()[0]
        
        # Sessions actives (dernières 24h)
        cursor.execute("""
            SELECT COUNT(*) FROM conversation_sessions 
            WHERE last_activity > datetime('now', '-1 day')
        """)
        active_sessions = cursor.fetchone()[0]
        
        # Taille du fichier DB
        db_size = Path(self.memory_db_path).stat().st_size if Path(self.memory_db_path).exists() else 0
        
        conn.close()
        
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'active_sessions_24h': active_sessions,
            'db_size_bytes': db_size,
            'retention_days': self.memory_retention_days
        }