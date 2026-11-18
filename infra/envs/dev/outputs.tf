output "api_url" {
  value = module.api.url
}

output "openai_endpoint" {
  value = module.openai.endpoint
}

output "search_endpoint" {
  value = module.search.endpoint
}

output "resource_group" {
  value = azurerm_resource_group.this.name
}
