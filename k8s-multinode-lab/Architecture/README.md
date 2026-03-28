# Architecture Diagrams

This folder contains the PlantUML source files and exported images for the architecture documentation of `k8s-multinode-lab`.

## Diagrams

- `C4_Context.puml`: high-level system context for the sample application and lab cluster
- `C4_Container.puml`: application-level containers and their relationships
- `Deployment.puml`: deployment view mapped to the current kubeadm lab topology

## Current Alignment

The diagrams are aligned with the application under [`app/`](../app/) and reflect:

- nginx frontend exposed through `frontend-service` on NodePort `30080`
- FastAPI backend exposed internally through `backend-service`
- Redis exposed internally through `redis-service`
- backend logging sidecar running in the backend pod, not the frontend pod
- the current two-node lab (`ubuntu-k8s-lab` and `k8s-worker-1`)
- an optional future `k8s-worker-2` as an extension point, not a current requirement

## Important Note About PNG Files

The `.puml` files are the editable source of truth.

If you update a `.puml` file, regenerate the corresponding `.png` file so the rendered images stay in sync. Example workflow on a machine with Java and PlantUML installed:

```bash
plantuml Architecture/C4_Context.puml
plantuml Architecture/C4_Container.puml
plantuml Architecture/Deployment.puml
```

If you prefer Docker-based rendering, regenerate the images later in your Ubuntu environment and commit the updated `.png` files together with the `.puml` source changes.
