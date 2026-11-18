output "id" {
  value = azurerm_storage_account.this.id
}

output "blob_endpoint" {
  value = azurerm_storage_account.this.primary_blob_endpoint
}
