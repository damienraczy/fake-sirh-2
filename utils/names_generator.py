# =============================================================================
# utils/names_generator.py
# =============================================================================

import random
from typing import Tuple, Set

class NamesGenerator:
    """
    Générateur de prénoms et noms pour la population calédonienne
    """
    
    def __init__(self):
        self.prenoms_hommes = [
            "Adrien", "Ali", "Antoine", "Benjamin", "Clément",
            "Damien", "David", "Dylan", "Elie", "Enzo",
            "Gilles", "Hugo", "Jean", "John", "Jonas",
            "Jesequiel", "Jordan", "Jérôme", "Kévin", "Kilian",
            "Lucas", "Ludovic", "Malik", "Mana", "Manuel",
            "Marcel", "Mathieu", "Maxime", "Mickael", "Nathan",
            "Nicolas", "Noah", "Oliver", "Olivier", "Paul",
            "Pierre", "Romain", "Samuel", "Soane", "Téva",
            "Thomas", "Tony", "Tupai", "Victor", "Waia",
            "Wesley", "William", "Yann", "Yohann", "Yvan"
        ]
        
        self.prenoms_femmes = [
            "Aïcha", "Aline", "Alice", "Anaïs", "Camille",
            "Chloé", "Claire", "Clara", "Djina", "Elodie",
            "Emilie", "Emma", "Ena", "Élise", "Fatima",
            "Hina", "Inès", "Isabelle", "Jade", "Julie",
            "Kaia", "Laura", "Laurine", "Léa", "Leila",
            "Lina", "Maeva", "Malia", "Malika", "Manuia",
            "Maria", "Marie", "Mélanie", "Nawel", "Noémie",
            "Océane", "Olivia", "Pauline", "Rani", "Sanaa",
            "Sarah", "Sophie", "Stéphanie", "Talisa", "Tanya",
            "Tara", "Tehani", "Teresa", "Tess", "Vaiana"
        ]
        
        self.noms_famille = [
            "Ahmat", "Bernard", "Blanchard", "Brun", "Carpentier",
            "Chan", "Dubois", "Dupont", "Durand", "Fabre",
            "Fao", "Forest", "Garnier", "Gautier", "Imani",
            "Kauma", "Kawa", "Lagikula", "Lemoine", "Leroy",
            "Mahé", "Martin", "Mata-Kili", "Michel", "Mézières",
            "Moreau", "Mory", "Naisseline", "Nguyen", "Van-Soc-Yen",
            "N‘Guyen", "Ounë", "Païta", "Perez", "Petit",
            "Paitawea", "Renaud", "Richard", "Rivet", "Robert",
            "Rosen", "Roux", "Silva", "Taïeb", "Tiaou",
            "Tran", "Vama", "Van-mai", "Waia", "Wamytan"
        ]
        
        self.used_combinations: Set[str] = set()
    
    def generate_unique_name(self, is_male: bool) -> Tuple[str, str, str]:
        """
        Génère un prénom/nom unique avec email
        
        Args:
            is_male: True pour homme, False pour femme
            
        Returns:
            Tuple (prénom, nom, email_base)
        """
        max_attempts = 1000
        attempt = 0
        
        while attempt < max_attempts:
            # Choisir le prénom selon le genre
            if is_male:
                prenom = random.choice(self.prenoms_hommes)
            else:
                prenom = random.choice(self.prenoms_femmes)
            
            nom = random.choice(self.noms_famille)
            
            # Créer l'identifiant unique
            identifiant = f"{prenom}_{nom}"
            
            if identifiant not in self.used_combinations:
                self.used_combinations.add(identifiant)
                
                # Générer la base email (sera complétée avec le domaine)
                email_base = f"{prenom.lower().replace('é', 'e').replace('è', 'e').replace('ï', 'i').replace('ç', 'c')}.{nom.lower().replace('-', '')}"
                
                return prenom, nom, email_base
            
            attempt += 1
        
        # Si on n'arrive pas à générer un nom unique, lever une exception
        raise Exception(f"Impossible de générer un nom unique après {max_attempts} tentatives")
    
    def reset(self):
        """Remet à zéro la liste des noms utilisés"""
        self.used_combinations.clear()
