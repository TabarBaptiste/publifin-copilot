terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state in a Storage Account created once by hand (see infra/README.md).
  # Settings come from backend.hcl: terraform init -backend-config=backend.hcl
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  # The storage account has account keys disabled: Terraform must use Entra ID for blob operations.
  storage_use_azuread = true
}
