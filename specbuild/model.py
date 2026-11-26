"""Load and validate the YAML data model."""

from __future__ import annotations

from pathlib import Path

import yaml

SCHEMA_FILE = "model.schema.json"


def repo_root_default() -> Path:
    """Return the repository root (the parent of this package)."""
    return Path(__file__).resolve().parents[1]


def load_schema(root: Path) -> dict:
    import json

    return json.loads((root / "model" / SCHEMA_FILE).read_text(encoding="utf-8"))


def iter_model_files(root: Path):
    return sorted((root / "model").rglob("*.yaml"))


def load_model(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return data


def find_model(root: Path, name: str) -> dict:
    """Resolve a model name such as ``elements/Icon`` to its YAML file."""
    path = root / "model" / (name + ".yaml")
    if not path.exists():
        raise FileNotFoundError(f"no model file for '{name}' (expected {path})")
    return load_model(path)


def validate(root: Path) -> list[str]:
    """Validate every model file against the meta-schema. Return error strings."""
    import jsonschema

    schema = load_schema(root)
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for path in iter_model_files(root):
        try:
            data = load_model(path)
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            errors.append(f"{path.relative_to(root)}: cannot parse YAML: {exc}")
            continue
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            location = "/".join(str(part) for part in err.path) or "<root>"
            errors.append(f"{path.relative_to(root)}: {location}: {err.message}")
    return errors
