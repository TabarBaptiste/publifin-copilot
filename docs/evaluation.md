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

## Phase 1 — latence à froid (2026-11-18)

Quand Ollama a déchargé les modèles (par défaut après 5 minutes sans requête), la première question doit d'abord les recharger. Mesure sur 3 questions différentes (pour éviter que le cache de prompt d'Ollama fausse la comparaison) :

| Situation | Total | Recherche (embedding) | Chargement du modèle de chat | Lecture du prompt | Génération |
| --- | --- | --- | --- | --- | --- |
| Froid (modèles déchargés) | 30,1 s | 5,6 s | 4,8 s | 13,1 s (1 716 tokens) | 4,5 s |
| Chaud (2ᵉ question) | 18,7 s | 2,1 s | 0 s | 8,3 s (1 401 tokens) | 6,0 s |
| Après préchauffage | 18,8 s | 2,1 s | 0 s | 7,2 s (1 191 tokens) | 7,4 s |

Le surcoût à froid est d'environ 10 s (chargement des deux modèles, puis lecture du prompt plus lente le temps que la mémoire « chauffe »).

### Mesures prises
- **Préchauffage au démarrage de l'API** : chargement des deux modèles dans un thread, sans bloquer `/health` (12,9 s). La taille de contexte (`num_ctx`) doit être la même que pour les questions, sinon Ollama recharge le modèle à la première question.
- **`keep_alive = 30m`** sur chaque appel : les modèles restent en mémoire 30 minutes après la dernière question au lieu de 5. Coût : environ 4,5 Go de RAM occupés pendant ce temps.

Ces chiffres varient selon la charge de la machine : la même question a pris 65 s lors d'un test dans le navigateur, avec d'autres programmes actifs (cause exacte non mesurée).
