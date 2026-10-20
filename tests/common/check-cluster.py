"""Run an isolated three-node proof using the published base image.

Usage: python tests/common/check-cluster.py
Requires Docker Compose and the imported hadoop-base:v0.1 image.
The test removes only its uniquely named containers/network/volumes on exit.
"""
from pathlib import Path
import json
import re
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "hadoop-base-check-" + uuid.uuid4().hex[:8]
FIXTURE = ROOT / "tests/common/fixtures/cluster/compose.yaml"
REPORT = ROOT / "runtime" / PROJECT
REPORT.mkdir(parents=True)
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(FIXTURE)]
EXPECTED = {"hadoop": 8000, "hello": 8000}
results = {"project": PROJECT}
sequence = 0


def run(args, *, timeout=60, input=None, check=True):
    global sequence
    sequence += 1
    completed = subprocess.run(args, cwd=ROOT, input=input, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=timeout)
    (REPORT / f"{sequence:03d}.log").write_text(
        " ".join(args) + "\n" + completed.stdout + completed.stderr,
        encoding="utf-8")
    if check and completed.returncode:
        raise RuntimeError(f"Command exited {completed.returncode}: {' '.join(args)}\n"
                           + (completed.stderr + completed.stdout)[-6000:])
    return completed


def compose(*args, **kwargs):
    return run([*COMPOSE, *args], **kwargs)


def master(*args, **kwargs):
    return compose("exec", "-T", "master", *args, **kwargs)


def ready():
    deadline = time.monotonic() + 180
    latest = {}
    last_print = 0
    while time.monotonic() < deadline:
        try:
            nn = master("curl", "-fsS", "--max-time", "4",
                        "http://master:9870/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo",
                        check=False, timeout=10)
            rm = master("curl", "-fsS", "--max-time", "4",
                        "http://master:8088/ws/v1/cluster/nodes",
                        check=False, timeout=10)
            if nn.returncode == 0 and rm.returncode == 0:
                bean = json.loads(nn.stdout)["beans"][0]
                live = json.loads(bean["LiveNodes"])
                nodes = json.loads(rm.stdout).get("nodes") or {}
                running = [n for n in nodes.get("node", []) if n["state"] == "RUNNING"]
                latest = {"datanodes": len(live), "node_managers": len(running),
                          "safemode": bean.get("Safemode", "")}
                if len(live) == 2 and len(running) == 2 and not latest["safemode"]:
                    return latest
        except (ValueError, KeyError, IndexError, subprocess.TimeoutExpired):
            pass
        if time.monotonic() - last_print >= 15:
            print("Waiting for HDFS/YARN readiness: " + json.dumps(latest), flush=True)
            last_print = time.monotonic()
        time.sleep(3)
    raise RuntimeError("Cluster was not ready after 180 seconds: " + json.dumps(latest))


def read_result():
    result = master("hdfs", "dfs", "-cat", "/base-probe/output/part-r-*")
    actual = {}
    for line in result.stdout.splitlines():
        word, count = line.split("\t")
        actual[word] = int(count)
    if actual != EXPECTED:
        raise RuntimeError("Unexpected job output: " + repr(actual))
    return actual


success = False
try:
    print("Isolated test project: " + PROJECT, flush=True)
    run(["docker", "image", "inspect", "hadoop-base:v0.1"])
    compose("config", "--quiet")
    uninitialized = compose("run", "--rm", "--no-deps", "master", "bash",
                            "scripts/hadoop-node.sh", "master", check=False)
    if uninitialized.returncode == 0 or "not initialized" not in uninitialized.stderr:
        raise RuntimeError("Uninitialized master was not rejected")
    guard = compose("run", "--rm", "--no-deps", "master", "bash", "-ec",
                    'mkdir -p "$HDFS_NAMENODE_DIR"; '
                    'touch "$HDFS_NAMENODE_DIR/guard-sentinel"; '
                    'if bash scripts/hadoop-node.sh init-namenode; then exit 1; fi; '
                    'test -f "$HDFS_NAMENODE_DIR/guard-sentinel"; '
                    'test ! -e "$HDFS_NAMENODE_DIR/current/VERSION"; '
                    'rm "$HDFS_NAMENODE_DIR/guard-sentinel"')
    if "Refusing to format" not in guard.stderr:
        raise RuntimeError("Nonempty directory guard did not run")
    results["initialization_guards"] = True
    print("Initializing a fresh test-only NameNode volume", flush=True)
    compose("run", "--rm", "--no-deps", "master", "bash",
            "scripts/hadoop-node.sh", "init-namenode", timeout=90)
    second_init = compose("run", "--rm", "--no-deps", "master", "bash",
                          "scripts/hadoop-node.sh", "init-namenode")
    if "already initialized" not in second_init.stdout:
        raise RuntimeError("Repeated initialization did not preserve existing metadata")
    results["repeat_init_preserves_metadata"] = True
    compose("up", "-d", "--no-build")
    results["initial_readiness"] = ready()
    print("PASS: two DataNodes and two NodeManagers registered", flush=True)
    master("hdfs", "dfs", "-mkdir", "-p", "/base-probe/input")
    prepare = ("mkdir -p /tmp/base-probe-input; cat > /tmp/base-probe-seed; "
               "for n in 1 2 3 4 5 6 7 8; do "
               "cp /tmp/base-probe-seed /tmp/base-probe-input/part-$n.txt; done; "
               "hdfs dfs -put /tmp/base-probe-input/*.txt /base-probe/input")
    master("bash", "-ec", prepare, input="hello hadoop\n" * 1000, timeout=90)
    print("Submitting the bundled MapReduce example to real YARN", flush=True)
    job = master("hadoop", "jar",
                 "/opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar",
                 "wordcount", "/base-probe/input", "/base-probe/output", timeout=300)
    job_log = job.stdout + job.stderr
    applications = re.findall(r"application_\d+_\d+", job_log)
    if not applications:
        raise RuntimeError("No YARN application ID; local mode is not an acceptable proof")
    results["application_id"] = applications[0]
    results["job_output"] = read_result()
    master("hdfs", "dfsadmin", "-report")
    for worker in ("worker1", "worker2"):
        logs = compose("exec", "-T", worker, "bash", "-c",
                       "find /opt/hadoop/logs/userlogs -name syslog -type f -print",
                       check=False)
        results[worker + "_container_logs"] = logs.stdout.splitlines()
    print("PASS: YARN example result is correct: " + json.dumps(results["job_output"]), flush=True)
    print("Restarting the three nodes while retaining test volumes", flush=True)
    compose("restart", timeout=120)
    results["restart_readiness"] = ready()
    results["after_restart_output"] = read_result()
    print("PASS: HDFS output survived cluster restart", flush=True)
    compose("exec", "-T", "worker1", "bash", "-ec",
            "target=$(jps | awk '$2 == \"DataNode\" {print $1}'); "
            'test -n "$target"; kill -TERM "$target"')
    container = compose("ps", "-a", "-q", "worker1").stdout.strip()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        state = json.loads(run(["docker", "inspect", container]).stdout)[0]["State"]
        if not state["Running"]:
            if state["ExitCode"] == 0:
                raise RuntimeError("Failed node exited with a successful status")
            results["service_failure_stops_node"] = True
            break
        time.sleep(1)
    else:
        raise RuntimeError("Node remained running after DataNode exited")
    print("PASS: a failed service stops its node with a failure status", flush=True)
    success = True
except Exception as error:
    results["error"] = str(error)
    print("FAIL: " + str(error), flush=True)
finally:
    try:
        compose("logs", "--no-color", timeout=30, check=False)
    finally:
        cleanup = compose("down", "--volumes", "--remove-orphans", timeout=120, check=False)
        results["cleanup_exit_code"] = cleanup.returncode
        success = success and cleanup.returncode == 0
        results["passed"] = success
        (REPORT / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
        print("Evidence: " + str(REPORT / "result.json"), flush=True)
if not success:
    raise SystemExit(1)
print("PASS: isolated three-node foundation, real YARN job and restart persistence", flush=True)
