####################################################
# Given a list of 3 values i, j, k in the variable
# ENTRYPOINT_PARAMS (default 9000, 20000 and 10000),
# create matrices of sizes i x j and j x k, and time
# the multiplication using cpu and gpu.
####################################################

import json
import os
from time import perf_counter

import torch

i, j, k = json.loads(os.environ.get("ENTRYPOINT_PARAMS", "[9000, 20000, 10000]"))

print("Creating matrices")
a = torch.rand(i, j)
b = torch.rand(j, k)

print("Computing matrix multiplication using cpu")
cpu_start = perf_counter()
print(torch.matmul(a, b).size())
cpu_end = perf_counter()
print("Time on cpu:", cpu_end - cpu_start)

print("Moving matrices to gpu")
a = a.cuda()
b = b.cuda()

print("Computing matrix multiplication using gpu")
gpu_start = perf_counter()
print(torch.matmul(a, b).size())
gpu_end = perf_counter()
print("Time on gpu:", gpu_end - gpu_start)
