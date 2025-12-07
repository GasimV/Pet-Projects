# NVIDIA MPS Hands-On – Experiment Notes

Use this file to record your observations when running the MPS lab on a Linux + CUDA GPU machine.

## System Info

- Date:
- Machine / Hostname:
- GPU model:
- Driver version:
- CUDA version:
- PyTorch / CUDA toolkit version:

## Baseline (MPS disabled)

Describe how you ran the test (commands, terminals, etc.):

```bash
python scripts/gpu_worker.py
# in another terminal
python scripts/gpu_worker.py
```

### Observations

- Total time (worker 1):
- Total time (worker 2):
- GPU utilization pattern from `nvidia-smi`:
- Any other notes (e.g., CPU load, fan noise, responsiveness):

## With MPS enabled

Commands you used:

```bash
export CUDA_MPS_PIPE_DIRECTORY=/tmp/mps_pipe
export CUDA_MPS_LOG_DIRECTORY=/tmp/mps_log
mkdir -p $CUDA_MPS_PIPE_DIRECTORY $CUDA_MPS_LOG_DIRECTORY
nvidia-cuda-mps-control -d

# In two terminals
python scripts/gpu_worker.py
python scripts/gpu_worker.py
```

### Observations

- Total time (worker 1):
- Total time (worker 2):
- GPU utilization pattern from `nvidia-smi`:
- Any difference compared to baseline:
- Any errors or warnings:

## Summary / Conclusions

- Did MPS improve concurrency or utilization?
- In what scenarios do you think MPS would help the most?
- Any ideas for future experiments (more processes, different workloads, etc.)?
