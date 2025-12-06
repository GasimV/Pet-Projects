# NVIDIA MPS Hands-On

This directory contains my experiments with **NVIDIA Multi-Process Service (MPS)**,  
which improves GPU utilization when multiple processes share a single GPU.

Official documentation:  
https://docs.nvidia.com/deploy/mps/introduction.html

## What I try in this lab

1. **Starting the MPS control daemon**
   ```bash
   nvidia-cuda-mps-control -d
   ```

2. **Launching multiple CUDA or PyTorch processes** to observe:
   - GPU sharing
   - Reduced context-switch overhead
   - Potential throughput improvements for small‑batch workloads

3. **Monitoring and profiling**
   - `nvidia-smi`
   - Process scheduling behavior
   - GPU memory distribution
   - Latency and throughput impact

4. **Experiments I run**
   - Two simultaneous inference scripts
   - Long-running training + a smaller inference job
   - Comparing MPS ON vs MPS OFF

## Folder structure

- `scripts/` – Small scripts used for GPU load and concurrency testing  
- `experiments/` – Notes, results, logs, and screenshots  

## Future work

- Testing MPS with PyTorch DataLoader multiprocessing  
- Combining Triton + MPS  
- Profiling latency differences with Nsight Systems  
