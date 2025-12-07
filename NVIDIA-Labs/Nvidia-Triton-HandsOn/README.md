# ✅ NVIDIA Triton Hands-On Playground**

This folder contains my hands-on experiment with **NVIDIA Triton Inference Server**, running locally on Windows using Docker.
My GPU (NVIDIA Quadro M1200, 4GB VRAM) is **unsupported** for GPU execution, so Triton falls back to **CPU-only mode** — but everything else works exactly the same, making this a perfect intro lab.

---

# 🧱 1. Folder setup

Inside my repo:

```
E:\Software\GitHub Pet Projects\NVIDIA-Labs\Nvidia-Triton-HandsOn\
```

I created Triton’s required *model repository* structure:

```
model_repository/
    onnx_mnist/
        1/
        config.pbtxt
```

Commands:

```cmd
mkdir model_repository
mkdir model_repository\onnx_mnist
mkdir model_repository\onnx_mnist\1
```

---

# 📥 2. Download a simple ONNX model (MNIST)

Used curl (Windows CMD):

```cmd
curl -L "https://github.com/onnx/models/raw/main/validated/vision/classification/mnist/model/mnist-8.onnx" ^
 -o "model_repository\onnx_mnist\1\model.onnx"
```

This gives a tiny 26 KB MNIST classifier.

---

# ⚙️ 3. Create Triton model config

Opened:

```cmd
notepad model_repository\onnx_mnist\config.pbtxt
```

Inserted the correct input/output shapes (**important**; we fixed errors when Triton validated dimensions):

```text
name: "onnx_mnist"
platform: "onnxruntime_onnx"
max_batch_size: 0

input [
  {
    name: "Input3"
    data_type: TYPE_FP32
    dims: [ 1, 1, 28, 28 ]
  }
]

output [
  {
    name: "Plus214_Output_0"
    data_type: TYPE_FP32
    dims: [ 1, 10 ]
  }
]
```

---

# 🐳 4. Pull Triton Docker image

```cmd
docker pull nvcr.io/nvidia/tritonserver:24.05-py3
```

---

# 🚀 5. Run Triton Server (CPU mode on unsupported GPU)

```cmd
docker run --rm --gpus 1 ^
  -p8000:8000 -p8001:8001 -p8002:8002 ^
  -v "E:/Software/GitHub Pet Projects/NVIDIA-Labs/Nvidia-Triton-HandsOn/model_repository:/models" ^
  nvcr.io/nvidia/tritonserver:24.05-py3 tritonserver --model-repository=/models
```

Triton printed:

```
ERROR: Detected Quadro M1200 GPU, which is not supported by this container
ERROR: No supported GPU(s) detected to run this container
```

This is expected.

Despite that, Triton continues loading the model using **onnxruntime (CPU backend)**:

```
loading: onnx_mnist:1
...
ModelInstanceInitialize: onnx_mnist_0 (CPU device 0)
Ready for inference
```

Leave this terminal window running.

---

# 🧪 6. Verify Triton is running

From a **new** terminal:

### Health check (empty response is OK)

```cmd
curl http://localhost:8000/v2/health/ready
```

### Get model metadata

```cmd
curl http://localhost:8000/v2/models/onnx_mnist
```

Output:

```json
{
  "name": "onnx_mnist",
  "versions": ["1"],
  "platform": "onnxruntime_onnx",
  "inputs": [{"name":"Input3","datatype":"FP32","shape":[1,1,28,28]}],
  "outputs":[{"name":"Plus214_Output_0","datatype":"FP32","shape":[1,10]}]
}
```

---

# 🐍 7. Install Triton Python client

Inside my virtual environment `(nvidia)`:

```cmd
pip install "tritonclient[all]"
```

---

# 🧾 8. Create `mnist_client.py`

Located in:

```
Nvidia-Triton-HandsOn/mnist_client.py
```

Contents:

```python
import numpy as np
import tritonclient.grpc as grpcclient

# Connect to Triton gRPC endpoint
client = grpcclient.InferenceServerClient("localhost:8001")

# Fake MNIST-like input
data = np.random.rand(1, 1, 28, 28).astype(np.float32)

inputs = [grpcclient.InferInput("Input3", data.shape, "FP32")]
inputs[0].set_data_from_numpy(data)

outputs = [grpcclient.InferRequestedOutput("Plus214_Output_0")]

result = client.infer("onnx_mnist", inputs=inputs, outputs=outputs)

output = result.as_numpy("Plus214_Output_0")

print("Triton output shape:", output.shape)
print("Triton output values:", output)
print("Predicted class:", int(output.argmax()))
```

---

# ▶️ 9. Run the Python client

```cmd
python mnist_client.py
```

Output (example):

```
Triton output shape: (1, 10)
Triton output values: [[-0.68 -0.29 -0.88 1.15 -0.27 1.47 -0.64 -2.36 1.21 0.42]]
Predicted class: 5
```

🎉 **Success: Python → Triton → ONNX Model → Prediction**

---

# 📌 Summary

| Step                          | Status       |
| ----------------------------- | ------------ |
| Download ONNX model           | ✅            |
| Create model repository       | ✅            |
| Write correct config.pbtxt    | ✅            |
| Run Triton via Docker         | ✅ (CPU only) |
| Health + metadata check       | ✅            |
| Write Python inference client | ✅            |
| End-to-end inference working  | ✅            |

---

# 📚 What’s Next?

Possible extensions:

* Load a **real MNIST image** instead of random noise
* Try **batch inference**
* Export your own PyTorch model → ONNX → Triton
* Add documentation + screenshots to GitHub
* Try TensorRT backend (CPU-only TensorRT also works!)