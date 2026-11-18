resource "azurerm_container_app_environment" "this" {
  name                       = "${var.name}-env"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

resource "azurerm_container_app" "this" {
  name                         = var.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  # The app reaches Azure services with this identity: no key or password in its configuration.
  identity {
    type = "SystemAssigned"
  }

  # Secret names are not sensitive, only their values: iterate on the names.
  dynamic "secret" {
    for_each = nonsensitive(toset(keys(var.secrets)))
    content {
      name  = secret.value
      value = var.secrets[secret.value]
    }
  }

  template {
    # Scale to zero: no cost while nobody uses the app (the first request then waits for a cold start).
    min_replicas = 0
    max_replicas = var.max_replicas

    container {
      name   = var.name
      image  = var.image
      cpu    = var.cpu
      memory = var.memory

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = nonsensitive(toset(keys(var.secrets)))
        content {
          name        = upper(replace(env.value, "-", "_"))
          secret_name = env.value
        }
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.port

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
