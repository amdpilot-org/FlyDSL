import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processes", type=int, choices=(2, 3, 4), default=4)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--example", required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    results_dir = Path(args.results_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    if any(cache_dir.iterdir()):
        raise SystemExit(f"cold-cache directory is not empty: {cache_dir}")

    environment = os.environ.copy()
    environment["FLYDSL_RUNTIME_CACHE_DIR"] = str(cache_dir)
    commands = []
    processes = []
    started_times = []
    for process_index in range(args.processes):
        label = f"process-{process_index + 1}"
        output_path = results_dir / f"{label}.pt"
        command = [
            args.python,
            args.worker,
            "--example",
            args.example,
            "--reference",
            args.reference,
            "--output",
            str(output_path),
            "--label",
            label,
        ]
        commands.append(command)
        started_times.append(time.monotonic())
        processes.append(
            subprocess.Popen(
                command,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    deadline = time.monotonic() + args.timeout_seconds
    while any(process.poll() is None for process in processes):
        if time.monotonic() > deadline:
            for process in processes:
                if process.poll() is None:
                    process.kill()
            raise SystemExit(f"experiment exceeded {args.timeout_seconds} seconds")
        time.sleep(0.05)

    worker_results = []
    for label, process, started in zip(
        (f"process-{index + 1}" for index in range(args.processes)),
        processes,
        started_times,
    ):
        stdout, stderr = process.communicate()
        parsed = None
        for line in reversed(stdout.splitlines()):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        worker_results.append(
            {
                "label": label,
                "command": commands[len(worker_results)],
                "returncode": process.returncode,
                "elapsed_seconds": time.monotonic() - started,
                "worker_result": parsed,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

    cache_files = []
    temporary_files = []
    for path in sorted(cache_dir.rglob("*")):
        if path.is_file():
            relative = path.relative_to(cache_dir)
            if path.suffix == ".tmp":
                temporary_files.append(str(relative))
            cache_files.append(
                {
                    "path": str(path),
                    "relative_path": str(relative),
                    "size_bytes": path.stat().st_size,
                }
            )

    experiment = {
        "process_count": args.processes,
        "cache_dir": str(cache_dir),
        "cache_state": "cold",
        "reference": args.reference,
        "timeout_seconds": args.timeout_seconds,
        "workers": worker_results,
        "cache_files": cache_files,
        "temporary_files": temporary_files,
        "partial_cache_errors": [
            worker["stderr"]
            for worker in worker_results
            if "Failed to load cache" in worker["stderr"]
        ],
        "all_workers_passed": all(
            worker["returncode"] == 0
            and worker["worker_result"] is not None
            and worker["worker_result"]["allclose"]
            for worker in worker_results
        ),
    }
    result_path = results_dir / "experiment.json"
    result_path.write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), "all_workers_passed": experiment["all_workers_passed"]}))
    if not experiment["all_workers_passed"] or temporary_files:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
