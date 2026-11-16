"""Pack the per-part viewer STLs and parts.json into one models.json for the web viewers.

Run:  python cad/pack_viewer.py              (writes cad/out/viewer/models.json)
      python cad/pack_viewer.py --frontend   (also writes frontend/public/field-unit/models.json)
"""

import argparse
import base64
import json
from pathlib import Path

VIEWER = Path(__file__).parent / "out" / "viewer"
FRONTEND = Path(__file__).parent.parent / "frontend" / "public" / "field-unit" / "models.json"

parser = argparse.ArgumentParser(description="Pack viewer meshes into models.json")
parser.add_argument("--frontend", action="store_true", help="Also copy the bundle into the dashboard's public folder")
args = parser.parse_args()

parts = json.loads((VIEWER / "parts.json").read_text())
for p in parts:
    p["stl_base64"] = base64.b64encode((VIEWER / p["file"]).read_bytes()).decode("ascii")
bundle = json.dumps(parts)
targets = [VIEWER / "models.json"] + ([FRONTEND] if args.frontend else [])
for target in targets:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(bundle)
    print(f"{target}: {len(parts)} parts, {target.stat().st_size / 1e6:.1f} MB")
