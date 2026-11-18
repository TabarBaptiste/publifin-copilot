resource "azurerm_cognitive_account" "this" {
  name                  = var.name
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = var.name
  # Entra ID only: no API key can be used to call the models.
  local_auth_enabled = false
  tags               = var.tags
}

resource "azurerm_cognitive_deployment" "this" {
  for_each = var.deployments

  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.this.id

  model {
    format  = "OpenAI"
    name    = each.value.model
    version = each.value.version
  }

  sku {
    # DataZoneStandard keeps processing inside the EU data zone (GDPR), unlike GlobalStandard.
    name     = "DataZoneStandard"
    capacity = each.value.capacity
  }
}
