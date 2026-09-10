#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Run the gfx950 public-shuffle matrix against an independent host oracle."""

import json
import os
import sys
from pathlib import Path
import numpy as np
import torch
import flydsl.compiler as flyc
import flydsl.expr as fx

WIDTH = 64
SENTINEL = 0x7badbadbadbadbad

@flyc.kernel
def idx_kernel(A: fx.Pointer, C: fx.Pointer, lane: fx.Int32):
    C[fx.thread_idx.x] = fx.shuffle_idx(A[fx.thread_idx.x], lane, WIDTH)

@flyc.kernel
def xor_kernel(A: fx.Pointer, C: fx.Pointer, offset: fx.Int32):
    C[fx.thread_idx.x] = fx.shuffle_xor(A[fx.thread_idx.x], offset, WIDTH)

@flyc.kernel
def up_kernel(A: fx.Pointer, C: fx.Pointer, offset: fx.Int32):
    C[fx.thread_idx.x] = fx.shuffle_up(A[fx.thread_idx.x], offset, WIDTH)

@flyc.kernel
def down_kernel(A: fx.Pointer, C: fx.Pointer, offset: fx.Int32):
    C[fx.thread_idx.x] = fx.shuffle_down(A[fx.thread_idx.x], offset, WIDTH)

@flyc.jit
def launch_idx(A, C, lane, stream: fx.Stream = fx.Stream(None)):
    idx_kernel(A, C, lane).launch(grid=(1,1,1), block=(WIDTH,1,1), stream=stream)

@flyc.jit
def launch_xor(A, C, offset, stream: fx.Stream = fx.Stream(None)):
    xor_kernel(A, C, offset).launch(grid=(1,1,1), block=(WIDTH,1,1), stream=stream)

@flyc.jit
def launch_up(A, C, offset, stream: fx.Stream = fx.Stream(None)):
    up_kernel(A, C, offset).launch(grid=(1,1,1), block=(WIDTH,1,1), stream=stream)

@flyc.jit
def launch_down(A, C, offset, stream: fx.Stream = fx.Stream(None)):
    down_kernel(A, C, offset).launch(grid=(1,1,1), block=(WIDTH,1,1), stream=stream)

def bits_tensor(dtype):
    if dtype == torch.int16:
        raw = np.array([0x8000 | ((lane + 1) & 0x7fff) for lane in range(WIDTH)], dtype=np.uint16)
        return torch.from_numpy(raw).view(torch.int16).cuda()
    if dtype == torch.int32:
        raw = np.array([0x80000000 | (lane + 1) for lane in range(WIDTH)], dtype=np.uint32)
        return torch.from_numpy(raw).view(torch.int32).cuda()
    if dtype == torch.int64:
        raw = np.array([0x8000000000000000 | (lane + 1) for lane in range(WIDTH)], dtype=np.uint64)
        return torch.from_numpy(raw).view(torch.int64).cuda()
    if dtype == torch.float16:
        raw = np.array([0x8000 | ((lane + 1) & 0x7fff) for lane in range(WIDTH)], dtype=np.uint16)
        return torch.from_numpy(raw.copy()).view(torch.int16).view(torch.float16).cuda()
    if dtype == torch.bfloat16:
        raw = np.array([0x8000 | ((lane + 1) & 0x7fff) for lane in range(WIDTH)], dtype=np.uint16)
        return torch.from_numpy(raw.copy()).view(torch.uint16).cuda().view(torch.bfloat16)
    if dtype == torch.float64:
        raw = np.array([0x8000000000000000 | (lane + 1) for lane in range(WIDTH)], dtype=np.uint64)
        return torch.from_numpy(raw.copy()).view(torch.int64).view(torch.float64).cuda()
    raise ValueError(dtype)

def raw_bits(tensor):
    if tensor.dtype == torch.bfloat16:
        return tensor.view(torch.uint16).cpu().numpy().astype(np.uint64).tolist()
    if tensor.dtype == torch.float16:
        return tensor.view(torch.int16).cpu().numpy().astype(np.uint16).astype(np.uint64).tolist()
    if tensor.dtype == torch.float32:
        return tensor.view(torch.int32).cpu().numpy().astype(np.uint32).astype(np.uint64).tolist()
    if tensor.dtype == torch.float64:
        return tensor.view(torch.int64).cpu().numpy().astype(np.uint64).tolist()
    return tensor.cpu().numpy().astype(np.uint64).tolist()

def expected_source(mode, operand, lane=0, offset=0):
    if mode == 'idx':
        return [operand[lane]] * WIDTH
    if mode == 'xor':
        return [operand[lane_id ^ offset] for lane_id in range(WIDTH)]
    if mode == 'up':
        return [operand[lane_id - offset] if lane_id - offset >= 0 else None for lane_id in range(WIDTH)]
    if mode == 'down':
        return [operand[lane_id + offset] if lane_id + offset < WIDTH else None for lane_id in range(WIDTH)]
    raise ValueError(mode)

def run_case(dtype, mode, lane=0, offset=0):
    a = bits_tensor(dtype)
    sentinel = -1 if dtype in (torch.int16, torch.int32, torch.int64) else float('nan')
    c = torch.full((WIDTH,), sentinel, dtype=dtype, device='cuda')
    stream = torch.cuda.Stream()
    ptr_type = {torch.int16: fx.Int16, torch.int32: fx.Int32, torch.int64: fx.Int64,
                torch.float16: fx.Float16, torch.bfloat16: fx.BFloat16,
                torch.float64: fx.Float64}[dtype]
    a_arg = flyc.from_c_void_p(ptr_type, a.data_ptr())
    c_arg = flyc.from_c_void_p(ptr_type, c.data_ptr())
    if mode == 'idx':
        launch_idx(a_arg, c_arg, lane, stream=stream)
    elif mode == 'xor':
        launch_xor(a_arg, c_arg, offset, stream=stream)
    elif mode == 'up':
        launch_up(a_arg, c_arg, offset, stream=stream)
    else:
        launch_down(a_arg, c_arg, offset, stream=stream)
    torch.cuda.synchronize()
    input_bits = raw_bits(a)
    output_bits = raw_bits(c)
    expected = expected_source(mode, input_bits, lane=lane, offset=offset)
    valid = [lane_id for lane_id in range(WIDTH) if expected[lane_id] is not None]
    mismatches = [lane_id for lane_id in valid if output_bits[lane_id] != expected[lane_id]]
    invalid_raw = [output_bits[lane_id] for lane_id in range(WIDTH) if expected[lane_id] is None]
    return {
        'dtype': str(dtype).removeprefix('torch.'),
        'mode': mode,
        'lane': lane,
        'offset': offset,
        'width': WIDTH,
        'input_bits': input_bits,
        'output_bits': output_bits,
        'expected_valid_bits': expected,
        'valid_mismatch_lanes': mismatches,
        'invalid_lanes': [lane_id for lane_id in range(WIDTH) if expected[lane_id] is None],
        'invalid_raw_bits': invalid_raw,
        'valid_exact_match': not mismatches,
    }

def main():
    results = []
    selected = {
        'int16': torch.int16,
        'int32': torch.int32,
        'int64': torch.int64,
        'float16': torch.float16,
        'bfloat16': torch.bfloat16,
        'float64': torch.float64,
    }
    import sys
    dtypes = [selected[name] for name in sys.argv[1:]] if len(sys.argv) > 1 else list(selected.values())
    for dtype in dtypes:
        results.append(run_case(dtype, 'idx', lane=0))
        results.append(run_case(dtype, 'idx', lane=63))
        results.append(run_case(dtype, 'xor', offset=1))
        results.append(run_case(dtype, 'xor', offset=63))
        results.append(run_case(dtype, 'up', offset=1))
        results.append(run_case(dtype, 'up', offset=63))
        results.append(run_case(dtype, 'down', offset=1))
        results.append(run_case(dtype, 'down', offset=63))
    out = Path(os.environ.get('SHUFFLE_RAW_RESULTS', 'shuffle_gfx950_raw.json'))
    out.write_text(json.dumps(results, indent=2) + '\n')
    summary = []
    for result in results:
        summary.append({key: result[key] for key in ('dtype','mode','lane','offset','valid_exact_match','valid_mismatch_lanes','invalid_lanes')})
    print(json.dumps(summary, indent=2))
    failures = [result for result in results if not result['valid_exact_match']]
    print(f'cases={len(results)} valid_mapping_failures={len(failures)}')
    for failure in failures:
        print('FAIL', failure['dtype'], failure['mode'], failure['lane'], failure['offset'], failure['valid_mismatch_lanes'][:16])

if __name__ == '__main__':
    main()
