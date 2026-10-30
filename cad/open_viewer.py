"""
Open the DeepCrop field-unit 3D viewer in the Helium browser.

Starts a local web server for cad/, then opens viewer.html in Helium
(or the default browser if Helium isn't found). Rebuilds the viewer
meshes first if they are missing or older than field_unit.py.

Run:  py cad/open_viewer.py          (Ctrl+C to stop the server)
Set HELIUM_PATH to override where Helium is looked for.
"""

import importlib.util
import os
import subprocess
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CAD_DIR = Path(__file__).resolve().parent
MODELS = CAD_DIR / "out" / "viewer" / "models.json"
SOURCE = CAD_DIR / "field_unit.py"


def find_helium():
    candidates = [
        os.environ.get("HELIUM_PATH", ""),
        os.path.expandvars(r"%LOCALAPPDATA%\imput\Helium\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\imput\Helium\Application\chrome.exe"),
    ]
    return next((Path(c) for c in candidates if c and Path(c).is_file()), None)


def ensure_models():
    stale = MODELS.exists() and SOURCE.stat().st_mtime > MODELS.stat().st_mtime
    if MODELS.exists() and not stale:
        return
    if importlib.util.find_spec("build123d") is None:
        if not MODELS.exists():
            sys.exit("[viewer] No model meshes yet. Install build123d for this Python "
                     "(python -m pip install build123d) and run this script again.")
        print("[viewer] field_unit.py changed, but build123d isn't installed here, so showing the last built model.")
        return
    print("[viewer] Model meshes are " + ("out of date" if stale else "missing") + ", rebuilding...")
    try:
        subprocess.run([sys.executable, str(SOURCE)], check=True)
        subprocess.run([sys.executable, str(CAD_DIR / "pack_viewer.py")], check=True)
    except subprocess.CalledProcessError:
        if not MODELS.exists():
            sys.exit("[viewer] Build failed, see the error above.")
        print("[viewer] Rebuild failed, see the error above. Showing the previous model instead.")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    ensure_models()

    # Port 0 picks a free port; the socket is already listening, so the browser can open first
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(CAD_DIR)))
    url = f"http://127.0.0.1:{server.server_port}/viewer.html"

    helium = find_helium()
    if helium:
        subprocess.Popen([str(helium), url])
        print(f"[viewer] Opened in Helium: {url}")
    else:
        webbrowser.open(url)
        print(f"[viewer] Helium not found, opened in the default browser: {url}")

    print("[viewer] Serving the model. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[viewer] Stopped.")


if __name__ == "__main__":
    main()
