# Évaluation

Résultats mesurés avec `uv run python scripts/eval_answers.py <top_k>` sur les 17 questions de [`eval/questions.jsonl`](../eval/questions.jsonl) (12 avec réponse, 5 pièges). Matériel : Ryzen 5 5600H, 16 Go, CPU seul. Modèle `qwen3:4b-instruct`, embeddings `bge-m3`, seuil de distance 0,43.

Une réponse est « bonne » si elle n'est pas refusée, contient les mots-clés attendus et cite une page attendue. Cette règle est stricte : voir les faux négatifs plus bas.

## Phase 1 — latence et nombre d'extraits (2026-11-17)

| top_k | Prompt | Bonnes réponses | Refus corrects | Latence médiane | p95 |
| --- | --- | --- | --- | --- | --- |
| 5 | v1 | 8/12 | 5/5 | 59,9 s | 78,6 s |
| 3 | v1 | 4/12 | 5/5 | 9,6 s | 29,7 s |
| 2 | v1 | 4/12 | 5/5 | 8,6 s | 23,8 s |
| 3 | v2 « phrases complètes » | 10/12 | 5/5 | 33,8 s | 37,1 s |
| 3 | v3 « concis » | 10/12 | 5/5 | 33,3 s | 36,3 s |
| **2** | **v3 « concis »** | **9/12** | **5/5** | **12,0 s** | **20,5 s** |

Les refus des questions pièges prennent 2 s : le garde-fou de distance n'appelle pas le modèle.

### Ce qu'on en retient
1. **Le prompt v1 produisait souvent une réponse réduite à « [1] »** (une citation sans texte). C'était la principale cause d'échec, bien avant le manque de contexte. Exiger des phrases complètes fait passer 3 extraits de 4/12 à 10/12.
2. **La latence dépend surtout du nombre d'extraits** (lecture du prompt sur CPU) : 5 extraits ≈ 60 s, 3 ≈ 33 s, 2 ≈ 12 s. L'objectif « < 30 s en local » n'est tenu qu'avec 2 extraits.
3. **Choix retenu : `top_k = 2`**, prompt v3. C'est un compromis à revalider en Phase 5 avec plus de questions et d'autres tailles de morceaux (un seul cas de différence entre 2 et 3 extraits, trop peu pour conclure).

### Détail des 3 échecs à `top_k = 2`
- `rgpd-04` : **faux négatif**. La réponse est correcte (retrait aussi simple que le consentement) mais ne contient pas la formule « à tout moment » exigée par le mot-clé.
- `aiact-01` : **vrai défaut**. La réponse donne 35 000 000 EUR mais oublie « 7 % du chiffre d'affaires » et mélange l'amende des institutions de l'Union (1 500 000 EUR) avec celle des entreprises. Un 2ᵉ extrait voisin a brouillé la réponse.
- `cnil-01` : **défaut de recherche** (la fiche « sécurité » de la CNIL n'est pas remontée), déjà vu dans `eval/README.md`.

### Limites
17 questions, une seule exécution par configuration (le modèle est légèrement non déterministe) : ces chiffres donnent un ordre de grandeur, pas une preuve. La Phase 5 ajoutera des questions, des reformulations et une mesure de fidélité par un juge.
