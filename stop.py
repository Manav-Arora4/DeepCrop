"""
Stop the DeepCrop stack started by start.py.

  py stop.py         stop the backend, frontend and Postgres container
  py stop.py --all   also quit Ollama and Docker Desktop

Your data stays: Postgres keeps its volume, so readings, scans and advice
are still there next time you run py start.py.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIDS = ROOT / ".run" / "pids.json"
PORTS = {"backend": 8000, "frontend": 5173}


def say(msg):
    print(f"[stop] {msg}", flush=True)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def kill_tree(pid):
    if os.name == "nt":
        return run(["taskkill", "/PID", str(pid), "/T", "/F"]).returncode == 0
    try:
        os.killpg(os.getpgid(pid), 15)
        return True
    except OSError:
        return False


def pids_on_port(port):
    """PIDs listening on a local port (catches servers not started by start.py)."""
    if os.name != "nt":
        out = run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"]).stdout
        return {int(p) for p in out.split()}
    found = set()
    for line in run(["netstat", "-ano", "-p", "TCP"]).stdout.splitlines():
        m = re.match(r"\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", line)
        if m and int(m.group(1)) == port and int(m.group(2)) != 0:
            found.add(int(m.group(2)))
    return found


def stop_servers():
    saved = json.loads(PIDS.read_text()) if PIDS.exists() else {}
    for name, port in PORTS.items():
        targets = set(pids_on_port(port))
        if name in saved:
            targets.add(saved[name])
        stopped = [pid for pid in targets if kill_tree(pid)]
        say(f"{name.title()} stopped." if stopped else f"{name.title()} wasn't running.")
    PIDS.unlink(missing_ok=True)


def stop_postgres():
    if run(["docker", "info"]).returncode != 0:
        say("Docker isn't running, so Postgres is already stopped.")
        return
    r = run(["docker", "compose", "stop", "postgres"], cwd=ROOT)
    say("Postgres stopped." if r.returncode == 0 else "Couldn't stop Postgres:\n" + r.stderr)


def stop_ollama():
    if os.name == "nt":
        run(["taskkill", "/IM", "ollama app.exe", "/F"])
        r = run(["taskkill", "/IM", "ollama.exe", "/T", "/F"])
    else:
        r = run(["pkill", "-f", "ollama serve"])
    say("Ollama stopped." if r.returncode == 0 else "Ollama wasn't running.")


def stop_docker_desktop():
    if run(["docker", "desktop", "stop"]).returncode == 0:
        say("Docker Desktop stopped.")
        return
    if os.name == "nt":
        r = run(["taskkill", "/IM", "Docker Desktop.exe", "/T", "/F"])
        say("Docker Desktop stopped." if r.returncode == 0 else "Docker Desktop wasn't running.")


def main():
    stop_servers()
    stop_postgres()
    if "--all" in sys.argv:
        stop_ollama()
        stop_docker_desktop()
    else:
        say("Ollama and Docker Desktop left running (use py stop.py --all to quit them too).")
    say("Done.")


if __name__ == "__main__":
    main()
