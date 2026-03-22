# =============================================================================
# Outputs — useful information after terraform apply
# =============================================================================

output "app_url" {
  description = "URL to access the RAG application"
  value       = "http://localhost:8000"
}

output "qdrant_url" {
  description = "URL to access the Qdrant dashboard"
  value       = "http://localhost:6333/dashboard"
}

output "qdrant_container_name" {
  description = "Name of the Qdrant Docker container"
  value       = docker_container.qdrant.name
}

output "app_container_name" {
  description = "Name of the application Docker container"
  value       = docker_container.app.name
}

output "network_name" {
  description = "Docker network connecting the services"
  value       = docker_network.rag_network.name
}
