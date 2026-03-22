#!/usr/bin/env bash
# =============================================================================
# Register the local GitLab Runner with Docker executor.
#
# Prerequisites:
#   1. GitLab CE must be running and healthy (http://localhost:8929).
#   2. Create a runner token in GitLab:
#        Admin → CI/CD → Runners → New instance runner
#        Copy the token.
#
# Usage:
#   bash infra/gitlab/register-runner.sh <REGISTRATION_TOKEN>
# =============================================================================

set -euo pipefail

TOKEN="${1:?Usage: $0 <REGISTRATION_TOKEN>}"

docker exec -it local-gitlab-runner gitlab-runner register \
  --non-interactive \
  --url "http://local-gitlab" \
  --token "$TOKEN" \
  --executor "docker" \
  --docker-image "python:3.11-slim" \
  --docker-network-mode "gitlab-network" \
  --clone-url "http://local-gitlab" \
  --description "local-docker-runner"

echo ""
echo "Runner registered successfully!"
echo "Check http://localhost:8929/admin/runners to verify."
