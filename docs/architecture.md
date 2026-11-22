# Architecture

Schémas au format [C4](https://c4model.com) : **contexte** (qui utilise le système, avec quoi il échange), puis **conteneurs** (les applications et stockages qui le composent), en local et sur Azure. Les choix sont justifiés dans les [ADR](adr/).

## Niveau 1 : contexte

```mermaid
flowchart LR
    ca(["👤 Chargé d'affaires<br/><i>pose des questions, lance et valide<br/>les pré-analyses</i>"])
    sys["<b>PubliFin Copilot</b><br/>RAG cité + agent de pré-analyse<br/>avec validation humaine"]
    corpus[("Corpus public<br/><i>RGPD, AI Act, CNIL,<br/>Cour des comptes, OFGL, DGCL</i>")]
    geo["API Géo<br/><i>geo.api.gouv.fr</i>"]
    ofgl["Données OFGL<br/><i>comptes des communes</i>"]
    llm["Modèle de langage<br/><i>Ollama en local,<br/>Azure OpenAI dans le cloud</i>"]

    ca -- "questions, demandes,<br/>décisions" --> sys
    sys -- "réponses citées,<br/>notes à valider" --> ca
    corpus -- "PDF ingérés" --> sys
    sys -- "recherche de commune" --> geo
    sys -- "finances de la commune" --> ofgl
    sys -- "génération, embeddings" --> llm
```

Tout est public : le corpus (6 PDF officiels, voir [corpus.md](corpus.md)) et les données financières. La banque est fictive.

## Niveau 2 : conteneurs, en local (état actuel)

```mermaid
flowchart LR
    ca(["👤 Chargé d'affaires"])

    subgraph poste["Poste de développement (0 €)"]
        web["<b>Front</b><br/>Next.js 16, TypeScript<br/><i>/ : questions<br/>/analyses : pré-analyses</i>"]
        api["<b>API</b><br/>FastAPI, Python 3.14<br/><i>/ask, /analyses</i>"]
        rag["RAG<br/><i>recherche, seuil, citations</i>"]
        agent["Agent LangGraph<br/><i>chemin fixe, interrupt<br/>avant enregistrement</i>"]
        chroma[("Chroma<br/><i>1 760 morceaux,<br/>bge-m3</i>")]
        pg[("PostgreSQL<br/><i>audit append-only,<br/>notes, checkpoints</i>")]
        ollama["Ollama<br/><i>qwen3:4b-instruct,<br/>bge-m3</i>"]
        ingest["Ingestion<br/><i>python -m rag.ingest</i>"]
        pdf[("data/corpus<br/>PDF")]
    end

    geo["API Géo"]
    ofgl["OFGL"]

    ca --> web
    web -- "HTTP / JSON" --> api
    api --> rag
    api --> agent
    agent -- "règles du corpus" --> rag
    rag --> chroma
    rag --> ollama
    agent --> ollama
    agent -- "lecture seule" --> geo
    agent -- "lecture seule" --> ofgl
    agent -- "audit, notes validées" --> pg
    pdf --> ingest --> chroma
    ingest --> ollama
```

- Le fournisseur de modèle est une interface (`LLMProvider`) : `LLM_PROVIDER=azure_openai` bascule sur Azure sans toucher au reste ([ADR 0004](adr/0004-fournisseur-azure-et-index-vectoriel.md)).
- Sans PostgreSQL, l'API démarre quand même : `/ask` fonctionne, `/analyses` répond 503.

## Niveau 2 : conteneurs, sur Azure (cible écrite, non déployée)

```mermaid
flowchart LR
    ca(["👤 Chargé d'affaires"])
    gh["GitHub Actions<br/><i>lint, tests, contrôle d'évaluation,<br/>image Docker</i>"]
    ghcr[("GitHub Container Registry<br/><i>image publique de l'API</i>")]

    subgraph rg["Groupe de ressources Azure, UE (Terraform, ADR 0003)"]
        aca["<b>Container App</b><br/>API FastAPI<br/><i>scale à zéro,<br/>identité managée</i>"]
        aoai["Azure OpenAI<br/><i>chat + text-embedding-3-small,<br/>DataZoneStandard UE</i>"]
        search[("Azure AI Search<br/><i>niveau gratuit,<br/>vecteurs (hybride à tester)</i>")]
        blob[("Blob Storage<br/><i>PDF du corpus</i>")]
        obs["Log Analytics +<br/>Application Insights"]
    end

    ca -- "HTTPS" --> aca
    gh -- "push" --> ghcr
    ghcr -- "image" --> aca
    aca -- "rôle : OpenAI User" --> aoai
    aca -- "rôle : lecture de l'index" --> search
    aca -- "rôle : lecture des blobs" --> blob
    aca -- "traces, journaux" --> obs
```

- **Aucune clé** : authentification par clé désactivée partout ; l'API utilise son identité managée avec trois rôles en lecture ou appel seulement.
- **Coûts** : fenêtre gratuite, budget avec alertes, `terraform destroy` après chaque session ([ADR 0001](adr/0001-budget-zero-euro.md)).
- **Pas encore dans la cible** : PostgreSQL managé (l'agent reste donc local pour l'instant), hébergement du front, Entra ID devant l'API, Key Vault (aucun secret à y mettre tant que tout passe par l'identité managée). Voir [securite.md](securite.md) et [limites.md](limites.md).

## Flux d'une question (RAG)

```mermaid
sequenceDiagram
    actor U as Chargé d'affaires
    participant A as API /ask
    participant V as Index vectoriel
    participant M as Modèle
    U->>A: question (≤ 1 000 caractères)
    A->>V: 4 passages les plus proches
    V-->>A: passages + distances
    alt aucun passage sous le seuil (0,43)
        A-->>U: « Je ne trouve pas l'information dans les documents. »
    else
        A->>M: question + extraits balisés (balises extrait)
        M-->>A: réponse avec [1], [2]…
        Note over A: citations vérifiées par le code, liens retirés,<br/>refus si aucune citation valide
        A-->>U: réponse + sources (fichier, page)
    end
```

## Flux d'une pré-analyse (agent)

```mermaid
flowchart TD
    req["Demande en texte libre"] --> ex["extract_request<br/><i>modèle, JSON validé ;<br/>montant lu par le code</i>"]
    ex --> fc["find_commune<br/><i>API Géo</i>"]
    fc --> gf["get_finances<br/><i>OFGL</i>"]
    gf --> ci["compute_indicators<br/><i>calcul, seuils d'alerte</i>"]
    ci --> sr["search_rules<br/><i>RAG</i>"]
    sr --> dn["draft_note<br/><i>modèle : 2-3 phrases citées ;<br/>chiffres calculés par le code</i>"]
    dn --> hr{{"human_review<br/><i>interrupt : rien n'est écrit avant</i>"}}
    hr --> rd["record_decision<br/><i>relecteur, action, commentaire</i>"]
    rd -- "approuver / corriger" --> save["save_note<br/><i>seule écriture</i>"]
    rd -- "rejeter" --> stop["fin, sans écriture"]
    audit[("Journal d'audit<br/>append-only")]
    ex & fc & gf & ci & sr & dn & rd & save -.-> audit
```

Chaque étape est tracée (entrée, sortie, durée, statut) ; la décision humaine aussi (relecteur, action, commentaire). Détails : [ADR 0005](adr/0005-agent-de-pre-analyse.md).
