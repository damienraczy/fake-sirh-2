# utils_llm.py
import re

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
