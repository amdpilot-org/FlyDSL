#!/usr/bin/env python3

import hashlib
import json

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx


SENTINEL = -123456789
CASES = ((64, 64), (256, 256), (64, 37), (256, 100))


def tensor_sha256(tensor):
    return hashlib.sha256(tensor.contiguous().cpu().numpy().tobytes()).hexdigest()


def run_case(block_threads, active_length, seed):
    @flyc.kernel(known_block_size=[block_threads, 1, 1])
    def kernel(values: fx.Tensor, output: fx.Tensor):
        tid = fx.thread_idx.x
        block_scan = fx.coop.BlockScan[
            fx.Int32,
            block_threads,
            fx.coop.BlockScanAlgorithm.WARP_SCANS,
        ]
        storage = fx.SharedAllocator().allocate(block_scan.SharedStorage).peek()
        value = (tid < active_length).select(values[tid], fx.Int32(0))
        scanned = block_scan.inclusive(value, fx.ReductionOp.ADD, storage=storage)
        if tid < active_length:
            output[tid] = scanned

    @flyc.jit
    def launch(values: fx.Tensor, output: fx.Tensor, stream: fx.Stream = fx.Stream(None)):
        kernel(values, output).launch(
            grid=(1, 1, 1),
            block=(block_threads, 1, 1),
            stream=stream,
        )

    generator = torch.Generator(device="cpu").manual_seed(seed)
    values = torch.randint(
        -1000,
        1001,
        (block_threads,),
        dtype=torch.int32,
        generator=generator,
    )
    values[active_length:] = 0
    values = values.to("cuda")
    output = torch.full(
        (block_threads,),
        SENTINEL,
        dtype=torch.int32,
        device="cuda",
    )
    launch(values, output, stream=torch.cuda.Stream())
    torch.cuda.synchronize()

    host_values = values.cpu()
    host_output = output.cpu()
    expected = host_values[:active_length].cumsum(0, dtype=torch.int32)
    active_mismatches = (host_output[:active_length] != expected).sum().item()
    sentinel_mismatches = (
        host_output[active_length:] != SENTINEL
    ).sum().item()

    return {
        "active_exact": active_mismatches == 0,
        "active_length": active_length,
        "active_mismatches": active_mismatches,
        "block_threads": block_threads,
        "expected_sha256": tensor_sha256(expected),
        "input_sha256": tensor_sha256(host_values),
        "num_waves": block_threads // 64,
        "output_first_4": host_output[: min(4, active_length)].tolist(),
        "output_last_4": host_output[max(0, active_length - 4) : active_length].tolist(),
        "output_sha256": tensor_sha256(host_output),
        "sentinel_exact": sentinel_mismatches == 0,
        "sentinel_mismatches": sentinel_mismatches,
    }


def main():
    results = [
        run_case(block_threads, active_length, 20260910 + index)
        for index, (block_threads, active_length) in enumerate(CASES)
    ]
    passed = all(
        result["active_exact"] and result["sentinel_exact"]
        for result in results
    )
    print(json.dumps({"all_passed": passed, "cases": results}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
