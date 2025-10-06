import re
import random
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



def gaussian_score(center: float, sigma: float = 0.5, min: float = 1.0, max: float=5.0) -> float:
    """
    Retourne une note sur [1.0, 5.0] obtenue en tirant
    un échantillon d’une loi normale centrée sur *center*.

    Parameters
    ----------
    center : float
        Valeur attendue (moyenne de la distribution). Doit être
        comprise entre 1.0 et 5.0 inclusive.
    sigma : float, optional (default 0.5)
        Écart-type de la distribution. Plus celui-ci est
        grand, plus la note peut s’éloigner de la moyenne.
    min : float, optional (default 1.0)
        Valeur minimale (incluse) que peut prendre la note.
    max : float, optional (default 5.0)
        Valeur maximale (incluse) que peut prendre la note.
    Returns
    -------
    float
       Une note aléatoire clamped entre 1.0 et 5.0.
    """
    if not (min <= center <= max):
        raise ValueError(f"center doit être compris entre {min} et {max} inclus.")

    # on ré‑tire tant que le résultat n’est pas dans l’intervalle
    while True:
        s = random.normalvariate(center, sigma)
        if min <= s <= max:
            return round(s, 3)            # 3 décimales suffisent pour une note
