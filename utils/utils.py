import re
from unidecode import unidecode

def normalize_string(chaine: str) -> str:
    """
    Combine la suppression des accents et le remplacement des caractères non autorisés.

    Étapes :
    1.  Convertit la chaîne en sa version ASCII la plus proche (ex: 'é' -> 'e').
    2.  Remplace tout ce qui n'est pas une lettre, un chiffre, un '.', ou un '_'
        par un seul '_'.
    """
    # Étape 1 : Supprimer les accents et translittérer
    chaine_sans_accents = unidecode(chaine)
    
    # Étape 2 : Remplacer les caractères non autorisés par '_'
    # Le pattern [^\w.] signifie "tout caractère qui n'est PAS (^)
    # un caractère alphanumérique (\w) ou un point (\.)."
    chaine_nettoyee = re.sub(r'[^\w.]', '_', chaine_sans_accents)
    
    return chaine_nettoyee
