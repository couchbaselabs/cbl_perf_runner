#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime
from alive_progress import alive_it

import json
import os
import uuid
import sys
import requests


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def _get_metrics():
    if sys.platform == "win32":
        metrics_path = Path(SCRIPT_DIR) / ".." / "metrics" / "metrics_windows.json"
    elif sys.platform == "darwin":
        metrics_path = Path(SCRIPT_DIR) / ".." / "metrics" / "metrics_macos.json"
    else:
        metrics_path = Path(SCRIPT_DIR) / ".." / "metrics" / "metrics_linux.json"

    with open(metrics_path) as fin:
        return json.load(fin)


def _update_benchmarks(directory: str):
    all_benchmarks = []
    for filename in Path(directory).glob("*.json"):
        with open(filename, "r") as fin:
            decoded = json.load(fin)

        for entry in decoded:
            if "metric" not in entry or "hidden" not in entry or "value" not in entry:
                print("Skipping invalid metric: {}".format(json.dumps(entry)))
                continue

            entry["dateTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            if args.build is not None:
                entry["build"] = args.build

            if args.build_url is not None:
                entry["buildURL"] = args.build_url

            entry["id"] = uuid.uuid4().hex

            all_benchmarks.append(entry)

    return all_benchmarks


if __name__ == "__main__":
    parser = ArgumentParser(prog="cbl_upload")

    parser.add_argument("directory", action="store", type=str,
                        help="The directory containing the JSON output of the performance tests")
    parser.add_argument("--server", action="store", type=str, default="localhost",
                        help="The server to upload the data to (default %(default)s)")
    parser.add_argument("--build-url", action="store", type=str,
                        help="The URL of the Jenkins job to record in the results")
    parser.add_argument("--build", action="store", type=str,
                        help="The build version to record in the results")
    args = parser.parse_args()

    print("Reading metrics...")
    all_metrics = _get_metrics()
    seen_metrics = set()
    print("Generating showfast data...")
    updated_benchmarks = _update_benchmarks(args.directory)
    print("Uploading...")
    for mark in alive_it(updated_benchmarks):
        with requests.post(f"http://{args.server}/api/v1/benchmarks", json=mark) as r:
            r.raise_for_status()

        if mark["metric"] not in seen_metrics:
            seen_metrics.add(mark["metric"])
            metric = next((m for m in all_metrics if m["id"] == mark["metric"]), None)
            if metric is not None:
                with requests.post(f"http://{args.server}/api/v1/metrics", json=metric) as r:
                    r.raise_for_status()