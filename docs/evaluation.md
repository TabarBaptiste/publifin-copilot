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

## Phase 5 — évaluation comparée (2026-11-18)

### Méthode

- **Jeu de test** : `eval/questions.jsonl`, 49 questions : 28 de base à réponse, 10 reformulations ou fautes de frappe, 11 pièges (hors corpus, hors sujet, tentative d'injection). Chaque fait et chaque page attendue ont été relus dans les PDF.
- **Mesures** : (1) règle automatique (mots-clés attendus + page attendue citée ; pour un piège, le refus) ; (2) deux juges locaux croisés (`gemma3:4b`, `qwen3:4b-instruct`) qui notent fidélité (aucune affirmation hors extraits) et pertinence (même information que la référence) ; (3) latence de bout en bout, tokens estimés (3,5 caractères par token) et coût indicatif.
- **Une variable à la fois** contre la base ; machine CPU seule, runs séquentiels. Commande : `uv run python scripts/evaluate.py run|judge|report` (résultats bruts dans `eval/results/`).
- **Coût indicatif** : tarif supposé de classe gpt-4o-mini (0,15 $ / 0,60 $ par million de tokens), **à vérifier avant tout chiffrage** ; Ollama local coûte 0 €.

### Résultats

| Variante | Bonnes (règle) | Refus corrects | Passage retrouvé | Reform./fautes | Médiane | p95 | Coût /1000 q | Fidèle (gemma / qwen) | Pertinente (gemma / qwen) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline` (2400/300, 2 extraits, qwen3:4b) | 23/38 | 11/11 | 29/38 | 6/10 | 19,1 s | 24,2 s | 0,21 $ | 33/34 · 24/34 | 33/34 · 24/34 |
| `chunks1200-k4` (1200/150, 4 extraits) | **30/38** | 11/11 | **35/38** | **8/10** | 20,8 s | 27,0 s | 0,22 $ | 31/31 · 27/31 | 31/31 · 27/31 |
| `gemma-k2` (gemma3:4b, 2 extraits) | 21/38 | 9/11 | 29/38 | 5/10 | **15,4 s** | **17,8 s** | 0,22 $ | 28/31 · 18/31 | 28/31 · 19/31 |

Les juges ne notent que les réponses données (pas les refus) ; les dénominateurs diffèrent donc selon la variante.

### Ce qu'on en retient

1. **Morceaux de 1 200 caractères + 4 extraits : meilleure variante** (+7 bonnes réponses, +6 passages retrouvés, reformulations 8/10), pour +1,7 s de médiane et un coût de tokens identique (même budget de contexte). C'est l'effet de la granularité, pas du nombre d'extraits seul : on n'a pas isolé les deux facteurs (limite).
2. **`gemma3:4b` plus rapide mais moins bon** : 21/38, 2 refus à tort manqués sur les pièges (9/11). Pas de gain de qualité qui justifie le changement.
3. **Les juges locaux sont peu fiables.** `gemma3:4b` valide presque tout (fidèle 31/31 sur `chunks1200-k4`) ; `qwen3:4b-instruct` est plus sévère mais accorde ou refuse parfois contre la règle. Les deux juges sont d'accord sur 22 à 27 questions sur 31 selon la variante. Les verdicts de juge servent d'indice, **la règle (mots-clés + page) fait foi** ; une revue humaine d'un échantillon reste nécessaire avant d'afficher des taux de fidélité.
4. **Pièges** : les 11 sont refusés par la base et par `chunks1200-k4`, y compris l'injection de prompt (`trap-11`). Mais le seuil `max_distance = 0,43` est fragile : la meilleure distance d'une question à réponse monte à 0,526 (`rgpd-07b`, refusée à tort) tandis qu'un piège descend à 0,351 (`trap-06`). Seuil 0,35 : 28/38 gardées, 11/11 refus corrects ; 0,40 : 35/38 et 9/11 ; 0,45 : 37/38 et 7/11. Aucun seuil unique ne sépare proprement les deux : c'est un argument pour la recherche hybride d'Azure AI Search (non testable avec Chroma) plutôt que pour un nouveau réglage.
5. **Échecs de recherche réels restants** (`cnil-01`, `cnil-03`, `dgcl-01`…) : la fiche CNIL de 4 pages est dominée par sa page 1, et la page DGCL ne contient qu'une phrase courte.
6. **Correction de mesure** : le mot-clé de `rgpd-04` avait des accents cassés et ne pouvait jamais correspondre ; le « faux négatif » de la Phase 1 venait de là. Les chiffres de la Phase 1 ne sont pas comparables à ceux-ci.
7. **Latence** : ~20 s par réponse sur CPU, quelle que soit la variante ; c'est le modèle, pas la recherche. Le coût local est nul ; le coût cloud indicatif (~0,2 $ pour 1 000 questions) est négligeable face à la latence.

### Recommandation : go sous conditions

- **Go** pour garder le RAG local comme base de la suite, en adoptant **morceaux de 1 200/150 et 4 extraits** (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`) et `qwen3:4b-instruct`. Il faut **ré-ingérer le corpus** avec ces valeurs (l'index par défaut est encore à 2 400/300).
- **Conditions avant d'afficher des chiffres** : 8 questions restent en échec sur 38 (dont plusieurs de recherche) ; relire à la main un échantillon de réponses fidèles/pertinentes ; ne pas modifier `max_distance` sans mesure sur Azure AI Search (hybride).
- **No-go** pour changer de modèle local (`gemma3:4b`) ou pour s'appuyer seul sur un juge 4B.

### Limites

- Corpus de 6 PDF, 49 questions : écarts d'une ou deux questions non significatifs.
- Latences mesurées sur CPU seul, une exécution par variante ; le `baseline` a dû être repris après un délai dépassé d'Ollama (mesures de la reprise non perturbées).
- Variantes non isolées (taille des morceaux et nombre d'extraits changent ensemble) ; recherche hybride, rerank et modèles Azure non évalués.
