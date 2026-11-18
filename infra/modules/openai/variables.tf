variable "name" {
  description = "Account name, also used as the endpoint subdomain (globally unique)."
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "deployments" {
  description = "Model deployments, keyed by deployment name. Capacity is in thousands of tokens per minute."
  type = map(object({
    model    = string
    version  = string
    capacity = number
  }))
}

variable "tags" {
  type    = map(string)
  default = {}
}
