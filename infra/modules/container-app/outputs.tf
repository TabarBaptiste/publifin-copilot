output "url" {
  value = "https://${azurerm_container_app.this.ingress[0].fqdn}"
}

output "principal_id" {
  description = "Object id of the app's managed identity, to grant it roles."
  value       = azurerm_container_app.this.identity[0].principal_id
}
