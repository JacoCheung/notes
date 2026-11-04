"""Summarize API events without adding VA reservation bytes to allocation bytes."""
import argparse
import csv
from collections import Counter


def summarize(path):
    with open(path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Empty trace: check subscription, workload, and output path")
    phases = list(dict.fromkeys(row["phase"] for row in rows))
    counts = Counter()
    failed = Counter()
    byte_totals = Counter()
    for row in rows:
        if row["kind"] != "api":
            continue
        key = (row["phase"], row["domain"], row["api"])
        if int(row["result"]) != 0:
            failed[key] += 1
            continue
        counts[key] += 1
        if row["bytes"]:
            byte_totals[key] += int(row["bytes"])
    print(f"{'phase':<14} {'domain':<8} {'API':<24} {'ok':>4} {'failed':>6} {'sum(bytes), MiB':>16}")
    for phase in phases:
        keys = sorted(key for key in counts.keys() | failed.keys() if key[0] == phase)
        if not keys:
            print(f"{phase:<14} (no selected API calls)")
        for key in keys:
            total = f"{byte_totals[key] / 2**20:.2f}" if key in byte_totals else "-"
            print(f"{key[0]:<14} {key[1]:<8} {key[2]:<24} {counts[key]:>4} {failed[key]:>6} {total:>16}")
    print("\nBytes are summed separately per API, not live memory or a cross-API total.")
    print("Reserve = VA range; Create = physical allocation; Map = mapping extent.")
    print("Release/Free can omit a size; recover it from the successful creation record.")
    if not counts:
        raise ValueError("No successful selected API calls: this is not evidence of zero allocation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("trace")
    summarize(parser.parse_args().trace)
