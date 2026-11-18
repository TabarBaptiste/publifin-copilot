variable "name" {
  description = "Search service name (globally unique)."
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "sku" {
  description = "\"free\" (one per subscription, 50 MB, 3 indexes) or \"basic\" (billed)."
  type        = string
  default     = "free"
}

variable "tags" {
  type    = map(string)
  default = {}
}
