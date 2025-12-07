import numpy as np
import tritonclient.grpc as grpcclient

# Connect to Triton's gRPC endpoint
client = grpcclient.InferenceServerClient("localhost:8001")

# Fake MNIST-style image (batch size = 1)
data = np.random.rand(1, 1, 28, 28).astype(np.float32)

# Prepare Triton input
inputs = []
inputs.append(grpcclient.InferInput("Input3", data.shape, "FP32"))
inputs[0].set_data_from_numpy(data)

# Prepare Triton output
outputs = []
outputs.append(grpcclient.InferRequestedOutput("Plus214_Output_0"))

# Send inference
result = client.infer(
    model_name="onnx_mnist",
    inputs=inputs,
    outputs=outputs
)

# Get output as numpy array
output = result.as_numpy("Plus214_Output_0")

print("Triton output shape:", output.shape)
print("Triton output values:", output)
print("Predicted class:", int(output.argmax()))
