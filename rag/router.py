# rag/router.py
import yaml
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

class SemanticRouter:
    def __init__(self, config_path: str):
        """
        Initialise le routeur en chargeant la configuration et en pré-calculant
        les embeddings des règles.
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.model = SentenceTransformer(config['embedding_model'])
        self.rules = config['rules']
        self.threshold = config['similarity_threshold']
        self.default_route = config['default_route']

        print("Pré-calcul des embeddings pour les règles du routeur...")
        # Chaque règle est représentée par la moyenne des embeddings de ses exemples
        for rule in self.rules:
            example_embeddings = self.model.encode(rule['intent_examples'])
            rule['embedding'] = example_embeddings.mean(axis=0)
        print("✓ Routeur sémantique initialisé.")

    def route(self, question: str) -> str:
        """
        Détermine la meilleure route pour une question donnée.
        """
        question_embedding = self.model.encode([question])[0]

        best_score = -1
        best_route = self.default_route

        for rule in self.rules:
            score = cosine_similarity([question_embedding], [rule['embedding']])[0][0]
            
            if score > best_score:
                best_score = score
                if score > self.threshold:
                    best_route = rule['destination']

        print(f"Question: '{question}' -> Route: {best_route} (Score: {best_score:.2f})")
        return best_route