# ADR 0001 — Budget zéro euro : local d'abord, Azure en fenêtre gratuite

- **Statut** : accepté
- **Date** : 2026-11-17

## Contexte
Projet d'entraînement personnel, sans financement. Contrainte forte : **ne dépenser aucun centime**. Le plan initial suppose des ressources Azure payantes (Azure OpenAI, AI Search, Container Apps, PostgreSQL…).

Machine de développement : Ryzen 5 5600H, 16 Go de RAM, Radeon RX 6500M 4 Go (accélération GPU d'Ollama non garantie sur cette puce AMD, CPU probable), ~165 Go de disque libres.

## Décision
1. **Phases 0, 1, 4, 5, 6 en local, à 0 €** : Ollama (modèle de chat quantifié 3B–8B, embeddings `nomic-embed-text`), base vectorielle locale (Chroma ou pgvector), PostgreSQL local, évaluation avec un LLM local comme juge.
2. **Abstraction `LLMProvider`** pour que le code ne dépende pas du fournisseur (Ollama ↔ Azure OpenAI par variable d'environnement).
3. **Terraform écrit et validé sans coût** (`fmt`, `validate`, `plan`). Aucun `apply` sans accord explicite.
4. **Azure uniquement via l'essai gratuit** (crédit ~200 $ sur ~30 jours, à re-vérifier à l'ouverture), en **une seule fenêtre time-boxée** pour les phases 2 et 3 : `apply`, démo enregistrée en vidéo, puis `destroy`.
5. **Jamais de passage en paiement à l'usage.** À la fin du crédit, les ressources sont suspendues plutôt que facturées.
6. GitHub Actions sur dépôt **public** (gratuit).

## Alternatives écartées
- **Azure payant avec alerte de budget** : contraire à la contrainte 0 €.
- **Tout local, jamais Azure** : zéro risque mais moins convaincant pour un projet centré Azure ; conservé comme plan de repli (« IaC validée, non déployée » + démo vidéo locale).

## Conséquences
- (+) Aucun risque de facture ; le projet avance sans attendre Azure.
- (+) L'abstraction `LLMProvider` et l'IaC testée à blanc rendent la bascule cloud rapide.
- (−) Modèles locaux petits : qualité et vitesse inférieures à GPT-4o-mini ; l'évaluation (phase 5) devra le documenter.
- (−) Fenêtre Azure courte : préparer tout en amont pour ne pas gaspiller les 30 jours.
- (−) Une carte bancaire est probablement exigée à l'ouverture du compte (vérification) ; aucune action ne sera prise sans accord de Baptiste.
- À vérifier avant la fenêtre Azure : accès à Azure OpenAI, limites du niveau gratuit d'AI Search, services gratuits uniquement 12 mois.

## Mise à jour du 2026-11-22 : conditions vérifiées

- **Essai gratuit** (page officielle Azure et Microsoft Learn, mise à jour de mars 2026) : 200 $ de crédit pendant 30 jours, un seul essai par client. À la fin du crédit ou des 30 jours, les ressources sont **désactivées** sans facturation, sauf passage volontaire au paiement à l'usage. Le point 5 reste donc tenable.
- **Azure OpenAI : quota de 0 sur un essai gratuit, très probablement.** Plusieurs réponses Microsoft Q&A de 2026 indiquent que les offres « Free Trial », « Azure Pass » et « Lightweight trial » ont 0 jeton par minute pour tous les modèles ; le passage au paiement à l'usage débloque le quota en conservant le crédit restant. La page officielle des quotas ne le dit plus explicitement : à confirmer dans le portail (page Quotas) dès l'ouverture du compte, avant tout `apply`.
- **Conséquence** : la cible Azure complète (Azure OpenAI pour la génération et les embeddings) n'est **pas réalisable sans paiement à l'usage**, que le point 5 interdit. Décision à prendre par Baptiste :
  1. **Rester à 0 € strict** : déployer sur l'essai ce qui n'exige pas de modèle (Container Apps, AI Search gratuit, Log Analytics), et garder la génération en local ; la démo cloud complète reste une vidéo locale (plan de repli prévu ci-dessus).
  2. **Passer au paiement à l'usage** pendant la fenêtre, avec budget et alertes à 5 €, plafonds de quota bas et `destroy` systématique : coût attendu de quelques centimes (environ 0,2 $ pour 1 000 questions, voir `docs/evaluation.md`), mais le risque de facture n'est plus nul.
  3. **Rester à 0 € avec un modèle ouvert hébergé soi-même** : faire tourner Ollama (`qwen3:4b-instruct`, `bge-m3`) dans une Container App, payée par le crédit d'essai et non soumise aux quotas des services d'IA. Limites à vérifier : 4 vCPU et 8 Go au plus par conteneur sur le plan Consommation, donc environ 20 à 40 s par réponse comme en local ; démarrage lent à cause des modèles (~4 Go) ; et ce n'est plus « Azure OpenAI », mais l'abstraction `LLMProvider` le permet déjà (`LLM_PROVIDER=ollama` avec une URL distante).
- **Autres fournisseurs sur Foundry, vérifiés aussi** : les modèles Claude (Anthropic) exigent un abonnement payant avec moyen de paiement actif ; les modèles partenaires en déploiement « serverless » (DeepSeek, Mistral, Llama via Marketplace) excluent explicitement les abonnements gratuits ou d'essai ; les modèles vendus par Azure (OpenAI, DeepSeek, Llama hébergés par Microsoft) suivent le même quota à 0. Aucun modèle de Foundry n'est donc utilisable sur l'essai gratuit.
- **Écartée** : GitHub Models (modèles hébergés sur Azure, gratuits pour le prototypage) a été **fermé le 30 juillet 2026** (documentation GitHub).
- **AI Search gratuit** : un service par abonnement, 50 Mo, 3 index, pas de mise à l'échelle, suppression possible après inactivité. L'index estimé (1 760 morceaux, vecteurs de 1 536 dimensions non stockés en double) fait environ 15 Mo.
- **Modèle prévu** : `gpt-4o-mini` version 2024-07-18 est déprécié, retrait annoncé le 14 avril 2027 ; utilisable pendant la fenêtre, à remplacer ensuite.
