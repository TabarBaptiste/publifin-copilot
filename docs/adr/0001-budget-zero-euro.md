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
