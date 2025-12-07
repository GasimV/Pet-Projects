# NVIDIA MPS Hands-On (Designed for Linux + CUDA GPU)

This lab demonstrates how to enable **NVIDIA Multi-Process Service (MPS)** and
run multiple GPU processes concurrently on a single GPU.

> ⚠ **Important:** NVIDIA MPS is *only supported on Linux and QNX*.  
> It **does not work on Windows** (including WDDM driver mode).  
> To repeat this experiment, use a **Linux machine with a CUDA-enabled GPU**.
>
> Official docs: https://docs.nvidia.com/deploy/mps/introduction.html

---

## 1. Prerequisites (on the Linux machine)

1. Verify GPU + driver:

   ```bash
   nvidia-smi
   ```

2. Check that MPS is installed:

   ```bash
   which nvidia-cuda-mps-control
   ```

3. (Optional) Install PyTorch for GPU workloads:

   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu130
   ```

---

## 2. Start MPS control daemon

```bash
export CUDA_MPS_PIPE_DIRECTORY=/tmp/mps_pipe
export CUDA_MPS_LOG_DIRECTORY=/tmp/mps_log
mkdir -p $CUDA_MPS_PIPE_DIRECTORY
mkdir -p $CUDA_MPS_LOG_DIRECTORY

nvidia-cuda-mps-control -d
```

Verify:

```bash
ps aux | grep mps
```

---

## 3. Create a simple GPU worker

Save under `scripts/gpu_worker.py`:

```python
import os
import time
import torch

def main():
    pid = os.getpid()
    print(f"[worker] PID = {pid}")
    device = torch.device("cuda:0")

    size = 4096
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)

    iters = 10
    start = time.time()
    for i in range(iters):
        c = a @ b
        torch.cuda.synchronize()
        print(f"[worker {pid}] iter {i+1}/{iters} done")
    end = time.time()

    print(f"[worker {pid}] total time: {end - start:.2f} s")

if __name__ == "__main__":
    main()
```

---

## 4. Baseline test (no MPS)

Terminal 1:

```bash
python scripts/gpu_worker.py
```

Terminal 2 (run simultaneously):

```bash
python scripts/gpu_worker.py
```

Observe:

- GPU utilization via `nvidia-smi`
- Total runtime for each worker

---

## 5. MPS test (with GPU sharing enabled)

Check MPS daemon:

```bash
echo get_server_list | nvidia-cuda-mps-control
```

Run both workers again:

Terminal 1:

```bash
python scripts/gpu_worker.py
```

Terminal 2:

```bash
python scripts/gpu_worker.py
```

Observe:

- Improved concurrency
- Smoother GPU utilization
- Possible reduction in total runtime per worker

---

## 6. Stop MPS daemon

```bash
echo quit | nvidia-cuda-mps-control
rm -rf /tmp/mps_pipe /tmp/mps_log
```

---

## 7. Folder structure for this lab

```
Nvidia-MPS-HandsOn/
  ├─ README.md
  ├─ scripts/
  │    └─ gpu_worker.py
  └─ experiments/
       └─ notes.md
```

Use `experiments/notes.md` to log:

- Baseline timings
- MPS timings
- Screenshots from `nvidia-smi`
- Observations on concurrency

---

## 8. Notes

- MPS only works on Linux.
- You can prepare this lab on Windows, commit to GitHub, and later run it on a Linux GPU machine.
- Great for understanding GPU scheduling, multi-process workloads, and CUDA concurrency.

---
