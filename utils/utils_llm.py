# utils_llm.py
import re
import unicodedata
import string

_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json|jsonld|txt|text)?\s*(?P<body>.+?)\s*```\s*$",
    re.IGNORECASE | re.DOTALL,
)

def strip_markdown_fences(s: str) -> str:
    """
    Supprime un bloc de fences Markdown entourant du JSON/texte.
    Ne modifie rien si aucun fence n'est détecté.
    """
    if not isinstance(s, str):
        return s
    m = _JSON_FENCE_RE.match(s.strip())
    return m.group("body") if m else s


def normalize_string(s: str) -> str:
    """
    Normalise une chaîne de caractères en supprimant les espaces superflus,
    en convertissant les caractères spéciaux en leurs équivalents ASCII
    et en remplaçant la ponctuation et les espaces par des tirets bas (_).
    """

    if not isinstance(s, str):
        return s
    
    # Remplacer tous les accents et caractères spéciaux par leurs équivalents ASCII
    normalized_s = unicodedata.normalize('NFD', s)
    ascii_s = "".join(char for char in normalized_s if unicodedata.category(char) != 'Mn')
    
    # Supprimer la ponctuation standard. Nous gardons les espaces pour l'instant.
    # On ajoute le tiret '-' à la ponctuation pour s'assurer qu'il soit aussi remplacé.
    punctuations = string.punctuation.replace('_', '') # On garde l'underscore pour la fin
    s_no_punc = "".join(char for char in ascii_s if char not in punctuations)
    
    # Supprimer les espaces superflus (tabulations, retours à la ligne, espaces multiples)
    # et remplacer par un simple espace
    cleaned_s = " ".join(s_no_punc.split())
    
    # Ligne finale : remplacer tous les espaces restants par un tiret bas (_)
    final_s = cleaned_s.replace(" ", "_")
    
    return final_s

