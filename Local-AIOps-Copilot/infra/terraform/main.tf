# ─────────────────────────────────────────────────────────
# Terraform configuration for Local-AIOps-Copilot
# ─────────────────────────────────────────────────────────
# Design-level: defines the infrastructure resources needed
# to deploy the platform on a Kubernetes cluster.
# Intended for use with Kubespray + Ansible provisioned clusters.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace for deployment"
  type        = string
  default     = "aiops-copilot"
}

variable "environment" {
  description = "Deployment environment (dev, gpu, production)"
  type        = string
  default     = "dev"
}

variable "enable_gpu" {
  description = "Enable GPU inference backends"
  type        = bool
  default     = false
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

provider "helm" {
  kubernetes {
    config_path = var.kubeconfig_path
  }
}

# ── Namespace ──

resource "kubernetes_namespace" "copilot" {
  metadata {
    name = var.namespace
    labels = {
      app     = "aiops-copilot"
      env     = var.environment
    }
  }
}

# ── Helm Release ──

resource "helm_release" "aiops_copilot" {
  name       = "aiops-copilot"
  chart      = "${path.module}/../helm"
  namespace  = kubernetes_namespace.copilot.metadata[0].name

  values = [
    yamlencode({
      global = {
        environment = var.environment
        llmBackend  = var.enable_gpu ? "vllm" : "mock"
      }
      vllm = {
        enabled = var.enable_gpu
      }
      triton = {
        enabled = var.enable_gpu
      }
    })
  ]

  depends_on = [kubernetes_namespace.copilot]
}

# ── Outputs ──

output "namespace" {
  value = kubernetes_namespace.copilot.metadata[0].name
}

output "gpu_enabled" {
  value = var.enable_gpu
}
