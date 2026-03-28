# Installation Guide

This document describes the full setup from VirtualBox to Kubernetes cluster.

---

## 🖥️ 1. VirtualBox Setup (Windows 10)

### Requirements

* Virtualization enabled (BIOS)
* VirtualBox + Extension Pack installed

---

## 🧱 2. Create Ubuntu VM

### Recommended Configuration (per VM)

* CPU: 2 cores
* RAM: 6 GB
* Disk: 50 GB (dynamic)

### Network Configuration

* Adapter 1: NAT
* Adapter 2: Host-only Adapter

---

## 🐧 3. Install Ubuntu Server

* Version: 22.04 LTS
* Enable OpenSSH during install

After installation:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## ⚙️ 4. Prepare System for Kubernetes

### Disable Swap

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

---

### Kernel Modules

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

---

### Sysctl Settings

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

sudo sysctl --system
```

---

## 🐳 5. Install Container Runtime (containerd)

```bash
sudo apt install -y containerd

sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
```

Edit config:

```bash
sudo nano /etc/containerd/config.toml
```

Set:

```
SystemdCgroup = true
```

Restart:

```bash
sudo systemctl restart containerd
sudo systemctl enable containerd
```

---

## ☸️ 6. Install Kubernetes Tools

```bash
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo tee /etc/apt/keyrings/kubernetes-apt-keyring.asc

echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.asc] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

---

## 🧠 7. Initialize Cluster (Control Plane)

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

Configure kubectl:

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

---

## 🌐 8. Install Network Plugin (Flannel)

```bash
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

---

## 🔗 9. Add Worker Node

Run the join command from kubeadm output on worker VM:

```bash
kubeadm join <IP> --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

---

## 📊 10. Verify Cluster

```bash
kubectl get nodes
kubectl get pods -A
```

---

## 🐳 11. Install Dev Tools (Optional)

```bash
sudo apt install -y git docker.io
```

---

## ✅ Result

You now have a working multi-node Kubernetes cluster ready for deploying applications.
