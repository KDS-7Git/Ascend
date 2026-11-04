"""Analyze bounded request observations, counting failures in the denominator."""

import argparse
import csv
import json
import math
from pathlib import Path


def analyze(path, window_seconds):
    if not 0 < window_seconds <= 86400:
        raise ValueError("A positive measurement window of at most one day is required")
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len(rows) > 100000:
        raise ValueError("Need 1..100000 observations")
    durations, good, bytes_out = [], [], 0
    for row in rows:
        elapsed, status = float(row["elapsed_ms"]), int(row["status"])
        if elapsed < 0 or not math.isfinite(elapsed):
            raise ValueError("Invalid observed duration")
        durations.append(elapsed)
        if 200 <= status < 400:
            good.append(elapsed)
        size = int(row.get("response_bytes", 0))
        if size < 0 or not 0 <= status <= 599:
            raise ValueError("Invalid status or response size")
        bytes_out += size

    def p95(values):
        return (
            sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)]
            if values
            else None
        )

    return {
        "attempts": len(rows),
        "successful": len(good),
        "failed": len(rows) - len(good),
        "error_rate": (len(rows) - len(good)) / len(rows),
        "mean_ms_all": sum(durations) / len(durations),
        "p95_ms_all": p95(durations),
        "p95_ms_successful": p95(good),
        "window_seconds": window_seconds,
        "successful_requests_per_second": len(good) / window_seconds,
        "observed_response_bytes_per_second": bytes_out / window_seconds,
        "scope": "Supplied observations and explicit window only. This is not an arrival generator, population forecast or stable-system proof.",
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("csv")
    cli.add_argument("--window-seconds", type=float, required=True)
    cli.add_argument("--max-error-rate", type=float, default=0.02)
    cli.add_argument("--max-p95-ms", type=float, default=300)
    args = cli.parse_args()
    if (
        not 0 <= args.max_error_rate <= 1
        or not math.isfinite(args.max_p95_ms)
        or args.max_p95_ms <= 0
    ):
        cli.error("max-error-rate must be 0..1; max-p95-ms must be finite and positive")
    try:
        result = analyze(args.csv, args.window_seconds)
    except (OSError, KeyError, ValueError) as error:
        cli.exit(1, str(error) + "\n")
    result["meets_selected_thresholds"] = (
        result["error_rate"] <= args.max_error_rate
        and result["p95_ms_all"] <= args.max_p95_ms
    )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["meets_selected_thresholds"] else 1)


if __name__ == "__main__":
    main()
