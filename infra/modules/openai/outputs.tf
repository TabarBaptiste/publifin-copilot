output "id" {
  value = azurerm_cognitive_account.this.id
}

output "endpoint" {
  value = azurerm_cognitive_account.this.endpoint
}

output "deployment_names" {
  value = keys(azurerm_cognitive_deployment.this)
}
