# CLAUDE.md — PubliFin Copilot

Projet d'entraînement « Architecte IA sur Azure » (projet personnel de Baptiste, destiné au CV/portfolio et à la montée en compétences d'architecte IA).
Plan complet et source de vérité : [docs/plan-projet.md](docs/plan-projet.md) — le relire avant de démarrer une phase.

## Le projet en une phrase

Assistant IA pour les chargés d'affaires d'une banque publique **fictive** finançant les collectivités :

1. **RAG** sur un corpus public (CNIL, RGPD, AI Act, guides de financement) avec citations (fichier + page) ;
2. **Agent LangGraph** de pré-analyse de demande de financement, avec **validation humaine** avant enregistrement et journal d'audit.

## Façon de travailler

- Avancer **phase par phase, étape par étape** (Phase 0 → 6 dans le plan). Ne pas anticiper les phases suivantes.
- Baptiste est développeur full-stack (TypeScript/NestJS/Next.js, PostgreSQL) mais **débutant en Python/Azure/IA** : expliquer brièvement les choix, comparer avec l'équivalent NestJS quand utile.
- Réponses et documentation en **français**. Code, noms de variables, commits en anglais (commits : Conventional Commits).
- Objectif architecte : chaque choix structurant donne lieu à un **ADR court** dans `docs/adr/` (`NNNN-titre.md`).
- Cocher les cases du plan au fil de l'avancement dans `docs/plan-projet.md`.
- Commits réguliers, petites PR propres (le dépôt est aussi une vitrine).

## Principes de code (adaptés des guidelines Karpathy-style)

1. **Réfléchir avant de coder** : énoncer les hypothèses, présenter les alternatives au lieu de choisir en silence, signaler s'il existe plus simple, demander quand c'est flou.
2. **Simplicité d'abord** : le minimum de code qui résout le problème. Pas de fonctionnalité, abstraction ou configurabilité non demandée ; pas de gestion d'erreur pour des cas impossibles.
3. **Changements chirurgicaux** : ne toucher que ce qui est nécessaire, respecter le style existant, ne pas refactorer ce qui n'est pas cassé. Chaque ligne modifiée doit se rattacher à la demande. Nettoyer uniquement ce que mes changements ont rendu inutile.
4. **Exécution guidée par des critères vérifiables** : transformer la tâche en objectif testable (bug → test qui le reproduit puis qui passe ; refactor → tests verts avant/après). Pour les tâches multi-étapes, annoncer un plan court `étape → vérification`.

## Git

- **Ne jamais ajouter `Co-Authored-By: Claude` (ni mention « Generated with Claude Code »)** dans les commits ou PR. Consigne explicite de Baptiste, appliquée aussi via `attribution` dans `.claude/settings.json`.
- Ne committer/pousser que sur demande de Baptiste.

## Stack cible

Python 3.14 (3.15 écarté : `onnxruntime` sans wheel, voir [ADR 0002](docs/adr/0002-vector-store-chroma-local.md) ; géré par **uv**) · FastAPI + Pydantic · LangGraph · Azure OpenAI (chat léger + text-embedding-3-small) · Azure AI Search (hybride) · Blob Storage · PostgreSQL (audit, pgvector possible en local) · Azure Container Apps · Key Vault + Managed Identity + Entra ID · Terraform · GitHub Actions (OIDC) · Application Insights + OpenTelemetry · Ragas/promptfoo · Next.js + TypeScript.
Développement local : **Ollama** derrière l'interface `LLMProvider` (bascule Azure OpenAI par variable d'environnement).

## Structure du dépôt

```
apps/api/        FastAPI : rag/ (ingestion, retrieval, prompts), agent/ (graphe, outils), providers/ (Ollama, Azure OpenAI), tests/
apps/web/        Next.js
infra/           modules/ (Terraform réutilisable), envs/dev/
eval/            jeu de test + scripts Ragas/promptfoo
docs/            plan-projet.md, cadrage, architecture (C4), adr/, securite, evaluation
data/corpus/     PDF publics (non versionnés)
.github/workflows/
```

## Règles non négociables

- **Aucun secret en dur**, jamais de `.env` commité (fournir `.env.example`). Cible Azure : Managed Identity / Key Vault / OIDC.
- **Dépôt public, vu par n'importe quelle entreprise** : ne jamais mentionner d'offre d'emploi, d'entreprise ciblée ou d'employeur (ex-employeur compris) dans le code, les docs, les commits ou les PR.
- **Données publiques uniquement.** Aucune donnée réelle de l'ancien employeur de Baptiste, aucune donnée personnelle réelle.
- **Budget : 0 €, aucune dépense** (voir [ADR 0001](docs/adr/0001-budget-zero-euro.md)). Tout se fait en local (Ollama, Chroma) sauf une fenêtre Azure time-boxée sur l'essai gratuit (~30 jours), **sans jamais passer en paiement à l'usage**. Terraform : `fmt`/`validate`/`plan` librement, **`apply` seulement avec accord explicite de Baptiste**. Ne jamais créer/déployer de ressource Azure ni ouvrir un compte payant sans son accord ; vérifier qu'un service est gratuit avant de le proposer ; `terraform destroy` après chaque session cloud.
- Machine de dev : Ryzen 5 5600H, 16 Go RAM, GPU AMD 4 Go (accélération Ollama incertaine) → modèles quantifiés 3B–8B, embeddings multilingues (`bge-m3` envisagé, corpus en français ; voir cadrage §8).
- L'agent ne peut **jamais écrire sans validation humaine** ; chaque appel d'outil et décision est tracé dans l'audit.
- Le RAG répond « je ne trouve pas l'information dans les documents » plutôt que d'inventer ; toujours citer les sources.
- Mesurer avant d'affirmer : décisions de qualité appuyées par l'évaluation (Phase 5).

## Piège Windows (uv)

Le Python géré par uv ne s'installe pas dans son dossier par défaut (`%APPDATA%/uv/python` est redirigé par l'app Claude et casse les liens). Il est installé dans `.uv-python/` (ignoré par git). Pour réinstaller : `UV_PYTHON_INSTALL_DIR=<racine du dépôt>/.uv-python uv python install 3.14`. Le `.venv` existant suffit ensuite pour `uv run`.

## Conventions

- Python : ruff (lint + format), pytest, typage strict encouragé (Pydantic), gestion des dépendances via `uv` uniquement.
- TypeScript : ESLint + Prettier, `strict` activé.
- Terraform : modules réutilisables, `terraform fmt` + `validate` avant commit.
- Tests unitaires sur tout code de logique (chunking, format de réponses, outils de l'agent).

## Commandes (à compléter au fil des phases)

```bash
# API (Phase 1)
cd apps/api && uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check .
uv run uvicorn main:app --reload   # http://localhost:8000/health
uv run python scripts/download_corpus.py   # télécharge les PDF (docs/corpus.md)
uv run python -m rag.ingest                # chunking 1200/150 + embeddings (Ollama) -> data/chroma (~6 min)
uv run python scripts/eval_retrieval.py    # qualité de la recherche sur eval/questions.jsonl (sans LLM)
uv run python scripts/evaluate.py run|judge|report   # Phase 5 : réponses, juges locaux, tableau (eval/results/)
uv run python scripts/check_eval.py        # contrôle CI : jeu de questions + résultats commités au-dessus du seuil

# Agent de pré-analyse (Phase 4) : PostgreSQL local (audit, notes, checkpoints), port 5433
docker compose up -d db
# Sans base, l'API démarre quand même : /ask marche, /analyses répond 503.

# Image Docker de l'API (Ollama de l'hôte, index local monté)
docker build -t publifin-api apps/api
docker run --rm -p 8000:8000 -v "$PWD/data:/srv/data" -e OLLAMA_BASE_URL=http://host.docker.internal:11434 publifin-api

# Terraform (à blanc, gratuit ; apply seulement avec accord explicite)
cd infra && terraform fmt -check -recursive && cd envs/dev && terraform init -backend=false && terraform validate

# Front (Next.js 16, http://localhost:3000 ; API attendue sur NEXT_PUBLIC_API_URL, défaut localhost:8000)
cd apps/web && npm install && npm run dev
npm run lint && npx tsc --noEmit && npm run build
```

## État d'avancement

- [x] Préparation du terrain (dépôt, structure, CLAUDE.md)
- [x] Phase 0 — Cadrage (`docs/cadrage.md`), validé
- [~] Phase 1 — RAG local : fait (corpus 6 PDF, ingestion, /ask avec citations et refus, tests, jeu de 17 questions `eval/`) ; latence réglée (préchauffage)
- [~] Front Next.js (Phase 2, partie locale) : page de question, réponse citée, sources cliquables, états chargement/erreur/refus
- [~] Préparation Azure à blanc : Dockerfile de l'API testé, Terraform (5 modules + envs/dev) validé sans déploiement (ADR 0003)
- [x] CI GitHub Actions écrite (`ci.yml` : API, web, Terraform ; `docker.yml` : image sur GHCR) — à vérifier au premier push
- [x] Phase 4 locale : agent LangGraph de pré-analyse + validation humaine + audit PostgreSQL + page `/analyses` (ADR 0005) ; reste : variante Semantic Kernel (facultatif)
- [~] Code Azure prêt et testé sans compte : `AzureOpenAIProvider`, `AzureSearchStore`, bascule par `LLM_PROVIDER=azure_openai` (ADR 0004) ; jamais exécuté en réel
- [~] Phase 5 : 49 questions, 3 variantes comparées, go sous conditions (`docs/evaluation.md`), réglage 1 200/150 + 4 extraits appliqué (ADR 0006) ; contrôle d'évaluation en CI ; reste : recherche hybride sur Azure
- [ ] Phases 2, 3 et 6 : voir le plan
