# ADR 0007 — Portabilité : poste local, serveur d'entreprise ou Azure

- **Statut** : accepté
- **Date** : 2026-11-22

## Contexte
La vérification de l'essai gratuit Azure ([ADR 0001](0001-budget-zero-euro.md), mise à jour du 2026-11-22) montre qu'aucun modèle d'IA Azure n'est utilisable sans paiement à l'usage. Le déploiement Azure dépend donc d'un choix de budget. Par ailleurs, une banque publique peut légitimement préférer garder ses données dans son propre système d'information, et la contrainte principale en local est la puissance de calcul (environ 20 s par réponse sur CPU).

## Décision
Présenter le projet comme **portable sur trois cibles**, avec pour chacune le niveau de preuve réel :

| Cible | Modèle et embeddings | Index | Base | API | Statut |
| --- | --- | --- | --- | --- | --- |
| Poste local | Ollama sur CPU | Chroma (fichiers) | PostgreSQL (Docker) | `uvicorn` | **Testé** (démo, évaluation, CI) |
| Serveur d'entreprise | Ollama ou serveur de modèles sur GPU, via `OLLAMA_BASE_URL` | Chroma sur volume persistant | PostgreSQL de l'organisation | image Docker de l'API | Même code et image de l'API, configuration par variables d'environnement ; image du front et `docker compose` complet à ajouter |
| Azure | Azure OpenAI | Azure AI Search | PostgreSQL à ajouter | Container Apps | **Prêt à déployer** : Terraform validé, code testé avec des doublures |

La portabilité tient à trois choix déjà faits : l'interface `LLMProvider`, l'interface du magasin vectoriel (`VECTOR_STORE`), et la configuration entièrement par variables d'environnement, sans secret dans le code.

## Quand choisir quoi
- **Serveur d'entreprise** : données sensibles qui ne doivent pas sortir, volume d'usage stable (coût fixe), compétences d'exploitation disponibles. Il faut un GPU pour des modèles de 8 à 30 milliards de paramètres.
- **Azure** : pas de matériel à acheter, modèles plus puissants payés au jeton, identité (Entra ID), supervision et gouvernance prêtes, données traitées dans une région de l'UE.
- **Poste local** : développement, évaluation, démonstration.

## Conséquences
- (+) Le projet se défend dans les deux scénarios courants d'une organisation publique, et l'évaluation chiffrée (Phase 5) sert aux deux.
- (+) Pas de dépendance à un déploiement Azure pour valider l'architecture.
- (−) Les deux cibles non locales sont validées à blanc : on écrit « prêt à déployer » ou « validé à blanc », et jamais de formule laissant croire qu'un déploiement a eu lieu.
- (−) Une qualité supérieure ne vient pas de la cible mais du modèle : sur nos 8 échecs, seuls 2 dépendent de sa taille (voir [évaluation](../evaluation.md)) ; la recherche hybride et le découpage comptent autant.
- Pour rendre la cible « serveur d'entreprise » vérifiable à 0 € : un `docker compose` complet (API, front, base, Ollama) à tester sur le poste. Non fait.
