# Corpus documentaire

PDF publics, en français, utilisés par le RAG. Ils ne sont **pas versionnés** (`data/corpus/` est ignoré par git) : on les récupère avec

```bash
cd apps/api && uv run python scripts/download_corpus.py
```

| Fichier | Source | Pages | Rôle |
| --- | --- | --- | --- |
| `rgpd-reglement-2016-679.pdf` | EUR-Lex, règlement (UE) 2016/679 | 88 | Protection des données |
| `ai-act-reglement-2024-1689.pdf` | EUR-Lex, règlement (UE) 2024/1689 | 144 | Régulation de l'IA |
| `cnil-ia-liste-de-verification-2025.pdf` | CNIL, fiches pratiques IA (liste de vérification, juillet 2025) | 4 | Conformité RGPD des systèmes d'IA |
| `cour-des-comptes-finances-locales-2026.pdf` | Cour des comptes, « Les finances publiques locales : résultats 2025 et perspectives 2026 » (juillet 2026) | 241 | Situation financière des collectivités, seuils d'alerte (épargne brute, années d'épargne) |

Total : 477 pages. Chaque PDF a été ouvert et son texte extrait avec `pypdf` pour vérifier qu'il correspond bien au document attendu.

## Points d'attention
- **Licences** : à confirmer avant toute redistribution. Les PDF restent hors du dépôt ; seules les URLs sont publiées.
- **Écartés** : le guide HAS/CNIL de 2026 (IA en santé, hors sujet) et le rapport de la Cour des comptes sur les Antilles et la Guyane (trop local).
- **Manque** : un guide pratique de financement des collectivités (procédures de prêt, critères d'éligibilité). Le rapport de la Cour des comptes couvre les indicateurs, pas les procédures. À compléter plus tard si une source libre de droits est trouvée ; sinon le périmètre du cas d'usage 2 s'appuiera sur les indicateurs et les règles de la doctrine.
- **Pages scannées** : `pypdf` extrait du texte sur les 4 fichiers. Aucun OCR n'est nécessaire pour l'instant.
