# 🧪 Kubernetes Lab – From Scratch to Working Multi-Node Cluster

## 📌 Overview

This project documents my hands-on journey of building a **multi-node Kubernetes cluster using kubeadm** inside VirtualBox VMs on a Windows host.

It includes:
- Full setup steps
- Real debugging scenarios
- Common Kubernetes issues and fixes
- Final working cluster with deployed application

---

# 💻 Environment

| Component | Details |
|----------|--------|
| Host OS | Windows |
| Hardware | 64 GB RAM, i7 CPU, SSD |
| Virtualization | VirtualBox |
| Guest OS | Ubuntu 24.04 LTS |
| Kubernetes | kubeadm-based cluster |
| Container Runtime | containerd |

---

# 🖥️ Cluster Architecture

### Control Plane
- Hostname: `ubuntu-k8s-lab`
- IP: `192.168.56.102`

### Worker Node
- Hostname: `k8s-worker-1`
- IP: `192.168.56.101`

### Network Setup
- Adapter 1: NAT (internet)
- Adapter 2: Host-only (`192.168.56.0/24`)

---

# ⚙️ Initial Setup

## On BOTH nodes

### Disable swap
```bash
sudo swapoff -a
```

### Enable kernel modules

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

### Configure sysctl

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sudo sysctl --system
```

---

# 📦 Install containerd

```bash
sudo apt update
sudo apt install -y containerd
```

---

# 📦 Install Kubernetes tools

```bash
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

---

# ❌ Major Issue #1 – Wrong IP (CRITICAL)

## Problem

Cluster initialized with NAT IP (`10.0.2.x`) instead of host-only IP.

## Symptoms

* API server unstable
* kube-proxy CrashLoopBackOff
* flannel failed
* worker join failed

## Root Cause

Wrong `--apiserver-advertise-address`

## Fix

Full reset:

```bash
sudo kubeadm reset -f
sudo systemctl restart containerd
sudo rm -rf /etc/cni/net.d
sudo iptables -F
sudo iptables -t nat -F
```

---

# 🚀 Correct Cluster Initialization

## Set node IP

```bash
echo 'KUBELET_EXTRA_ARGS=--node-ip=192.168.56.102' | sudo tee /etc/default/kubelet
sudo systemctl restart kubelet
```

---

## Initialize cluster

```bash
sudo kubeadm init \
  --apiserver-advertise-address=192.168.56.102 \
  --pod-network-cidr=10.244.0.0/16
```

---

## Configure kubectl

```bash
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
```

---

# ❌ Major Issue #2 – Control Plane Crash Loop

## Symptoms

* kube-apiserver exiting
* controller-manager crashing
* connection refused errors

## Root Cause

containerd misconfiguration (cgroup mismatch)

---

# 🔧 Fix – containerd Configuration

## Generate config

```bash
containerd config default | sudo tee /etc/containerd/config.toml
```

---

## Critical Fixes

### ❌ WRONG

```toml
systemd_cgroup = true
```

### ✅ CORRECT

```toml
systemd_cgroup = false
```

### ✅ REQUIRED

```toml
SystemdCgroup = true
```

### Fix pause image

```toml
sandbox_image = "registry.k8s.io/pause:3.9"
```

---

## Restart services

```bash
sudo systemctl restart containerd
sudo systemctl restart kubelet
```

---

# 🌐 Install Flannel (CNI)

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

---

# 🟢 Cluster Becomes Healthy

```bash
kubectl get nodes
```

Result:

```
ubuntu-k8s-lab   Ready
```

---

# ➕ Add Worker Node

## On worker

```bash
echo 'KUBELET_EXTRA_ARGS=--node-ip=192.168.56.101' | sudo tee /etc/default/kubelet
```

---

## Join cluster

```bash
sudo kubeadm join 192.168.56.102:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

---

## Verify

```bash
kubectl get nodes -o wide
```

Result:

```
ubuntu-k8s-lab   Ready
k8s-worker-1     Ready
```

---

# 🚀 Deploy First Application

## Create deployment

```bash
kubectl create deployment nginx --image=nginx
```

## Expose service

```bash
kubectl expose deployment nginx --port=80 --type=NodePort
```

---

## Get service

```bash
kubectl get svc
```

Example:

```
NodePort: 30522
```

---

## Access app

```bash
curl http://192.168.56.101:30522
```

Result:

```
Welcome to nginx!
```

---

# ❌ Minor Issue – kube-proxy Crash

## Symptoms

* kube-proxy on worker restarting

## Fix

```bash
kubectl delete pod -n kube-system -l k8s-app=kube-proxy
```

---

# 🟢 Final Cluster State

* 2 nodes (control + worker)
* Flannel networking working
* CoreDNS running
* Pods scheduled on worker
* NodePort service accessible

---

# 🧠 Key Learnings

## 🔥 Critical Lessons

* Always use correct IP during `kubeadm init`
* Never change node IP after cluster creation
* containerd config is crucial for stability
* CNI is required before cluster becomes usable
* kube-proxy issues can affect networking
* Logs are your best debugging tool

---

## 🧪 Real Debugging Skills Gained

* Analyzed CrashLoopBackOff
* Investigated container runtime issues
* Fixed cgroup mismatch
* Understood Kubernetes control plane components
* Debugged networking layer (CNI)

---

# 🏁 Outcome

Successfully built and debugged a:

✅ Multi-node Kubernetes cluster
✅ Fully working networking (Flannel)
✅ Application deployment (nginx)
✅ Service exposure via NodePort

---

# 🚀 Next Steps

* Deploy multiple replicas
* Learn Services & Ingress
* Use Helm charts
* Deploy real applications (APIs, DBs)
* Explore monitoring (Prometheus, Grafana)

---

# 🙌 Final Note

This project involved real-world Kubernetes issues and debugging scenarios, providing hands-on experience beyond basic setup tutorials.
