import os
import time
import torch

def main():
    pid = os.getpid()
    print(f"[worker] PID = {pid}")
    device = torch.device("cuda:0")

    # simple workload: repeated matrix multiplications
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
