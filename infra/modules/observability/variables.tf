variable "name" {
  description = "Prefix for the Log Analytics workspace and Application Insights names."
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "daily_quota_gb" {
  type    = number
  default = 0.1
}

variable "tags" {
  type    = map(string)
  default = {}
}
