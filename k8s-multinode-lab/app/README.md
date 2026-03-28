# k8s-multinode-lab Application Guide

This directory contains a small, educational microservices application designed for the existing kubeadm-based lab cluster in this repository.

The application uses:

- `frontend`: nginx serving a static UI and proxying API traffic
- `backend`: FastAPI serving `/health` and `/visits`
- `redis`: visit counter storage
- `log-sidecar`: a BusyBox sidecar that tails backend logs from a shared volume

The manifests are intentionally simple, plain YAML, and sized for a small VirtualBox lab cluster with containerd.

## 1. Prerequisites

Before using this application, make sure your lab already has:

- a working kubeadm cluster
- containerd running on the nodes
- Flannel or another CNI already installed
- `kubectl` configured on the control-plane node
- enough free resources for:
  - 1 frontend pod
  - 2 backend pods
  - 1 Redis pod

Recommended cluster context for this repo:

- control-plane: `ubuntu-k8s-lab` (`192.168.56.102`)
- worker: `k8s-worker-1` (`192.168.56.101`)

## 2. Directory Layout

```text
app/
├── README.md
├── backend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py
├── frontend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── nginx.conf
│   └── html/
│       ├── app.js
│       ├── index.html
│       └── style.css
└── k8s/
    ├── 00-namespace.yaml
    ├── 10-backend-configmap.yaml
    ├── 20-redis.yaml
    ├── 30-backend.yaml
    ├── 40-frontend.yaml
    └── optional/
        └── 50-backend-hpa.yaml
```

## 3. Build the Images

Do the image build on an Ubuntu VM or another Linux environment later. Do not build from this repository session.

From the repository root:

```bash
docker build -t k8s-lab-backend:1.0.0 ./app/backend
docker build -t k8s-lab-frontend:1.0.0 ./app/frontend
```

If you prefer `nerdctl` instead of Docker, use:

```bash
nerdctl build -t k8s-lab-backend:1.0.0 ./app/backend
nerdctl build -t k8s-lab-frontend:1.0.0 ./app/frontend
```

## 4. Load Images into containerd for kubeadm Labs

Because this lab uses containerd, the cluster nodes need the application images in the `k8s.io` containerd namespace.

### Option A: Build with Docker, then import into containerd

Save the images:

```bash
docker save -o k8s-lab-backend_1.0.0.tar k8s-lab-backend:1.0.0
docker save -o k8s-lab-frontend_1.0.0.tar k8s-lab-frontend:1.0.0
```

Copy the tar files to every node that may run workloads. In this lab, importing to both VMs is the safest option:

```bash
scp k8s-lab-backend_1.0.0.tar ubuntu@192.168.56.102:~/
scp k8s-lab-frontend_1.0.0.tar ubuntu@192.168.56.102:~/
scp k8s-lab-backend_1.0.0.tar ubuntu@192.168.56.101:~/
scp k8s-lab-frontend_1.0.0.tar ubuntu@192.168.56.101:~/
```

Import on each node:

```bash
sudo ctr -n k8s.io images import ~/k8s-lab-backend_1.0.0.tar
sudo ctr -n k8s.io images import ~/k8s-lab-frontend_1.0.0.tar
sudo ctr -n k8s.io images ls | grep k8s-lab
```

### Option B: Build directly with nerdctl on a node

If `nerdctl` is installed on the node:

```bash
sudo nerdctl --namespace k8s.io build -t k8s-lab-backend:1.0.0 ./app/backend
sudo nerdctl --namespace k8s.io build -t k8s-lab-frontend:1.0.0 ./app/frontend
```

## 5. Step-by-Step Deployment Guide

Apply the manifests in order from the repository root:

```bash
kubectl apply -f app/k8s/00-namespace.yaml
kubectl apply -f app/k8s/10-backend-configmap.yaml
kubectl apply -f app/k8s/20-redis.yaml
kubectl apply -f app/k8s/30-backend.yaml
kubectl apply -f app/k8s/40-frontend.yaml
```

Optional autoscaling:

```bash
kubectl apply -f app/k8s/optional/50-backend-hpa.yaml
```

Wait for the pods to become ready:

```bash
kubectl get pods -n lab-demo -w
```

## 6. Verification Commands

Check the main resources:

```bash
kubectl get all -n lab-demo
kubectl get pods -n lab-demo -o wide
kubectl get svc -n lab-demo
```

Check the backend logs:

```bash
kubectl logs -n lab-demo deploy/backend -c backend --tail=20
kubectl logs -n lab-demo deploy/backend -c log-sidecar --tail=20
```

Check the backend service from inside the cluster:

```bash
kubectl run tmp-curl --rm -it --restart=Never -n lab-demo \
  --image=curlimages/curl:8.9.1 -- \
  curl http://backend-service:8000/health
```

Check the frontend from your host machine or from a VM:

```bash
curl http://192.168.56.101:30080
curl http://192.168.56.101:30080/api/health
curl http://192.168.56.101:30080/api/visits
```

Expected result:

- the UI loads in a browser
- `/api/health` returns HTTP `200` when Redis is reachable
- repeated `/api/visits` calls increment the counter
- backend logs appear in both the app container and the log sidecar output

## 7. Cleanup Commands

Delete the optional HPA first if you applied it:

```bash
kubectl delete -f app/k8s/optional/50-backend-hpa.yaml --ignore-not-found
```

Remove the whole application by deleting the namespace:

```bash
kubectl delete namespace lab-demo
```

If you also want to clean the local images from a node later:

```bash
sudo ctr -n k8s.io images rm docker.io/library/k8s-lab-backend:1.0.0
sudo ctr -n k8s.io images rm docker.io/library/k8s-lab-frontend:1.0.0
```

## 8. What Each Kubernetes Manifest Does

- `00-namespace.yaml`: creates the dedicated `lab-demo` namespace
- `10-backend-configmap.yaml`: stores backend environment variables
- `20-redis.yaml`: creates the Redis `ClusterIP` service and single-replica deployment
- `30-backend.yaml`: creates the backend `ClusterIP` service and a deployment with:
  - two backend replicas
  - a shared `emptyDir` log volume
  - a logging sidecar
  - readiness and liveness probes
- `40-frontend.yaml`: creates the frontend deployment and a `NodePort` service on `30080`
- `optional/50-backend-hpa.yaml`: adds autoscaling for the backend if metrics-server exists

## 9. Design Notes for This Lab

This application is designed to run completely on the current two-VM setup:

- frontend, backend, and Redis can all run on `k8s-worker-1`
- the control-plane node does not need to run workloads
- no dynamic storage provisioner is required

It is also easy to extend later:

- if you add `k8s-worker-2`, Redis is the easiest workload to pin there
- if you add persistent storage later, Redis can be migrated from `Deployment + emptyDir` to `StatefulSet + PVC`
- the backend already uses labels and anti-affinity preferences that scale cleanly to more nodes

## 10. Troubleshooting

### Pods stuck in `ImagePullBackOff`

The images were not imported into the node's containerd image store, or the tag does not match the manifest.

Check:

```bash
sudo ctr -n k8s.io images ls | grep k8s-lab
kubectl describe pod -n lab-demo <pod-name>
```

### Backend readiness probe fails

The backend readiness check depends on Redis. If Redis is not ready yet, the backend will stay unready until Redis responds.

Check:

```bash
kubectl get pods -n lab-demo
kubectl logs -n lab-demo deploy/redis
kubectl logs -n lab-demo deploy/backend -c backend --tail=50
```

### Frontend loads but API calls fail

This usually means one of these:

- backend service is not ready
- nginx proxy target does not resolve because the backend service is missing
- backend cannot reach Redis

Check:

```bash
kubectl get svc -n lab-demo
kubectl get endpoints -n lab-demo
kubectl logs -n lab-demo deploy/frontend --tail=20
kubectl logs -n lab-demo deploy/backend -c backend --tail=50
```

### Log sidecar looks empty

The backend writes logs only when requests arrive. Generate a few requests first, then check the sidecar:

```bash
curl http://192.168.56.101:30080/api/visits
kubectl logs -n lab-demo deploy/backend -c log-sidecar --tail=50
```

## 11. Suggested Link from the Root README

The root `README.md` should remain focused on the cluster lab. If you want a small link there later, add something like:

```md
## Sample Application

For the hands-on microservices deployment used in this lab, see [app/README.md](app/README.md).
```
