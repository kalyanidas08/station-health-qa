"""Reduces a full OpenAPI schema down to the parts that matter to a consumer
of this API: which paths/methods/status codes exist, and the required
fields + property types of each named schema. Deliberately ignores metadata
(descriptions, title, version strings, examples) that changes often without
being a breaking change to anyone actually calling this API.

Shared by test_openapi_contract.py (the guard) and generate_snapshot.py
(the tool for updating the guard after an intentional API change).
"""


def extract_contract_surface(openapi_schema: dict) -> dict:
    surface = {"paths": {}, "schemas": {}}

    for path, methods in openapi_schema.get("paths", {}).items():
        surface["paths"][path] = {
            method: {"status_codes": sorted(operation.get("responses", {}).keys())}
            for method, operation in methods.items()
        }

    for name, schema in openapi_schema.get("components", {}).get("schemas", {}).items():
        surface["schemas"][name] = {
            "required": sorted(schema.get("required", [])),
            "properties": {
                prop_name: prop_schema.get("type") or prop_schema.get("anyOf") or prop_schema.get("$ref")
                for prop_name, prop_schema in schema.get("properties", {}).items()
            },
        }

    return surface
