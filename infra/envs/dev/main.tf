locals {
  name = "${var.project}-${var.environment}"
  # Some Azure names are global (endpoints): a short random suffix avoids collisions.
  unique = "${var.project}${var.environment}${random_string.suffix.result}"
  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

# Safety net for the zero-euro rule: e-mail alerts long before the free credit is used up.
resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-${local.name}"
  resource_group_id = azurerm_resource_group.this.id
  amount            = var.budget_amount
  time_grain        = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  notification {
    threshold      = 50
    operator       = "GreaterThan"
    contact_emails = var.alert_emails
  }

  notification {
    threshold      = 100
    threshold_type = "Forecasted"
    operator       = "GreaterThan"
    contact_emails = var.alert_emails
  }
}

module "openai" {
  source              = "../../modules/openai"
  name                = "oai-${local.unique}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
  deployments = {
    chat = {
      model    = var.chat_model.name
      version  = var.chat_model.version
      capacity = var.chat_model.capacity
    }
    embeddings = {
      model    = var.embedding_model.name
      version  = var.embedding_model.version
      capacity = var.embedding_model.capacity
    }
  }
}

module "search" {
  source              = "../../modules/ai-search"
  name                = "srch-${local.unique}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = var.search_sku
  tags                = local.tags
}

module "storage" {
  source              = "../../modules/storage"
  name                = "st${local.unique}"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  containers          = ["corpus"]
  tags                = local.tags
}

module "observability" {
  source              = "../../modules/observability"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

module "api" {
  source                     = "../../modules/container-app"
  name                       = "ca-${local.name}-api"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = module.observability.log_analytics_workspace_id
  image                      = var.api_image
  tags                       = local.tags
  env = {
    LLM_PROVIDER                  = "azure_openai"
    AZURE_OPENAI_ENDPOINT         = module.openai.endpoint
    AZURE_OPENAI_CHAT_DEPLOYMENT  = "chat"
    AZURE_OPENAI_EMBED_DEPLOYMENT = "embeddings"
    AZURE_SEARCH_ENDPOINT         = module.search.endpoint
    AZURE_STORAGE_BLOB_ENDPOINT   = module.storage.blob_endpoint
  }
  secrets = {
    "applicationinsights-connection-string" = module.observability.app_insights_connection_string
  }
}

# Least privilege for the API identity: call the models, read the index, read the PDFs.
resource "azurerm_role_assignment" "api_openai" {
  scope                = module.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = module.api.principal_id
}

resource "azurerm_role_assignment" "api_search" {
  scope                = module.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = module.api.principal_id
}

resource "azurerm_role_assignment" "api_storage" {
  scope                = module.storage.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = module.api.principal_id
}
