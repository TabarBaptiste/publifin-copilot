# Limites connues et points à observer

Ce qui est vrai aujourd'hui (2026-11-18) et qu'il faudra surveiller ou lever. Chaque point renvoie vers le document qui le détaille. À relire avant la Phase 5 (évaluation) et avant la fenêtre Azure.

## Recherche et réponses (RAG)
- **Peu de questions de test** : 17 questions, une seule exécution par réglage. Les chiffres donnent un ordre de grandeur, pas une preuve. → [evaluation.md](evaluation.md), [eval/README.md](../eval/README.md)
- **Seuil de pertinence fragile** : `max_distance = 0,43`, réglé pour `bge-m3` ; les meilleures questions à réponse sont à 0,418 et la première question piège à 0,448. À recalibrer avec plus de questions et avec chaque nouveau modèle d'embeddings.
- **Échecs connus à 2 extraits** : `cnil-01` (la fiche « sécurité » de la CNIL n'est pas retrouvée), `aiact-01` (amende de l'AI Act : « 7 % » oublié et mélangé avec l'amende des institutions), `rgpd-04` (faux négatif : mot-clé trop strict).
- **Latence** : ~12 s en médiane à chaud, 20 à 30 s à froid, mais 65 s observées une fois dans le navigateur sans cause mesurée. La CPU est le facteur limitant ; `top_k = 2` est un compromis.
- **Prompt réglé pour un seul modèle** (`qwen3:4b-instruct`). À revérifier avec `gpt-4o-mini`. Une réponse sans citation valide est refusée, ce qui peut gonfler le taux de refus.

## Corpus
- **Manque** : procédures de prêt, critères d'éligibilité, Code général des collectivités territoriales. Les questions de procédure sont donc des questions pièges. → [corpus.md](corpus.md)
- **Licences de réutilisation non confirmées** ; les PDF restent hors du dépôt.
- **Années différentes** : OFGL (2024) et Cour des comptes (2025) peuvent donner des chiffres différents pour un même indicateur.
- **PDF illisible** : le bulletin DGCL BIS 211 demande un OCR (non fait).

## Agent de pré-analyse
- **Paragraphe d'appréciation** écrit par un petit modèle : parfois maladroit ou ambigu (« 7,2 % dépasse le seuil d'alerte de 7 % »), seuils parfois mal appliqués avant correction du prompt. La validation humaine le couvre ; à mesurer en Phase 5. → [ADR 0005](adr/0005-agent-de-pre-analyse.md)
- **Relecteur non authentifié** : le nom est saisi à la main, il n'est pas une preuve d'identité (Entra ID en Phase 6).
- **Périmètre des chiffres** : budget principal des communes uniquement (pas les budgets annexes), dernière année publiée. La population de l'API Géo et celle de l'OFGL diffèrent légèrement.
- **Homonymes** : la commune la plus peuplée est retenue et signalée dans la note. Pas de choix proposé au relecteur.
- **Montants** : seul le premier montant de la demande est lu ; le budget de tokens est estimé (1 token ≈ 3,5 caractères).
- **Redémarrage de l'API** : une analyse en attente de validation est conservée (checkpoints PostgreSQL), une analyse en cours de calcul est marquée « interrompue ». Pas de liste des analyses dans l'interface.
- **Variante Semantic Kernel** : non faite (étape facultative).
- **Base locale** : identifiants de développement uniquement ; elle contient des notes de test (Bastia, Quimper).

## Azure (rien n'a été exécuté contre un vrai compte)
- **Jamais appelé pour de vrai** : fournisseur Azure OpenAI, index AI Search, `terraform plan/apply`. → [ADR 0003](adr/0003-infrastructure-azure-minimale.md), [ADR 0004](adr/0004-fournisseur-azure-et-index-vectoriel.md)
- **À vérifier au premier essai** : formule du score AI Search (distance = (1 − score) / score), analyseur `fr.microsoft`, rôles sur le niveau gratuit d'AI Search, disponibilité des modèles et de `DataZoneStandard` dans la région, accès à Azure OpenAI sur un compte d'essai, conditions actuelles de l'essai gratuit.
- **Pas encore faits** : recherche hybride, comparaison local / cloud, recalibrage du seuil, authentification OIDC de la CI, déploiement automatique.
- **Scale à zéro** : la première requête après une pause attend le démarrage du conteneur.

## Sécurité et conformité (Phase 6, voir `docs/securite.md`)
- **Injection de prompt** : 9 attaques testées, 7 bloquées. Restent possibles un mot imposé dans la note de l'agent par un extrait piégé, et une commune falsifiée par l'auteur de la demande ; la validation humaine les couvre. Une exécution par attaque : pas une garantie.
- **Pas d'authentification** sur l'API ; CORS limité à `localhost:3000`. Pas de filtrage des documents par rôle.
- **Le journal d'audit conserve le texte des demandes** : durée de conservation proposée (12 mois pour le texte libre) mais non implémentée ; pas de masquage des données personnelles.

## Processus
- **La CI ne lance pas l'évaluation RAG** (elle demande Ollama) : elle vérifie seulement les résultats commités (`scripts/check_eval.py`). Pas de `terraform plan` en CI.
- **Piège Windows avec uv** : voir `CLAUDE.md`.
- **Le front de développement** utilise l'API sur `NEXT_PUBLIC_API_URL` (par défaut le port 8000) : redémarrer l'API pour prendre le nouveau code.
