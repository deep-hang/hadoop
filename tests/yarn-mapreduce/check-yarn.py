#!/usr/bin/env python3
"""Verify YARN/MapReduce on the three-node cluster.

Run on the host from the repository root:

    python3 tests/yarn-mapreduce/check-yarn.py

Defaults match member 2's documented cluster
(compose/distributed.yaml, project hadoop-distributed). To use the local
pre-integration lab instead:

    COMPOSE_FILE=runtime/yarn-lab/compose.yaml \
    COMPOSE_PROJECT=hadoop-yarn-lab \
    python3 tests/yarn-mapreduce/check-yarn.py

The script only reads and submits work: it does not start, stop or format the
cluster. Every failed assertion returns a non-zero exit code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPOSE = "compose/distributed.yaml"
DEFAULT_PROJECT = "hadoop-distributed"
EXAMPLES = "/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar"
DEFAULT_INPUT = "/project/input/yarn-check"
EXPECTED = {"hadoop": 8000, "hello": 8000}
AM_CONTAINER_SUFFIX = "_01_000001"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compose-file",
                    default=os.environ.get("COMPOSE_FILE", DEFAULT_COMPOSE),
                    help="compose file relative to the repository root")
parser.add_argument("--project",
                    default=os.environ.get("COMPOSE_PROJECT", DEFAULT_PROJECT),
                    help="compose project name")
parser.add_argument("--input", default=DEFAULT_INPUT,
                    help="HDFS input directory (fixed input, reused)")
parser.add_argument("--output", default=None,
                    help="HDFS output directory (must not exist)")
parser.add_argument("--wait", type=int, default=420,
                    help="seconds to wait for two DataNodes and two NodeManagers")
parser.add_argument("--job-timeout", type=int, default=1200,
                    help="seconds allowed for the MapReduce job")
args = parser.parse_args()

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT = args.output or f"/project/output/yarn-check/run-{STAMP}"
REPORT = ROOT / "runtime" / f"yarn-check-{STAMP}"
REPORT.mkdir(parents=True)
COMPOSE = ["docker", "compose", "--env-file", str(ROOT / ".development"),
           "-p", args.project, "-f", str((ROOT / args.compose_file).resolve())]
results: dict[str, object] = {
    "project": args.project,
    "compose_file": args.compose_file,
    "input": args.input,
    "output": OUTPUT,
    "started_at": datetime.now().isoformat(timespec="seconds"),
}
sequence = 0


def run(command: list[str], *, timeout: int = 120, check: bool = True,
        stdin_text: str | None = None) -> subprocess.CompletedProcess:
    global sequence
    sequence += 1
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=ROOT, input=stdin_text,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   timeout=timeout)
    except subprocess.TimeoutExpired as error:
        text = (error.stdout or "") + (error.stderr or "")
        (REPORT / f"{sequence:03d}.log").write_text(
            " ".join(command) + f"\nTIMEOUT after {timeout}s\n" + text,
            encoding="utf-8")
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(command)}")
    elapsed = round(time.monotonic() - started, 1)
    (REPORT / f"{sequence:03d}.log").write_text(
        " ".join(command) + f"\n(exit {completed.returncode}, {elapsed}s)\n"
        + completed.stdout + completed.stderr, encoding="utf-8")
    if check and completed.returncode:
        detail = (completed.stderr + completed.stdout).strip()[-4000:]
        raise RuntimeError(
            f"Command exited {completed.returncode}: {' '.join(command)}\n{detail}")
    return completed


def compose(*command: str, **kwargs) -> subprocess.CompletedProcess:
    return run([*COMPOSE, *command], **kwargs)


def master(*command: str, **kwargs) -> subprocess.CompletedProcess:
    return compose("exec", "-T", "master", *command, **kwargs)


def parse_nodes(text: str) -> dict[str, str]:
    nodes: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"\s*(\S+):\d+\s+RUNNING\b", line)
        if match:
            nodes[match.group(1)] = line.strip()
    return nodes


def datanodes(text: str) -> int | None:
    match = re.search(r"Live datanodes \((\d+)\)", text)
    return int(match.group(1)) if match else None


def wait_ready() -> dict[str, object]:
    deadline = time.monotonic() + args.wait
    latest: dict[str, object] = {}
    last_print = 0.0
    while time.monotonic() < deadline:
        nodes_report = master("yarn", "node", "-list", check=False, timeout=30)
        names = parse_nodes(nodes_report.stdout)
        report = master("hdfs", "dfsadmin", "-report", check=False, timeout=30)
        live = datanodes(report.stdout)
        safemode = master("hdfs", "dfsadmin", "-safemode", "get",
                          check=False, timeout=30)
        off = "Safe mode is OFF" in safemode.stdout
        latest = {"nodes": sorted(names), "datanodes": live, "safemode_off": off}
        if len(names) == 2 and live == 2 and off:
            return latest
        if time.monotonic() - last_print >= 15:
            print(f"Waiting for cluster: {json.dumps(latest)}", flush=True)
            last_print = time.monotonic()
        time.sleep(3)
    raise RuntimeError(f"Cluster not ready after {args.wait}s: {json.dumps(latest)}")


def prepare_input() -> None:
    script = """
set -eu
mkdir -p /tmp/yarn-check-input
for n in 01 02 03 04 05 06 07 08; do
  awk 'BEGIN { for (i = 0; i < 1000; i++) print "hello hadoop" }' \
    > "/tmp/yarn-check-input/part-$n.txt"
done
if hdfs dfs -test -d @INPUT@; then
  count=$(hdfs dfs -ls @INPUT@/part-*.txt | grep -c 'part-' || true)
  if [ "$count" -ne 8 ]; then
    echo "Existing input @INPUT@ has $count part files, expected 8." >&2
    exit 1
  fi
else
  hdfs dfs -mkdir -p @INPUT@
  hdfs dfs -put /tmp/yarn-check-input/part-*.txt @INPUT@
fi
test "$(hdfs dfs -cat @INPUT@/part-01.txt | wc -l)" -eq 1000
hdfs dfs -ls @INPUT@
""".replace("@INPUT@", args.input)
    master("bash", "-ec", script, timeout=180)


def read_counts() -> dict[str, int]:
    result = master("hdfs", "dfs", "-cat", f"{OUTPUT}/part-r-*", timeout=60)
    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        word, count = line.split("\t")
        counts[word] = counts.get(word, 0) + int(count)
    if counts != EXPECTED:
        raise RuntimeError(f"Unexpected word counts: {counts}; expected {EXPECTED}")
    return counts


def container_evidence(app_id: str) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    for worker in ("worker1", "worker2"):
        found = compose(
            "exec", "-T", worker, "bash", "-c",
            f"find /opt/hadoop/logs/userlogs/{app_id} -mindepth 1 -maxdepth 1 "
            "-type d -printf '%f\\n' 2>/dev/null | sort",
            check=False, timeout=60)
        containers = [line.strip() for line in found.stdout.splitlines()
                      if line.strip().startswith("container_")]
        tasks = [c for c in containers if not c.endswith(AM_CONTAINER_SUFFIX)]
        evidence[worker] = tasks
        if not tasks:
            raise RuntimeError(
                f"{worker} has no non-AM container logs for {app_id}; "
                f"all containers: {containers}")
    return evidence


success = False
try:
    print(f"Compose project: {args.project} ({args.compose_file})", flush=True)
    run(["docker", "compose", "version"], timeout=30)
    compose("config", "--quiet", timeout=60)
    compose("exec", "-T", "master", "true", timeout=30)
    results["readiness"] = wait_ready()
    nodes = parse_nodes(master("yarn", "node", "-list").stdout)
    if sorted(nodes) != ["worker1", "worker2"]:
        raise RuntimeError(f"Expected exactly worker1 and worker2 RUNNING, got {nodes}")
    results["node_managers"] = nodes
    print("PASS: two NodeManagers RUNNING: worker1, worker2", flush=True)

    prepare_input()
    if master("hdfs", "dfs", "-test", "-e", OUTPUT,
              check=False).returncode == 0:
        raise RuntimeError(f"Output already exists, refusing to delete it: {OUTPUT}")

    print(f"Submitting the bundled WordCount example: {args.input} -> {OUTPUT}",
          flush=True)
    job = master("hadoop", "jar", EXAMPLES, "wordcount",
                 "-D", "mapreduce.job.reduces=2", args.input, OUTPUT,
                 timeout=args.job_timeout)
    job_log = job.stdout + job.stderr
    applications = re.findall(r"application_\d+_\d+", job_log)
    if not applications:
        raise RuntimeError("No YARN application ID in the job output; "
                           "local mode is not acceptable")
    app_id = applications[-1]
    results["application_id"] = app_id

    status = master("yarn", "application", "-status", app_id).stdout
    results["application_status"] = status
    if "Final-State : SUCCEEDED" not in status:
        raise RuntimeError(f"Application did not succeed:\n{status}")
    print(f"PASS: {app_id} FINISHED / SUCCEEDED", flush=True)

    counts = read_counts()
    results["word_counts"] = counts
    print(f"PASS: output matches expected {json.dumps(counts)}", flush=True)

    evidence = container_evidence(app_id)
    results["worker_task_containers"] = evidence
    for worker, containers in evidence.items():
        print(f"PASS: {worker} ran {len(containers)} task container(s): "
              + ", ".join(containers), flush=True)

    master("hdfs", "dfsadmin", "-report", check=False, timeout=60)
    success = True
except Exception as error:
    results["error"] = str(error)
    print(f"FAIL: {error}", flush=True)
finally:
    results["passed"] = success
    results["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (REPORT / "result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidence: {REPORT / 'result.json'}", flush=True)

if not success:
    sys.exit(1)
print("PASS: YARN registration, real MapReduce job and both workers' task evidence",
      flush=True)
