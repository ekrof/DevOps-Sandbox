terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
  backend "azurerm" {
    use_oidc         = true
    use_azuread_auth = true
  }
}

provider "azurerm" {
  features {}
  use_oidc                        = true
  resource_provider_registrations = "none"
}

variable "environment" {
  type = string
}

locals {
  config = yamldecode(file("${path.module}/../config-${var.environment}.yaml")).terraform
}

# Free resource standing in for the real platform: editing config-<env>.yaml tags changes
# only that environment's plan.
resource "azurerm_user_assigned_identity" "demo" {
  name                = "id-ipp-demo-${var.environment}"
  resource_group_name = "rg-ipp-${var.environment}"
  location            = "norwayeast"
  tags                = merge(local.config.tags, { environment = var.environment })
}
