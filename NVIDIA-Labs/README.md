# NVIDIA Experiments

This folder contains hands-on experiments with NVIDIA technologies related to
GPU compute, model serving, and performance optimization.  
Each subfolder documents my experience, commands, results, and challenges while
exploring these tools in real projects.

## Included Projects

### 1. NVIDIA Triton Inference Server (Nvidia-Triton-HandsOn)
Hands-on exploration of deploying and serving models using Triton.  
Topics I document here include:
- Running Triton locally with Docker
- Preparing a model repository
- Sending inference requests (HTTP / gRPC)
- Experimenting with batching, performance tools, and model loading

### 2. NVIDIA Multi-Process Service (Nvidia-MPS-HandsOn)
Experiments with NVIDIA MPS, which allows multiple GPU clients to share the same
GPU more efficiently.  
I document:
- How to enable/disable the MPS control daemon
- Running multiple CUDA processes concurrently
- Testing GPU sharing behaviour
- Observing scheduling, throughput limits, and profiling results

## Future Additions
- TensorRT optimization tests  
- FasterTransformer experiments  
- NeMo ASR / TTS performance profiling  
- GPU memory / concurrency benchmarking  
