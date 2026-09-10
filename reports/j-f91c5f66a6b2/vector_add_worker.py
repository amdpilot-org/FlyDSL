import argparse
import json
import runpy
import time

import torch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--example", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--create-reference", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    example_globals = runpy.run_path(args.example)

    a = example_globals["A"]
    b = example_globals["B"]
    c = example_globals["C"]
    expected = a + b
    torch.save(
        {
            "label": args.label,
            "seed": args.seed,
            "shape": list(a.shape),
            "A": a.cpu(),
            "B": b.cpu(),
            "C": c.cpu(),
            "expected": expected.cpu(),
        },
        args.output,
    )

    if args.create_reference:
        torch.save(expected, args.reference)
        reference = expected
    else:
        reference = torch.load(args.reference, map_location=a.device, weights_only=True)
    max_abs_diff = (c - reference).abs().max().item()
    allclose = torch.allclose(c, reference, rtol=0.0, atol=0.0)
    result = {
        "label": args.label,
        "seed": args.seed,
        "shape": list(a.shape),
        "elapsed_seconds": time.perf_counter() - started,
        "max_abs_diff": max_abs_diff,
        "allclose": allclose,
        "exit_code": 0,
    }
    print(json.dumps(result, sort_keys=True))
    if not allclose:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
