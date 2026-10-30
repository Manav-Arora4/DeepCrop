"""Pack the per-part viewer STLs and parts.json into one models.json for the web viewer."""

import base64
import json
from pathlib import Path

VIEWER = Path(__file__).parent / "out" / "viewer"

parts = json.loads((VIEWER / "parts.json").read_text())
for p in parts:
    p["stl_base64"] = base64.b64encode((VIEWER / p["file"]).read_bytes()).decode("ascii")
(VIEWER / "models.json").write_text(json.dumps(parts))
print(f"models.json: {len(parts)} parts, {(VIEWER / 'models.json').stat().st_size / 1e6:.1f} MB")
