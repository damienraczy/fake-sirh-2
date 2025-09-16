# Problème d'affichage mélangeant du markdown
**Côté front‑end** : remplacer l’appel à escapeHtml par un véritable parseur Markdown (par exemple marked.js ou **markdown-it**)
et désinfecter ensuite le HTML généré.
Cela permettrait d’afficher correctement les titres, puces ou blocs de code.

Et affichage trop étroit.

La solution est d'utiliser markdown-it.
