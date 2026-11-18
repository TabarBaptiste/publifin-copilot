variable "name" {
  description = "Storage account name: 3-24 lowercase letters and digits, globally unique."
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "containers" {
  description = "Private blob containers to create."
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
