# NVIDIA Triton Hands-On Playground

This folder is my personal lab for trying out **NVIDIA Triton Inference Server** and
documenting what I learn while deploying models with it.

Official docs: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html

## What I did

1. **Set up environment**
   - Installed Docker and NVIDIA Container Toolkit so containers can see my GPU.
   - Pulled the Triton container image from NGC.

2. **Prepared a model repository**
   - Cloned the Triton `server` repo and copied the `docs/examples/model_repository`
     folder into this directory as `model_repository/`.
   - This gives a few ready-made demo models to test Triton with.

3. **Started Triton**
   - Ran Triton from Docker, mounting `model_repository/`:

     ```bash
     docker run --gpus=1 --rm \
       -p8000:8000 -p8001:8001 -p8002:8002 \
       -v /path/to/Triton-HandsOn/model_repository:/models \
       nvcr.io/nvidia/tritonserver:<version>-py3 tritonserver --model-repository=/models
     ```

   - Verified the server is healthy with:

     ```bash
     curl http://localhost:8000/v2/health/ready
     ```

4. **First experiments**
   - Sent simple inference requests to one of the sample models (HTTP / gRPC clients).
   - Observed how Triton logs model loading, batching, and requests.

## Folder structure

- `model_repository/` – Models in Triton’s required layout (copied from the official examples at first, later I can add my own).
- `client_examples/` – Scripts or notebooks I use to send requests to Triton.
- `README.md` – This document with my notes and commands.

## Ideas for future experiments

- Add one of my own models (ASR / TTS / classifier) exported to ONNX or TensorRT.
- Try different backends (PyTorch, ONNX Runtime, TensorRT).
- Experiment with:
  - Dynamic batching
  - Multiple models on one server
  - Basic performance testing using Triton tools (Perf Analyzer, Model Analyzer).
- Later: explore deployment on cloud platforms (Vertex AI, SageMaker, etc.) that support Triton.
