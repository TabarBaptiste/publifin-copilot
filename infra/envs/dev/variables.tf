variable "project" {
  type    = string
  default = "publifin"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "location" {
  description = "EU region (GDPR). Check model availability there before applying."
  type        = string
  default     = "swedencentral"
}

variable "api_image" {
  description = "API image, e.g. ghcr.io/<owner>/publifin-api:<tag> (public GHCR: no registry to pay for)."
  type        = string
}

variable "chat_model" {
  type = object({ name = string, version = string, capacity = number })
  default = {
    name     = "gpt-4o-mini"
    version  = "2024-07-18"
    capacity = 10
  }
}

variable "embedding_model" {
  type = object({ name = string, version = string, capacity = number })
  default = {
    name     = "text-embedding-3-small"
    version  = "1"
    capacity = 10
  }
}

variable "search_sku" {
  type    = string
  default = "free"
}

variable "budget_amount" {
  description = "Monthly budget (in the subscription currency) that triggers e-mail alerts."
  type        = number
  default     = 5
}

variable "budget_start_date" {
  description = "First day of the current month, e.g. 2026-12-01T00:00:00Z (Azure refuses a past month)."
  type        = string
}

variable "alert_emails" {
  description = "Who receives budget alerts. Set it in terraform.tfvars (not committed)."
  type        = list(string)
}
