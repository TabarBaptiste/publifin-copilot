# Jeu de questions de référence

`questions.jsonl` : une question par ligne (JSON Lines). Format :

| Champ | Sens |
| --- | --- |
| `id` | identifiant stable (`rgpd-01`, `trap-03`…) |
| `question` | question posée à `/ask` |
| `type` | `answerable` (réponse dans le corpus), `not_in_corpus` (sujet attendu mais absent) ou `off_topic` (hors sujet) |
| `expected_answer` | réponse attendue, rédigée à la main d'après le document |
| `expected_sources` | fichier et pages où se trouve la réponse (vérifiées en lisant les PDF) |
| `keywords` | éléments qui doivent apparaître dans une bonne réponse |

Pour les questions `not_in_corpus` et `off_topic`, le comportement attendu est le refus « Je ne trouve pas l'information dans les documents ».

## Lancer la mesure de recherche (sans LLM, quelques secondes)
```bash
cd apps/api && uv run python scripts/eval_retrieval.py
```
Elle indique, pour chaque question, si un passage attendu est retrouvé dans le top 5 et à quelle distance, et ce que donnerait chaque seuil de pertinence.

## Limites
49 questions (28 de base, 10 reformulations ou fautes `paraphrase`/`typo` reliées par `variant_of`, 11 pièges) ; champ `category` : base, paraphrase, typo, trap. Banc : `apps/api/scripts/evaluate.py` (run, judge, report) ; résultats dans `eval/results/` ; analyse dans `docs/evaluation.md`. Seuil `max_distance` : voir la Phase 5, il reste fragile.

**Contrôle en CI** (`uv run python scripts/check_eval.py`, sans LLM) : le jeu de questions doit être bien formé, et `eval/results/default-1200-k4.jsonl` doit couvrir toutes les questions, avoir été mesuré avec les réglages actuels (`top_k`, modèle, `max_distance`) et rester au-dessus du seuil (≥ 75 % de bonnes réponses, tous les pièges refusés). Après une modification du RAG ou du jeu de questions, relancer la mesure en local (supprimer le fichier, puis `scripts/evaluate.py run default-1200-k4`) et commiter le résultat.

## Premier constat (recherche seule, bge-m3, 935 morceaux, 2026-11-17)
- Passage attendu retrouvé : top 1 pour 9/12 questions, top 3 et top 5 pour 11/12. Seule `cnil-01` échoue : la fiche « sécurité » de la CNIL n'est pas remontée (la question parle de « fonctionnement », la fiche de « sécurité des données »).
- Distance du meilleur passage : ≤ 0,418 pour les questions à réponse ; ≥ 0,448 pour celles à refuser. L'écart est faible : le seuil de `max_distance` est fixé à **0,43** (0,45 laissait passer `trap-01`). À revalider avec plus de questions en Phase 5.
- Deux pages attendues manquaient au départ (`cdc-02`, `cdc-04`) : la même information figure en plusieurs endroits du rapport. Les listes de pages doivent rester des « pages valables », pas une page unique.
