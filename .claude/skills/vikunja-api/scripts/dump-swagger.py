#!/usr/bin/env python3
"""Parse Vikunja swagger.json and output a markdown endpoint reference.

Usage:
    uv run scripts/dump-swagger.py                          # all endpoints
    uv run scripts/dump-swagger.py --tag task               # filter by tag
    uv run scripts/dump-swagger.py --file path/to/spec.json # custom spec file
"""

import argparse
import json
import sys
from pathlib import Path


def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref like '#/definitions/models.Task' to its definition."""
    if not ref.startswith("#/"):
        return {"type": ref}
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def format_schema(spec: dict, schema: dict, depth: int = 0) -> str:
    """Format a schema reference as a readable string."""
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return ref_name
    if schema.get("type") == "array":
        items = schema.get("items", {})
        inner = format_schema(spec, items, depth)
        return f"[{inner}]"
    return schema.get("type", "object")


def dump_endpoint(spec: dict, method: str, path: str, details: dict) -> str:
    """Format a single endpoint as markdown."""
    lines = []
    summary = details.get("summary", "")
    lines.append(f"### {method.upper()} {path}")
    if summary:
        lines.append(f"{summary}")
    lines.append("")

    # Parameters
    params = details.get("parameters", [])
    if params:
        path_params = [p for p in params if p["in"] == "path"]
        query_params = [p for p in params if p["in"] == "query"]
        body_params = [p for p in params if p["in"] == "body"]

        if path_params:
            lines.append("**Path params:**")
            for p in path_params:
                req = " (required)" if p.get("required") else ""
                lines.append(f"- `{p['name']}`: {p.get('type', 'integer')}{req}")
            lines.append("")

        if query_params:
            lines.append("**Query params:**")
            for p in query_params:
                ptype = p.get("type", "string")
                desc = p.get("description", "")
                req = " (required)" if p.get("required") else ""
                lines.append(f"- `{p['name']}`: {ptype}{req} — {desc}")
            lines.append("")

        if body_params:
            for p in body_params:
                schema = p.get("schema", {})
                schema_name = format_schema(spec, schema)
                lines.append(f"**Body:** `{schema_name}`")
            lines.append("")

    # Responses
    responses = details.get("responses", {})
    for code, resp in sorted(responses.items()):
        schema = resp.get("schema", {})
        desc = resp.get("description", "")
        if schema:
            schema_name = format_schema(spec, schema)
            lines.append(f"**Response {code}:** `{schema_name}` — {desc}")
        else:
            lines.append(f"**Response {code}:** {desc}")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Dump Vikunja swagger spec as markdown")
    parser.add_argument("--file", default=None, help="Path to swagger JSON file")
    parser.add_argument("--tag", default=None, help="Filter endpoints by tag (case-insensitive)")
    args = parser.parse_args()

    # Find the spec file
    if args.file:
        spec_path = Path(args.file)
    else:
        # Try common locations
        candidates = [
            Path("docs/vikunja-swagger.json"),
            Path("../docs/vikunja-swagger.json"),
            Path(__file__).parent.parent.parent.parent / "docs" / "vikunja-swagger.json",
        ]
        spec_path = next((p for p in candidates if p.exists()), None)
        if not spec_path:
            print("ERROR: Could not find vikunja-swagger.json. Use --file to specify.", file=sys.stderr)
            sys.exit(1)

    with open(spec_path) as f:
        spec = json.load(f)

    version = spec.get("info", {}).get("version", "unknown")
    base_path = spec.get("basePath", "/api/v1")

    print(f"# Vikunja API Endpoints (v{version})")
    print(f"\nBase path: `{base_path}`\n")
    print("---\n")

    # Group by tag
    tagged: dict[str, list[tuple[str, str, dict]]] = {}
    for path, methods in sorted(spec["paths"].items()):
        for method, details in methods.items():
            tags = details.get("tags", ["untagged"])
            primary_tag = tags[0]
            if args.tag and args.tag.lower() not in primary_tag.lower():
                continue
            tagged.setdefault(primary_tag, []).append((method, path, details))

    for tag in sorted(tagged.keys()):
        print(f"## {tag.title()}\n")
        for method, path, details in tagged[tag]:
            print(dump_endpoint(spec, method, path, details))

    # Print definitions summary
    if not args.tag:
        print("\n## Model Definitions\n")
        for name in sorted(spec.get("definitions", {}).keys()):
            defn = spec["definitions"][name]
            props = defn.get("properties", {})
            field_names = ", ".join(sorted(props.keys())[:8])
            if len(props) > 8:
                field_names += ", ..."
            print(f"- **{name}**: {field_names}")


if __name__ == "__main__":
    main()
