#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path
from getpass import getpass
from datetime import datetime
from couchbase.cluster import Cluster, ClusterOptions
from couchbase_core.cluster import PasswordAuthenticator

import json
import os
import uuid


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def _get_metrics():
    metrics_path = Path(SCRIPT_DIR) / ".." / "metrics" / "all_metrics.json"
    with open(metrics_path) as fin:
        return json.load(fin)


def _update_benchmarks(directory: str):
    all_benchmarks = []
    for filename in Path(args.directory).glob("*.json"):
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

            all_benchmarks.append(entry)

    return all_benchmarks


if __name__ == "__main__":
    parser = ArgumentParser(prog="cbl_upload")

    parser.add_argument("directory", action="store", type=str,
                        help="The directory containing the JSON output of the performance tests")
    parser.add_argument("--server", action="store", type=str, default="localhost",
                        help="The server to upload the data to (default %(default)s)")
    parser.add_argument("--username", action="store", type=str, default="Administrator",
                        help="The username to use to authenticate with the server (default %(default)s)")
    parser.add_argument("--password", action="store", type=str,
                        help="The password to use to authenticate with the server (will prompt if omitted)")
    parser.add_argument("--build-url", action="store", type=str,
                        help="The URL of the Jenkins job to record in the results")
    parser.add_argument("--build", action="store", type=str,
                        help="The build version to record in the results")
    args = parser.parse_args()

    if args.password is None:
        args.password = getpass("Enter server password: ")

    print("Connecting to couchbase://{}:8091".format(args.server))
    cluster = Cluster("couchbase://{}:8091".format(args.server), ClusterOptions(
        PasswordAuthenticator(args.username, args.password)))

    all_metrics = _get_metrics()
    seen_metrics = set()
    updated_benchmarks = _update_benchmarks(args.directory)
    metrics_bucket = cluster.bucket("metrics")
    benchmarks_bucket = cluster.bucket("benchmarks")
    for mark in updated_benchmarks:
        benchmarks_bucket.upsert(str(uuid.uuid4()), mark)
        if mark["metric"] not in seen_metrics:
            seen_metrics.add(mark["metric"])
            metric = next((m for m in all_metrics if m["id"] == mark["metric"]), None)
            if metric is not None:
                metrics_bucket.upsert(mark["metric"], metric)