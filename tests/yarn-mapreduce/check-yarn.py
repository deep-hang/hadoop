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

Paths are HDFS paths. Spaces and shell-special characters are supported when
the path is quoted on the command line, for example:

    python3 tests/yarn-mapreduce/check-yarn.py \
      --input '/project/input/yarn check $demo' \
      --output '/project/output/yarn check/run 001'

HDFS glob characters (* ? [ ] { }) are rejected because FsShell would treat
them as patterns instead of literal directory names.

The script only reads and submits work: it does not start, stop or format the
cluster. Every failed assertion returns a non-zero exit code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
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
# ApplicationMaster is container 1 in every application attempt.  Matching just
# _01_000001 would wrongly count an AM retry (_02_000001) as a task container.
AM_CONTAINER_SUFFIX = "_000001"
# Task containers print this line only after the task (and its commit) finished.
TASK_SUCCESS = re.compile(r"Task '(attempt_\d+_\d+_[mr]_\d+_\d+)' done\.")
HDFS_GLOB_CHARS = set("*?[]{}")


def checked_hdfs_path(value: str, option: str) -> str:
    """Validate an HDFS path while allowing spaces and shell-special chars."""
    if not value:
        raise SystemExit(f"{option} must not be empty")
    if not value.startswith("/"):
        raise SystemExit(f"{option} must be an absolute HDFS path: {value!r}")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise SystemExit(f"{option} must not contain control characters: {value!r}")
    globbed = "".join(sorted({char for char in value if char in HDFS_GLOB_CHARS}))
    if globbed:
        raise SystemExit(
            f"{option} contains HDFS glob characters {globbed!r}: {value!r}; "
            "use a literal path without * ? [ ] { }")
    return value


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compose-file",
                    default=os.environ.get("COMPOSE_FILE", DEFAULT_COMPOSE),
                    help="compose file relative to the repository root")
parser.add_argument("--project",
                    default=os.environ.get("COMPOSE_PROJECT", DEFAULT_PROJECT),
                    help="compose project name")
parser.add_argument("--input", default=DEFAULT_INPUT,
                    help="absolute HDFS input directory (spaces allowed when quoted)")
parser.add_argument("--output", default=None,
                    help="absolute HDFS output directory (must not exist)")
parser.add_argument("--wait", type=int, default=420,
                    help="seconds to wait for two DataNodes and two NodeManagers")
parser.add_argument("--job-timeout", type=int, default=1200,
                    help="seconds allowed for the MapReduce job")
args = parser.parse_args()

STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
args.input = checked_hdfs_path(args.input, "--input")
OUTPUT = checked_hdfs_path(
    args.output or f"/project/output/yarn-check/run-{STAMP}", "--output")
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
    display = shlex.join(command)
    try:
        completed = subprocess.run(command, cwd=ROOT, input=stdin_text,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   timeout=timeout)
    except subprocess.TimeoutExpired as error:
        text = (error.stdout or "") + (error.stderr or "")
        (REPORT / f"{sequence:03d}.log").write_text(
            display + f"\nTIMEOUT after {timeout}s\n" + text,
            encoding="utf-8")
        raise RuntimeError(f"Command timed out after {timeout}s: {display}")
    elapsed = round(time.monotonic() - started, 1)
    (REPORT / f"{sequence:03d}.log").write_text(
        display + f"\n(exit {completed.returncode}, {elapsed}s)\n"
        + completed.stdout + completed.stderr, encoding="utf-8")
    if check and completed.returncode:
        detail = (completed.stderr + completed.stdout).strip()[-4000:]
        raise RuntimeError(
            f"Command exited {completed.returncode}: {display}\n{detail}")
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
    script = r"""
set -eu
input=$1
mkdir -p /tmp/yarn-check-input
for n in 01 02 03 04 05 06 07 08; do
  awk 'BEGIN { for (i = 0; i < 1000; i++) print "hello hadoop" }' \
    > "/tmp/yarn-check-input/part-$n.txt"
done
if hdfs dfs -test -d "$input"; then
  files=$(hdfs dfs -count "$input" | awk '{print $2}')
  if [ "$files" -eq 0 ]; then
    hdfs dfs -put -f /tmp/yarn-check-input/part-*.txt "$input"
  elif [ "$files" -ne 8 ]; then
    echo "Existing input $input has $files files, expected 8; refusing to mix old and new data." >&2
    exit 1
  elif ! hdfs dfs -test -e "$input/part-01.txt" || ! hdfs dfs -test -e "$input/part-08.txt"; then
    echo "Existing input $input does not contain the expected part-01..08 files." >&2
    exit 1
  fi
else
  hdfs dfs -mkdir -p "$input"
  hdfs dfs -put -f /tmp/yarn-check-input/part-*.txt "$input"
fi
test "$(hdfs dfs -cat "$input/part-01.txt" | wc -l)" -eq 1000
echo "input=$input files=8 lines_per_file=1000"
"""
    # Pass the path as $1 instead of interpolating it into the script.  This is
    # what makes spaces, quotes, $, & and non-ASCII characters safe.
    master("bash", "-ec", script, "bash", args.input, timeout=180)


def read_counts() -> dict[str, int]:
    if master("hdfs", "dfs", "-test", "-e", f"{OUTPUT}/_SUCCESS",
              check=False, timeout=30).returncode != 0:
        raise RuntimeError(f"Missing _SUCCESS under {OUTPUT}")
    counts: dict[str, int] = {}
    # Two reducers produce exactly these files; explicit names avoid HDFS glob
    # expansion and keep spaces or $ in OUTPUT literal.
    for name in ("part-r-00000", "part-r-00001"):
        result = master("hdfs", "dfs", "-cat", f"{OUTPUT}/{name}", timeout=60)
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            word, count = line.split("\t")
            counts[word] = counts.get(word, 0) + int(count)
    if counts != EXPECTED:
        raise RuntimeError(f"Unexpected word counts: {counts}; expected {EXPECTED}")
    return counts


def parse_worker_evidence(worker: str, text: str) -> dict[str, object]:
    """Parse one worker's container log summary.

    A container counts only when it is a YarnChild task container and its
    syslog shows a completed task.  Failed, killed, speculative and retried
    attempts have no such marker and are reported as skipped, so a retry can
    never make an idle worker look busy.
    """
    containers: list[str] = []
    successful: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) != 3:
            continue
        container, kind, marker = parts
        if not container.startswith("container_"):
            continue
        containers.append(container)
        if kind == "MRAppMaster" or container.endswith(AM_CONTAINER_SUFFIX):
            skipped.append({"container": container, "reason": "ApplicationMaster"})
            continue
        if kind != "YarnChild" and not (kind == "" and TASK_SUCCESS.search(marker)):
            skipped.append({
                "container": container,
                "reason": f"container type is not YarnChild ({kind or 'unknown'})",
            })
            continue
        match = TASK_SUCCESS.search(marker)
        if not match:
            skipped.append({
                "container": container,
                "reason": "no successful task completion marker "
                          "(failed, killed or retried attempt)",
            })
            continue
        attempt = match.group(1)
        task_type = "map" if "_m_" in attempt else "reduce"
        successful.append({"container": container, "attempt": attempt,
                           "type": task_type})
    maps = [item["attempt"] for item in successful if item["type"] == "map"]
    reduces = [item["attempt"] for item in successful if item["type"] == "reduce"]
    return {
        "worker": worker,
        "containers": containers,
        "successful": successful,
        "maps": maps,
        "reduces": reduces,
        "skipped": skipped,
    }


def worker_task_evidence(app_id: str) -> dict[str, dict[str, object]]:
    script = r"""
set -eu
app=$1
base="/opt/hadoop/logs/userlogs/$app"
if [ ! -d "$base" ]; then
  echo "NO_LOGS"
  exit 0
fi
for d in "$base"/*; do
  [ -d "$d" ] || continue
  c=$(basename "$d")
  kind=$(grep -aoE 'YarnChild|MRAppMaster' "$d/launch_container.sh" 2>/dev/null | head -1 || true)
  if [ -z "$kind" ]; then
    kind=$(grep -aoE 'YarnChild|MRAppMaster' "$d/syslog" 2>/dev/null | head -1 || true)
  fi
  marker=$(grep -aoE "Task 'attempt_[0-9]+_[0-9]+_[mr]_[0-9]+_[0-9]+' done\." "$d/syslog" 2>/dev/null | tail -1 || true)
  printf '%s|%s|%s\n' "$c" "$kind" "$marker"
done
"""
    evidence: dict[str, dict[str, object]] = {}
    for worker in ("worker1", "worker2"):
        found = compose("exec", "-T", worker, "bash", "-ec", script, "bash",
                        app_id, check=False, timeout=120)
        if found.returncode != 0:
            detail = (found.stderr + found.stdout).strip()[-2000:]
            raise RuntimeError(f"Could not read {worker} userlogs: {detail}")
        if "NO_LOGS" in found.stdout:
            raise RuntimeError(
                f"{worker} has no userlogs for {app_id}. The NodeManager may "
                "have restarted and cleaned them; rerun the check immediately "
                "after a new job.")
        parsed = parse_worker_evidence(worker, found.stdout)
        if not parsed["successful"]:
            raise RuntimeError(
                f"{worker} has no successful YarnChild task for {app_id}. "
                f"Containers: {parsed['containers'] or 'none'}; "
                f"skipped: {parsed['skipped'] or 'none'}")
        evidence[worker] = parsed
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

    evidence = worker_task_evidence(app_id)
    results["worker_task_evidence"] = evidence
    results["worker_task_containers"] = {
        worker: [item["container"] for item in data["successful"]]
        for worker, data in evidence.items()
    }
    for worker, data in evidence.items():
        print(f"PASS: {worker} completed {len(data['maps'])} Map and "
              f"{len(data['reduces'])} Reduce attempt(s): "
              + ", ".join(item["container"] for item in data["successful"]),
              flush=True)
        ignored = [item for item in data["skipped"]
                   if item["reason"] != "ApplicationMaster"]
        for item in ignored:
            print(f"INFO: {worker} ignored {item['container']}: {item['reason']}",
                  flush=True)

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
print("PASS: YARN registration, real MapReduce job and both workers' successful task evidence",
      flush=True)
