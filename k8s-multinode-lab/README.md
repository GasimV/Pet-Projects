# k8s-multinode-lab

A hands-on Kubernetes learning project built on a multi-node cluster using kubeadm, VirtualBox, and Ubuntu.

## 🚀 Overview

This project demonstrates how to:

* Build a multi-node Kubernetes cluster from scratch
* Deploy a microservices-based application
* Use core Kubernetes primitives (Pods, Deployments, Services, ConfigMaps, Volumes)
* Implement a multi-container (sidecar) pattern

## 🧱 Architecture

The system consists of:

* **Frontend (nginx)** → serves UI and proxies requests
* **Backend (Flask API)** → business logic
* **Redis** → caching layer
* **Sidecar container** → log collection

## 🖥️ Infrastructure

* Virtualization: VirtualBox
* OS: Ubuntu Server 22.04 LTS
* Kubernetes: kubeadm-based cluster
* Container runtime: containerd

## 📦 Kubernetes Components

* Deployments
* Pods (including multi-container pods)
* Services (ClusterIP + NodePort)
* ConfigMaps
* Volumes
* (Optional) Horizontal Pod Autoscaler

## 🧪 Learning Goals

* Understand cluster architecture (control plane + workers)
* Learn kubectl commands
* Debug pods and networking
* Work with YAML manifests
* Implement real-world deployment patterns

## ▶️ Quick Start

```bash
kubectl apply -f k8s/
kubectl get pods -A
kubectl get svc
```

## 🔍 Useful Commands

```bash
kubectl get nodes
kubectl describe pod <pod>
kubectl logs <pod>
kubectl exec -it <pod> -- bash
```

## 📁 Project Structure

```
k8s-multinode-lab/
├── backend/
├── frontend/
├── redis/
├── k8s/
├── docs/
```

## 📚 Next Steps

* Add HPA (autoscaling)
* Add Ingress controller
* Add monitoring (Prometheus + Grafana)

---

💡 This project is designed for learning real-world Kubernetes, not simplified environments.
