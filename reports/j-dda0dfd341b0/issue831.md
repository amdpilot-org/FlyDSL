# ROCm/FlyDSL issue 831

Title: [Feature]: Intra-kernel profiling
State: open
URL: https://github.com/ROCm/FlyDSL/issues/831
Created: 2026-07-12T06:43:41Z
Updated: 2026-08-17T22:27:53Z
Author: benenzhu

## Description

### Suggestion Description

Intra-kenrel profiling is really useful for communications kernels. 
Also it is useful for compute-bound kernels too, to identify the XCD-imbanlance, and tail effect of some grids.

Some reference for other dsl.
1. cutedsl: https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/cute_dsl_general/iket_profiling.html
2. tilelang: https://github.com/tile-ai/tilelang/pull/2515
3. triton: https://github.com/triton-lang/triton/blob/main/third_party/proton/tutorials/intra_kernel/example_dsl.py
4. flashinfer: https://github.com/flashinfer-ai/flashinfer/pull/913

Also here is a blog for how to use it to identify uneven work distribution in MI300x intra-node all2all implementations: 
https://gau-nernst.github.io/amd-a2a/#intra-kernel-profiling

<img width="2186" height="1162" alt="Image" src="https://github.com/user-attachments/assets/07c1fbb7-1efe-419b-940d-dfa353286b1f" />


### Operating System

_No response_

### GPU

_No response_

### ROCm Component

_No response_

## Comments

### LeiWang1999 at 2026-07-12T12:03:47Z

awesome, and welcome to contribute it into tilelang :)

### coderfeli at 2026-07-13T08:37:24Z

@benenzhu thanks. make sense, we need this feature.
