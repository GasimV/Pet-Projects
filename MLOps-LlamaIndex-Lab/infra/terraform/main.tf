# =============================================================================
# MLOps-LlamaIndex-Lab — Terraform Configuration
# =============================================================================
# Manages the local Docker infrastructure for the RAG application.
#
# Usage:
#   cd infra/terraform
#   terraform init
#   terraform plan
#   terraform apply
#   terraform destroy
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# ── Provider ─────────────────────────────────────────────────────────────────

provider "docker" {
  # On Windows with Docker Desktop, the default works automatically.
  # On Linux you may need: host = "unix:///var/run/docker.sock"
}

# ── Network ──────────────────────────────────────────────────────────────────

resource "docker_network" "rag_network" {
  name = "rag-network-tf"
}

# ── Qdrant Vector Database ──────────────────────────────────────────────────

resource "docker_image" "qdrant" {
  name         = "qdrant/qdrant:v1.13.2"
  keep_locally = true
}

resource "docker_container" "qdrant" {
  name  = "llamaindex-qdrant-tf"
  image = docker_image.qdrant.image_id

  ports {
    internal = 6333
    external = 6333
  }
  ports {
    internal = 6334
    external = 6334
  }

  volumes {
    host_path      = abspath("${path.module}/../../data/qdrant")
    container_path = "/qdrant/storage"
  }

  networks_advanced {
    name = docker_network.rag_network.id
  }

  restart = "unless-stopped"
}

# ── RAG Application ─────────────────────────────────────────────────────────

resource "docker_image" "app" {
  name = "llamaindex-lab-app:latest"

  build {
    context    = abspath("${path.module}/../..")
    dockerfile = "Dockerfile"
  }
}

resource "docker_container" "app" {
  name  = "llamaindex-app-tf"
  image = docker_image.app.image_id

  ports {
    internal = 8000
    external = 8000
  }

  volumes {
    host_path      = abspath("${path.module}/../../data/uploads")
    container_path = "/app/data/uploads"
  }

  env = [
    "QDRANT_HOST=llamaindex-qdrant-tf",
    "QDRANT_PORT=6333",
    "LLM_PROVIDER=${var.llm_provider}",
    "LLM_MODEL=${var.llm_model}",
    "LLM_API_BASE=${var.llm_api_base}",
    "EMBEDDING_PROVIDER=${var.embedding_provider}",
    "EMBEDDING_MODEL=${var.embedding_model}",
    "CHUNK_SIZE=${var.chunk_size}",
    "CHUNK_OVERLAP=${var.chunk_overlap}",
  ]

  networks_advanced {
    name = docker_network.rag_network.id
  }

  depends_on = [docker_container.qdrant]
  restart    = "unless-stopped"
}
