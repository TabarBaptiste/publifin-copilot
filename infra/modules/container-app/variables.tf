variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "image" {
  description = "Full image reference, e.g. ghcr.io/<owner>/publifin-api:<tag>."
  type        = string
}

variable "port" {
  type    = number
  default = 8000
}

variable "cpu" {
  type    = number
  default = 0.5
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "max_replicas" {
  type    = number
  default = 1
}

variable "env" {
  description = "Plain environment variables (no secrets)."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets, exposed to the container as environment variables (name upper-cased, '-' -> '_')."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
