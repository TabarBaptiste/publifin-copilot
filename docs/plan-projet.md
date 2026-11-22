# Projet d'entraînement : Architecte IA sur Azure

Nov 14, 2026 · @Baptiste

## Le projet en bref

**Nom de travail : PubliFin Copilot.** Un assistant IA pour les chargés d'affaires d'une banque publique fictive qui finance les collectivités locales. Il fait deux choses :

1. **Répondre aux questions** à partir d'un corpus de documents (guides de financement, textes réglementaires, doctrine CNIL, AI Act), avec les sources citées. C'est la partie RAG.
2. **Préparer une pré-analyse de demande de financement** : un agent récupère les données publiques d'une commune (population, finances), cherche les règles applicables dans le corpus, rédige une note, puis **attend la validation d'un humain** avant de l'enregistrer. C'est la partie agentique.

Le tout tourne sur Azure, déployé par Infrastructure as Code, avec CI/CD, observabilité, évaluation et une note sécurité/RGPD.

### Pourquoi ce sujet

Chaque brique correspond à une mission type d'architecte IA :

| Mission type | Ce que tu construis |
| --- | --- |
| Cadrer les cas d'usage | Une fiche de cadrage (besoin, valeur, risques) avant de coder |
| Concevoir des agents et du RAG | Le RAG documentaire + l'agent de pré-analyse |
| Plateforme de prototypage sur Azure | Terraform, template de projet, GitHub Actions |
| Observabilité (qualité, coûts) | Application Insights + suivi des tokens |
| Évaluer et industrialiser | Jeu de tests, métriques, recommandation go / no-go |
| Sécurité et IA responsable | Managed Identity, Key Vault, garde-fous anti-injection, note RGPD |
| Documenter et transmettre | README d'architecture, ADR, schémas |

Le domaine (banque publique, collectivités) n'est pas un hasard : en entretien, tu parles leur langue.

### Données utilisées (toutes publiques)

- Documents PDF publics : guides de la CNIL sur l'IA, texte du RGPD, AI Act, rapports annuels de banques publiques, guides de financement des collectivités.
- Données des communes : API Géo (geo.api.gouv.fr) pour la population, et les comptes des collectivités publiés sur data.gouv.fr / data.economie.gouv.fr.

N'utilise jamais de données réelles de ton ancien employeur.

## Architecture cible et stack

### Vue d'ensemble

```
[Front Next.js]  --(Entra ID / token)-->  [API FastAPI - Azure Container Apps]
                                              |
          +-----------------------------------+------------------------------+
          |                     |                       |                    |
  [Azure OpenAI]       [Azure AI Search]        [Blob Storage]      [PostgreSQL]
  chat + embeddings    index vectoriel +        PDF sources         journal d'audit,
                       recherche hybride                            validations
          |
  [Agent LangGraph] --> outils : recherche corpus, API Géo, données finances,
                        rédaction de note, enregistrement (après validation humaine)

Transverse : Key Vault, Managed Identity, Application Insights (OpenTelemetry),
Terraform, GitHub Actions
```

### Stack

| Couche | Choix | Pourquoi |
| --- | --- | --- |
| Langage backend | Python 3.12, gestionnaire **uv** | Langage de référence de l'écosystème IA |
| API | FastAPI + Pydantic | Proche de ce que tu connais avec NestJS |
| Orchestration agent | **LangGraph** (variante : Semantic Kernel) | Très utilisé pour les agents, gère bien la pause pour validation humaine |
| Modèles | Azure OpenAI : un modèle de chat léger (type GPT-4o-mini) + text-embedding-3-small | Coût faible |
| Recherche | Azure AI Search (hybride : mots-clés + vecteurs) | Brique RAG standard sur Azure |
| Stockage | Blob Storage (PDF), PostgreSQL (audit) | Tu connais déjà PostgreSQL |
| Hébergement | Azure Container Apps | Simple, scale à zéro, peu cher |
| Sécurité | Managed Identity, Key Vault, Entra ID | Pas de clé en dur |
| IaC | **Terraform** (ou Bicep) | Standard de l'infrastructure as code |
| CI/CD | GitHub Actions | Visible sur ton GitHub |
| Observabilité | Application Insights + OpenTelemetry | Qualité, latence, coûts |
| Évaluation | Ragas ou promptfoo | Mesurer au lieu de dire « ça marche » |
| Front | Next.js + TypeScript | Ton point fort : une vraie interface |

**Astuce coût :** développe en local avec **Ollama** (un petit modèle open source) derrière une même interface Python, et ne bascule sur Azure OpenAI que pour les tests et la démo.

## Phase 0 — Cadrage (2-3 jours)

Avant de coder, fais ce qu'un architecte ferait. Livrable : `docs/cadrage.md`.

- [x] Décrire les 2 cas d'usage : utilisateur, besoin, gain attendu (ex. temps de réponse à une collectivité).
- [x] Lister les risques : hallucination, fuite de données, coût, dépendance fournisseur.
- [x] Définir les critères de succès mesurables (ex. ≥ 80 % de réponses jugées fidèles aux sources, latence < 5 s, coût < X € / 100 questions).
- [x] Dessiner un premier schéma d'architecture (draw.io ou Excalidraw).

## Phase 1 — Python et RAG en local (2-3 semaines)

Objectif : un RAG qui marche sur ta machine, sans Azure.

- [x] Installer Python (3.14 : voir ADR 0002) et uv, créer le projet, configurer ruff (lint) et pytest.
- [x] Script d'**ingestion** : lire les PDF, découper en morceaux (chunks de \~500-800 tokens avec chevauchement), garder les métadonnées (fichier, page, titre).
- [x] Calculer les embeddings et les stocker dans une base vectorielle locale (Chroma, ou pgvector sur ton PostgreSQL).
- [x] Endpoint FastAPI `POST /ask` : recherche des morceaux pertinents → prompt → réponse **avec citations** (fichier + page).
- [x] Garde-fou : si aucun passage pertinent, l'assistant répond « je ne trouve pas l'information dans les documents » au lieu d'inventer.
- [x] Une interface d'abstraction `LLMProvider` pour passer d'Ollama à Azure OpenAI par une variable d'environnement. *(code et tests faits ; Azure OpenAI jamais appelé pour de vrai, voir ADR 0004)*
- [x] Tests unitaires sur le découpage et le format des réponses.

**Ce que tu apprends :** Python moderne, chaîne RAG complète, prompt avec citations.

## Phase 2 — Passage sur Azure (2 semaines)

Objectif : la même chose, en version cloud, déployée à la main d'abord (pour comprendre), automatisée en phase 3.

- [ ] Créer un compte Azure (crédit gratuit) et un **budget avec alerte** dès le premier jour.
- [ ] Déployer un modèle de chat et un modèle d'embeddings dans Azure OpenAI / Azure AI Foundry.
- [ ] Créer Azure AI Search, définir l'index (champs texte, vecteur, métadonnées), passer l'ingestion dessus.
- [ ] Activer la **recherche hybride** (mots-clés + vecteurs) et comparer la qualité avec la version locale.
- [ ] Stocker les PDF dans Blob Storage.
- [~] Conteneuriser l'API (Dockerfile) et la déployer sur Azure Container Apps. *(Dockerfile fait et testé en local ; déploiement à faire pendant la fenêtre Azure)*
- [ ] Supprimer toute clé en dur : **Managed Identity** pour accéder à OpenAI, Search et Blob ; Key Vault pour le reste.
- [x] Brancher le front Next.js : zone de question, réponse, liste des sources cliquables.

**Ce que tu apprends :** services Azure IA, identités managées, conteneurs, sécurité cloud de base.

## Phase 3 — Plateforme de prototypage : IaC, CI/CD, observabilité (2 semaines)

Objectif : pouvoir détruire et recréer tout l'environnement en une commande. C'est la mission « plateforme sécurisée de prototypage ».

- [~] Décrire toute l'infra en **Terraform** : resource group, OpenAI, AI Search, Storage, Container Apps, Key Vault, Log Analytics, Application Insights, rôles RBAC. *(écrit et validé à blanc, sans Key Vault ni registre : voir ADR 0003)*
- [x] Découper en **modules réutilisables** (`modules/ai-search`, `modules/container-app`…) et un dossier par environnement (`envs/dev`).
- [~] Stocker l'état Terraform dans un Storage Account distant. *(backend configuré ; Storage Account de l'état à créer à l'ouverture d'Azure)*
- [~] Pipeline **GitHub Actions** : *(CI faite : lint, tests, front, `terraform validate`, build et publication de l'image sur GHCR ; `plan`, évaluation RAG et déploiement viendront avec Azure et la Phase 5)*
  - sur pull request : lint, tests, `terraform plan`, évaluation RAG (phase 5) ;
  - sur merge : build de l'image, push dans Azure Container Registry, déploiement.
- [ ] Authentifier GitHub Actions sur Azure par **OIDC** (pas de secret stocké dans GitHub).
- [ ] Instrumenter l'API avec OpenTelemetry : latence par étape (recherche, génération), tokens consommés, coût estimé par requête, erreurs.
- [ ] Un petit tableau de bord (Azure Workbook ou page admin dans ton front) : nombre de requêtes, coût du jour, latence p95, taux de « je ne sais pas ».
- [ ] Bonus : un **template de projet** (cookiecutter ou repo template GitHub) qui génère un nouveau prototype IA avec tout ça déjà branché.

**Ce que tu apprends :** IaC, CI/CD cloud, observabilité et pilotage des coûts.

## Phase 4 — Agent de pré-analyse avec supervision humaine (3 semaines)

Objectif : un agent qui enchaîne plusieurs outils, s'arrête pour validation, et trace tout.

### Scénario

Le chargé d'affaires saisit : « La commune de X demande 2 M€ pour rénover son école. » L'agent :

1. identifie la commune (API Géo) et récupère population et données financières publiques ;
2. calcule quelques indicateurs simples (encours de dette par habitant, capacité de désendettement si les données le permettent) ;
3. cherche dans le corpus les règles et critères applicables (outil RAG de la phase 1) ;
4. rédige une note de pré-analyse structurée, avec sources et points d'attention ;
5. **se met en pause** : l'humain valide, corrige ou rejette dans l'interface ;
6. seulement après validation, enregistre la note (base de données ou Blob).

### À implémenter

- [x] Graphe **LangGraph** avec un état typé, un nœud par étape, et un *interrupt* avant l'enregistrement.
- [x] Outils définis avec des schémas d'entrée stricts (Pydantic) et des droits minimaux : l'agent ne peut pas écrire sans validation.
- [x] **Journal d'audit** dans PostgreSQL : chaque appel d'outil (entrée, sortie, durée), chaque décision humaine (qui, quand, quoi).
- [x] Limites : nombre maximum d'étapes, timeout, budget de tokens par exécution. *(25 étapes, 12 000 tokens, 600 s)*
- [x] Dans le front : timeline des étapes de l'agent + écran de validation.
- [ ] Variante pour aller plus loin : refaire un outil avec **Semantic Kernel** et noter les différences dans un ADR.

**Ce que tu apprends :** conception d'agents, orchestration, human-in-the-loop, traçabilité.

## Phase 5 — Évaluation et recommandation (1-2 semaines)

Objectif : prouver la qualité avec des chiffres, puis trancher comme un architecte.

- [x] Constituer un **jeu de test** de 30 à 50 questions avec la réponse attendue et la source attendue (dont quelques questions pièges sans réponse dans le corpus).
- [~] Mesurer avec Ragas ou promptfoo : fidélité aux sources, pertinence de la réponse, précision de la recherche, taux de refus correct. *(banc maison + juges locaux, voir `docs/evaluation.md` ; Ragas/promptfoo non utilisés)*
- [x] Mesurer aussi latence, coût par question, et robustesse (questions reformulées, fautes de frappe).
- [~] Comparer au moins deux variantes : taille des chunks, recherche vectorielle seule vs hybride, deux modèles. Tableau de résultats dans `docs/evaluation.md`. *(fait : taille des morceaux, nombre d'extraits, 2 modèles ; hybride à tester sur Azure AI Search)*
- [x] Lancer l'évaluation automatiquement dans la CI : la PR échoue si la qualité baisse sous un seuil. *(sans LLM en CI : `scripts/check_eval.py` valide le jeu de questions et exige des résultats commités à jour, ≥ 75 % de bonnes réponses et 100 % de pièges refusés ; la mesure elle-même se lance en local)*
- [x] Rédiger une **recommandation argumentée** (1 page) : on industrialise, on fait évoluer ou on arrête, et à quelles conditions. C'est un livrable typique d'un architecte.

## Phase 6 — Sécurité, RGPD et IA responsable (1 semaine, en continu)

- [ ] Lire l'**OWASP Top 10 for LLM Applications** et, pour chaque risque, noter s'il s'applique et ta mesure (`docs/securite.md`).
- [ ] Tester l'**injection de prompt**, y compris indirecte : glisser dans un PDF du corpus une instruction malveillante et vérifier que l'agent ne l'exécute pas.
- [ ] Garde-fous : filtrage de contenu Azure, validation des sorties d'outils, séparation nette instructions / données dans les prompts.
- [ ] Contrôle d'accès : authentification Entra ID sur l'API, filtrage des documents par rôle dans la recherche (*security trimming*).
- [ ] Note **RGPD** : quelles données passent par le modèle, région d'hébergement (UE), durée de conservation des journaux, masquage des données personnelles dans les logs.
- [ ] Paragraphe **AI Act / IA responsable** : niveau de risque du cas d'usage, transparence vis-à-vis de l'utilisateur, rôle de la supervision humaine.

## Documentation d'architecte (tout au long du projet)

C'est ce qui te distingue d'un développeur qui « a fait un chatbot ».

- [ ] `README.md` : problème, démo (GIF ou vidéo), schéma, lancement en 3 commandes, résultats chiffrés, limites.
- [ ] Schémas au format **C4** (contexte, conteneurs) dans `docs/architecture.md`.
- [ ] Des **ADR** (Architecture Decision Records) courts, par exemple : « Pourquoi LangGraph plutôt que Semantic Kernel », « Pourquoi la recherche hybride », « Pourquoi Container Apps plutôt qu'App Service ».
- [ ] Un guide « créer un nouveau prototype avec le template », pour la partie accompagnement des équipes.

## Organisation pratique

### Structure du dépôt

```
publifin-copilot/
├── apps/
│   ├── api/            # FastAPI : RAG, agent, audit
│   │   ├── rag/        # ingestion, retrieval, prompts
│   │   ├── agent/      # graphe LangGraph, outils
│   │   ├── providers/  # Ollama / Azure OpenAI
│   │   └── tests/
│   └── web/            # Next.js
├── infra/
│   ├── modules/        # Terraform réutilisable
│   └── envs/dev/
├── eval/               # jeu de test + scripts Ragas/promptfoo
├── docs/               # cadrage, architecture, ADR, sécurité, évaluation
└── .github/workflows/
```

### Maîtriser le budget Azure

- Alerte de budget dès le début (par exemple 20 € / mois).
- Modèles légers, et Ollama en local pour le développement.
- Azure AI Search : commence par le niveau gratuit ou le plus bas, et vérifie ses limites avant de choisir.
- Container Apps avec scale à zéro.
- `terraform destroy` quand tu ne travailles pas sur le projet pendant plusieurs jours : c'est aussi la preuve que ton IaC fonctionne.
- Les tarifs changent : vérifie-les sur la calculatrice de prix Azure avant de créer chaque ressource.

### Planning indicatif (environ 12 semaines à temps partiel)

| Semaines | Phase | Jalon visible |
| --- | --- | --- |
| 1 | Phase 0 | Cadrage + schéma publiés sur GitHub |
| 2-4 | Phase 1 | RAG local avec citations |
| 5-6 | Phase 2 | Première démo en ligne sur Azure |
| 7-8 | Phase 3 | Tout recréable par Terraform, CI/CD vert |
| 9-11 | Phase 4 | Agent avec écran de validation |
| 12 | Phases 5-6 | Rapport d'évaluation + note sécurité/RGPD |

En parallèle : certification **AI-900** vers la semaine 4, puis **AI-102** après la phase 4 si tu veux aller plus loin.

**Conseil :** publie au fil de l'eau. Un dépôt avec des commits réguliers et des PR propres vaut plus qu'un gros commit final.

## Valoriser le projet sur le CV et le portfolio

### Sur le CV (section Projets)

> **PubliFin Copilot — Assistant IA générative et agentique sur Azure** (projet personnel) Conception de l'architecture et développement d'un assistant RAG et d'un agent de pré-analyse de financement avec validation humaine et journal d'audit. Azure OpenAI, AI Search, Container Apps, Terraform, GitHub Actions (OIDC), LangGraph, FastAPI, Next.js. Évaluation automatisée (Ragas) : X % de fidélité aux sources, coût moyen Y € / 100 requêtes. Analyse de risques OWASP LLM et note RGPD.

Remplace X et Y par tes vrais résultats : des chiffres mesurés sont ton meilleur argument.

### Sur le portfolio

- Une page dédiée : problème → architecture (schéma) → démo vidéo de 2 minutes → résultats d'évaluation → choix et compromis → limites et suite.
- Mets en avant le rôle d'**architecte** : les ADR, la recommandation go / no-go, la plateforme réutilisable.
- Lien vers le dépôt GitHub et, si le budget le permet, une démo en ligne protégée (sinon la vidéo suffit).

### En entretien

Prépare trois histoires courtes tirées du projet : un choix technique que tu as changé après mesure, un risque de sécurité que tu as trouvé et corrigé, et comment tu expliquerais le projet à un métier non technique.
