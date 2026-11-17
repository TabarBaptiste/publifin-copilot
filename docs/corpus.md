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
| `ofgl-rapport-2025-vue-d-ensemble.pdf` | OFGL (Observatoire des finances et de la gestion publique locales), « Les finances des collectivités locales en 2025 » — vue d'ensemble, comptes 2024 | 21 | Chiffres de référence sur l'épargne, l'investissement et la dette du secteur local |
| `dgcl-cl-en-chiffres-2025-ch1-synthese.pdf` | DGCL, « Les collectivités locales en chiffres 2025 », chapitre 1 (synthèse) | 2 | Chiffres clés, délais de désendettement par type de collectivité |

Total : 500 pages. Chaque PDF a été ouvert et son texte extrait avec `pypdf` pour vérifier qu'il correspond bien au document attendu.

## Points d'attention
- **Licences** : à confirmer avant toute redistribution. Les PDF restent hors du dépôt ; seules les URLs sont publiées.
- **Écartés** : le guide HAS/CNIL de 2026 (IA en santé, hors sujet) et le rapport de la Cour des comptes sur les Antilles et la Guyane (trop local).
- **Manque persistant** : un guide pratique de financement des collectivités (procédures de prêt, critères d'éligibilité) et les règles du Code général des collectivités territoriales. Pistes testées sans succès :
  - le guide DGCL « élaboration, adoption et exécution des budgets locaux » (mars 2024) n'est plus à l'adresse trouvée (erreur 404) ;
  - le bulletin DGCL BIS 211 se télécharge mais son texte est illisible (police mal encodée : il faudrait un OCR) ;
  - Légifrance est une application web : on ne peut pas en tirer proprement le texte des articles du code.
  Le cas d'usage 2 s'appuie donc sur les indicateurs et seuils d'alerte, pas sur des procédures de prêt ; les questions de procédure restent des questions pièges (refus attendu).
- **Chiffres d'années différentes** : le rapport OFGL porte sur 2024, celui de la Cour des comptes sur 2025. Les deux peuvent donner des valeurs différentes pour un même indicateur : bon test de robustesse pour la Phase 5 (la réponse doit préciser l'année).
- **Pages scannées** : `pypdf` extrait du texte sur les 6 fichiers retenus. Aucun OCR n'est nécessaire pour l'instant.
