"""
Start the whole DeepCrop stack and open the dashboard.

  py start.py              start everything, open the dashboard in Helium
  py start.py --no-browser start everything, don't open a browser

Starts, in order (anything already running is left alone):
  1. Docker Desktop, then the Postgres container
  2. Ollama (the advisor's language model)
  3. Backend  (FastAPI, http://localhost:8000)
  4. Frontend (Vite, http://localhost:5173)

The backend and frontend keep running after this script exits, even if you
close the terminal. Their output goes to logs/backend.log and logs/frontend.log.
Stop everything with: py stop.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / ".run"
LOG_DIR = ROOT / "logs"
PIDS = RUN_DIR / "pids.json"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
DOCKER_DESKTOP = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"

BACKEND_URL = "http://127.0.0.1:8000/health"
FRONTEND_URL = "http://127.0.0.1:5173"
OLLAMA_URL = "http://127.0.0.1:11434/api/tags"
DASHBOARD = "http://localhost:5173/dashboard"

# Detach on Windows so the servers outlive this terminal
DETACHED = 0x00000008 | 0x00000200 | 0x08000000 if os.name == "nt" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW


def say(msg):
    print(f"[start] {msg}", flush=True)


def fail(msg):
    print(f"[start] ERROR: {msg}", flush=True)
    sys.exit(1)


def http_ok(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500
    except Exception:
        return False


def wait_for(check, what, timeout, log=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check():
            return True
        time.sleep(1)
    hint = f" See {log.relative_to(ROOT)} for details." if log else ""
    fail(f"{what} didn't come up within {timeout}s.{hint}")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def read_env(key, default):
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return default


# ---------------------------------------------------------------- services

def start_docker_and_postgres():
    if not shutil.which("docker"):
        fail("Docker isn't installed or not on PATH.")
    if run(["docker", "info"]).returncode != 0:
        if not DOCKER_DESKTOP.exists():
            fail("Docker isn't running and Docker Desktop wasn't found. Start it manually.")
        say("Starting Docker Desktop (can take a minute)...")
        subprocess.Popen([str(DOCKER_DESKTOP)], creationflags=DETACHED)
        wait_for(lambda: run(["docker", "info"]).returncode == 0, "Docker", 180)
    say("Docker is running.")

    say("Starting Postgres...")
    r = run(["docker", "compose", "up", "postgres", "-d"], cwd=ROOT)
    if r.returncode != 0:
        fail("docker compose failed:\n" + r.stderr)
    health = lambda: run(["docker", "inspect", "-f", "{{.State.Health.Status}}", "crophealth_postgres"]).stdout.strip() == "healthy"
    wait_for(health, "Postgres", 90)
    say("Postgres is healthy.")


def start_ollama():
    if not http_ok(OLLAMA_URL):
        exe = shutil.which("ollama")
        if not exe:
            say("WARNING: Ollama isn't installed; the Advisor won't be able to write advice.")
            return
        say("Starting Ollama...")
        subprocess.Popen([exe, "serve"], creationflags=DETACHED,
                         stdout=open(LOG_DIR / "ollama.log", "a"), stderr=subprocess.STDOUT)
        wait_for(lambda: http_ok(OLLAMA_URL), "Ollama", 60, LOG_DIR / "ollama.log")
    model = read_env("OLLAMA_MODEL", "qwen2.5:7b")
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=5) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        names = []
    if not any(n == model or n.startswith(model + ":") for n in names):
        say(f"WARNING: model '{model}' isn't pulled. Run: ollama pull {model}")
    say(f"Ollama is running ({model}).")


def spawn(name, cmd, url, timeout, pids):
    if http_ok(url):
        say(f"{name.title()} is already running.")
        return
    log = LOG_DIR / f"{name}.log"
    say(f"Starting {name}...")
    with open(log, "w", encoding="utf-8") as out:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, creationflags=DETACHED)
    pids[name] = p.pid
    PIDS.write_text(json.dumps(pids, indent=2))
    def ready():
        if p.poll() is not None:
            fail(f"{name} exited on startup. See {log.relative_to(ROOT)}.")
        return http_ok(url)

    wait_for(ready, name.title(), timeout, log)
    say(f"{name.title()} is up.")


def start_backend(pids):
    if not VENV_PY.exists():
        fail("No .venv found. Create it and install backend/requirements.txt first.")
    spawn("backend",
          [str(VENV_PY), "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
          BACKEND_URL, 180, pids)


def start_frontend(pids):
    npm = shutil.which("npm")
    if not npm:
        fail("npm isn't installed or not on PATH.")
    if not (ROOT / "frontend" / "node_modules").exists():
        say("Installing frontend packages (first run only)...")
        if subprocess.run([npm, "--prefix", "frontend", "install"], cwd=ROOT).returncode != 0:
            fail("npm install failed.")
    spawn("frontend",
          [npm, "--prefix", "frontend", "run", "dev", "--", "--port", "5173", "--strictPort"],
          FRONTEND_URL, 60, pids)


def open_browser():
    candidates = [
        os.environ.get("HELIUM_PATH", ""),
        os.path.expandvars(r"%LOCALAPPDATA%\imput\Helium\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\imput\Helium\Application\chrome.exe"),
    ]
    helium = next((c for c in candidates if c and Path(c).is_file()), None)
    if helium:
        subprocess.Popen([helium, DASHBOARD])
    else:
        webbrowser.open(DASHBOARD)


def main():
    RUN_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}

    start_docker_and_postgres()
    start_ollama()
    start_backend(pids)
    start_frontend(pids)

    print()
    say(f"DeepCrop is running: {DASHBOARD}")
    say("Logs are in logs/. Stop everything with: py stop.py")
    if "--no-browser" not in sys.argv:
        open_browser()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("Cancelled. Anything already started is still running; use py stop.py to stop it.")
