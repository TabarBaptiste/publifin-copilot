# ADR 0004 — Code Azure : fournisseur OpenAI et index vectoriel interchangeables

- **Statut** : accepté (code et tests sans Azure ; jamais exécuté contre un vrai compte)
- **Date** : 2026-11-18

## Contexte
L'API doit tourner à l'identique en local (Ollama + Chroma) et sur Azure (Azure OpenAI + AI Search), sans réécriture le jour du déploiement, et sans clé stockée.

## Décision
- **Deux interfaces, deux implémentations chacune** :
  - `LLMProvider` : `OllamaProvider` (local) et `AzureOpenAIProvider` (SDK `openai` + `azure-identity`).
  - `VectorStore` : `ChromaStore` (fichiers locaux) et `AzureSearchStore` (SDK `azure-search-documents`).
- **Un seul réglage** : `LLM_PROVIDER=azure_openai` bascule aussi l'index sur Azure AI Search. `VECTOR_STORE` permet de forcer l'autre combinaison. Raison : les embeddings de deux modèles différents (`bge-m3` en 1 024 dimensions, `text-embedding-3-small` en 1 536) ne sont pas comparables, chaque fournisseur a donc son propre index, à reconstruire par `python -m rag.ingest`.
- **Authentification par Entra ID** (`DefaultAzureCredential`) : `az login` en local, identité managée sur Azure. Aucune clé, aucun secret.
- **Recherche vectorielle seule** pour l'instant. AI Search renvoie un score cosinus `1 / (1 + distance)` ; on le reconvertit en distance pour réutiliser le seuil de pertinence. Les scores d'une recherche hybride sont de type RRF (rangs fusionnés) et ne se convertissent pas ainsi : l'hybride sera ajouté après mesure (Phase 2/5), avec une autre façon de décider du refus.
- **Identifiants de documents hachés** (SHA-1) : AI Search refuse les `:` et `.` de `fichier.pdf:12:3`.
- **Imports paresseux** : les SDK Azure ne se chargent que si le fournisseur est choisi.

## Alternatives écartées
- **Une seule abstraction « RAG backend »** : mélange deux choix indépendants (modèle de langue, index) et complique les tests.
- **Embeddings locaux avec index Azure** : possible, mais l'ingestion en cloud se ferait depuis une machine qui n'a pas forcément Ollama. À reconsidérer si les coûts d'embeddings pèsent.

## Conséquences
- (+) 32 tests sans compte Azure : conversion des scores, identifiants, correspondance des déploiements, erreurs transformées en `ProviderUnavailable`.
- (−) **Non vérifié en réel** : formule du score, comportement de `fr.microsoft` comme analyseur, rôles sur le niveau gratuit d'AI Search. À contrôler dès le premier `apply`.
- (−) **Le seuil de pertinence `max_distance` (0,43) a été réglé pour `bge-m3`.** Avec `text-embedding-3-small` les distances seront différentes : relancer `scripts/eval_retrieval.py` après la première ingestion Azure et recalibrer.
- (−) Le comportement du prompt (citations, phrases complètes) a été réglé pour `qwen3:4b-instruct` ; à revérifier avec `gpt-4o-mini` via `scripts/eval_answers.py`.
