import json
from pathlib import Path

from app.main import app
from schema_contract import extract_contract_surface

SNAPSHOT_PATH = Path(__file__).parent / "openapi_contract_snapshot.json"


def test_openapi_contract_matches_snapshot():
    """Guards the API's public contract: which paths/methods/status codes
    exist, and the required fields + property types of every request/response
    schema. A failure here means one of two things:

      - An accidental breaking change (renamed or retyped field, removed
        endpoint or status code) - fix the code, not the snapshot.
      - An intentional, reviewed change to the API - regenerate the snapshot
        with `python tests/contract/generate_snapshot.py` and commit the diff
        so reviewers can see exactly what changed for consumers.
    """
    current = extract_contract_surface(app.openapi())
    expected = json.loads(SNAPSHOT_PATH.read_text())

    assert current == expected
