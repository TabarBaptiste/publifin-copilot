# ADR 0003 — Infrastructure Azure minimale et sans clé

- **Statut** : accepté (écrit et validé à blanc, pas encore déployé)
- **Date** : 2026-11-18

## Contexte
L'infrastructure doit pouvoir être créée puis détruite en une commande pendant la fenêtre gratuite Azure ([ADR 0001](0001-budget-zero-euro.md)), sans aucune clé stockée, et rester réutilisable pour d'autres prototypes.

## Décision
- **Terraform**, provider `azurerm` 4.x, cinq modules réutilisables (`openai`, `ai-search`, `storage`, `observability`, `container-app`) assemblés dans `infra/envs/dev`.
- **Aucune clé** : authentification par clé désactivée sur Azure OpenAI, AI Search et le Storage Account. L'API utilise l'**identité managée** de sa Container App, avec trois rôles en lecture ou appel seulement (`Cognitive Services OpenAI User`, `Search Index Data Reader`, `Storage Blob Data Reader`).
- **Déploiements de modèles `DataZoneStandard`** dans une région de l'UE (`swedencentral`) : les données restent traitées dans la zone UE, contrairement à `GlobalStandard` (argument RGPD).
- **Coûts contenus** : AI Search en niveau `free`, Container App avec **scale à zéro**, quota quotidien de 0,1 Go sur Log Analytics, **budget avec alertes e-mail** (50 % consommé, 100 % prévu) sur le groupe de ressources.
- **Image de l'API sur GitHub Container Registry (public)** au lieu d'Azure Container Registry.
- **État Terraform distant** dans un Storage Account dédié, créé une fois à la main, accès par Entra ID.

## Alternatives écartées
- **Azure Container Registry** : niveau Basic facturé chaque jour ; GHCR public est gratuit et suffit pour une image sans secret.
- **Key Vault dès maintenant** : aucun secret à y mettre tant que tout passe par l'identité managée. La seule valeur sensible (chaîne de connexion Application Insights) est un secret de la Container App. Key Vault sera ajouté au premier vrai secret.
- **Bicep** : équivalent sur Azure, mais Terraform est plus répandu et réutilisable hors Azure.

## Conséquences
- (+) `terraform destroy` supprime tout ; rien ne coûte quand l'application est inutilisée, sauf le stockage (quelques centimes).
- (+) Aucune clé à faire tourner ou à faire fuiter.
- (−) Scale à zéro : la première requête après une pause attend le démarrage du conteneur.
- (−) `terraform plan` n'a pas pu être lancé (il faut un compte Azure) : seuls `fmt` et `validate` sont vérifiés.
- À vérifier à l'ouverture d'Azure : disponibilité des modèles et de `DataZoneStandard` dans la région, rôles RBAC sur le niveau `free` d'AI Search, accès à Azure OpenAI sur un compte d'essai.
