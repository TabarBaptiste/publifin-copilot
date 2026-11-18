# Infrastructure (Terraform)

Choix et compromis : [ADR 0003](../docs/adr/0003-infrastructure-azure-minimale.md). Rien n'est déployé tant que `terraform apply` n'est pas lancé, et il ne doit l'être qu'avec l'accord explicite du propriétaire du projet (règle budget 0 €, [ADR 0001](../docs/adr/0001-budget-zero-euro.md)).

```
modules/            briques réutilisables
  openai/           compte Azure OpenAI + déploiements de modèles (sans clé)
  ai-search/        service AI Search (sans clé)
  storage/          Storage Account + conteneurs privés (sans clé)
  observability/    Log Analytics + Application Insights
  container-app/    environnement + Container App avec identité managée
envs/dev/           assemblage, rôles RBAC, budget avec alertes
```

## Vérifier sans compte Azure (gratuit)
```bash
cd infra && terraform fmt -check -recursive
cd envs/dev && terraform init -backend=false && terraform validate
```

## Déployer (pendant la fenêtre Azure uniquement)
1. `az login`, puis créer une fois le stockage de l'état (groupe `rg-publifin-tfstate`, Storage Account, conteneur `tfstate`).
2. Copier `backend.hcl.example` en `backend.hcl` et `terraform.tfvars.example` en `terraform.tfvars`, puis les compléter (ces fichiers ne sont pas versionnés).
3. `terraform init -backend-config=backend.hcl`, `terraform plan`, relire le plan, puis `terraform apply`.
4. Après la session : `terraform destroy`.
