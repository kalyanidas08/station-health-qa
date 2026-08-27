"""Regenerate openapi_contract_snapshot.json after an intentional, reviewed
change to the API's request/response shapes.

Run from qa-automation-suite/:
    .venv\\Scripts\\python.exe tests\\contract\\generate_snapshot.py
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2] / "service"))
sys.path.insert(0, str(_HERE))

from app.main import app  # noqa: E402
from schema_contract import extract_contract_surface  # noqa: E402

SNAPSHOT_PATH = _HERE / "openapi_contract_snapshot.json"


if __name__ == "__main__":
    surface = extract_contract_surface(app.openapi())
    SNAPSHOT_PATH.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {SNAPSHOT_PATH}")
