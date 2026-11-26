"""Compare the staged XSD import with the current model.

The specification always wins. This report is for the committee: it shows where
the XSD import disagrees with the model so that each difference can be resolved
in favour of the specification text.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ELEMENT_FOLDERS = ("elements", "resources", "messages")
BUCKET_FOLDERS = {
    "elements": ELEMENT_FOLDERS,
    "enums": ("enums",),
    "types": ("types",),
}


def _load_folder(folder: Path) -> dict:
    nodes: dict = {}
    if not folder.exists():
        return nodes
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("name"):
            nodes[data["name"]] = data
    return nodes


def _model_set(root: Path) -> dict:
    model = root / "model"
    result = {}
    for bucket, folders in BUCKET_FOLDERS.items():
        nodes: dict = {}
        for folder in folders:
            nodes.update(_load_folder(model / folder))
        result[bucket] = nodes
    return result


def _staged_set(root: Path) -> dict:
    staged = root / "import" / "xsd" / "xjdf"
    return {bucket: _load_folder(staged / bucket) for bucket in BUCKET_FOLDERS}


def _variants(node: dict) -> set:
    return set(node.get("variants", ["jdf", "xjdf"]))


def _values(attribute: dict):
    values = attribute.get("values") or {}
    return (values.get("from"), tuple(values.get("list") or ()), bool(values.get("multiple")))


def _diff_node(model: dict, imported: dict) -> list[str]:
    lines: list[str] = []
    if _variants(model) != _variants(imported):
        lines.append(f"variants: model {sorted(_variants(model))} vs xsd {sorted(_variants(imported))}")
    if bool(model.get("abstract")) != bool(imported.get("abstract")):
        lines.append(f"abstract: model {bool(model.get('abstract'))} vs xsd {bool(imported.get('abstract'))}")
    if model.get("substitutes") != imported.get("substitutes"):
        lines.append(f"substitutes: model {model.get('substitutes')} vs xsd {imported.get('substitutes')}")

    model_attrs = {a["name"]: a for a in model.get("attributes", [])}
    xsd_attrs = {a["name"]: a for a in imported.get("attributes", [])}
    for name in sorted(set(model_attrs) | set(xsd_attrs)):
        if name not in model_attrs:
            lines.append(f"attribute {name}: only in XSD")
            continue
        if name not in xsd_attrs:
            lines.append(f"attribute {name}: only in model")
            continue
        left, right = model_attrs[name], xsd_attrs[name]
        for field in ("type", "required"):
            if left.get(field) != right.get(field):
                lines.append(f"attribute {name}.{field}: model {left.get(field)} vs xsd {right.get(field)}")
        if _values(left) != _values(right):
            lines.append(f"attribute {name}.values: model {_values(left)} vs xsd {_values(right)}")
        if _variants(left) != _variants(right):
            lines.append(f"attribute {name}.variants: model {sorted(_variants(left))} vs xsd {sorted(_variants(right))}")

    model_children = {c["name"]: c for c in model.get("elements", [])}
    xsd_children = {c["name"]: c for c in imported.get("elements", [])}
    for name in sorted(set(model_children) | set(xsd_children)):
        if name not in model_children:
            lines.append(f"element {name}: only in XSD")
            continue
        if name not in xsd_children:
            lines.append(f"element {name}: only in model")
            continue
        left, right = model_children[name], xsd_children[name]
        if left.get("cardinality", "1") != right.get("cardinality", "1"):
            lines.append(
                f"element {name}.cardinality: model {left.get('cardinality', '1')} "
                f"vs xsd {right.get('cardinality', '1')}"
            )
        if _variants(left) != _variants(right):
            lines.append(f"element {name}.variants: model {sorted(_variants(left))} vs xsd {sorted(_variants(right))}")

    if model.get("kind") == "enum":
        model_values = [v["name"] for v in model.get("values", [])]
        xsd_values = [v["name"] for v in imported.get("values", [])]
        if set(model_values) != set(xsd_values):
            lines.append(f"values: model {model_values} vs xsd {xsd_values}")
    return lines


def reconcile(root: Path) -> tuple[Path, dict]:
    model = _model_set(root)
    staged = _staged_set(root)
    summary = {}
    sections: list[str] = []

    for bucket in BUCKET_FOLDERS:
        model_nodes = model[bucket]
        xsd_nodes = staged[bucket]
        common = sorted(set(model_nodes) & set(xsd_nodes))
        model_only = sorted(set(model_nodes) - set(xsd_nodes))
        xsd_only = sorted(set(xsd_nodes) - set(model_nodes))
        summary[bucket] = {
            "model": len(model_nodes),
            "xsd": len(xsd_nodes),
            "common": len(common),
            "model_only": model_only,
            "xsd_only_count": len(xsd_only),
            "xsd_only_sample": xsd_only[:20],
        }
        if common:
            sections.append(f"### {bucket}\n")
            for name in common:
                differences = _diff_node(model_nodes[name], xsd_nodes[name])
                if differences:
                    sections.append(f"#### {name}\n")
                    sections += [f"- {line}" for line in differences]
                    sections.append("")

    lines = [
        "# Reconciliation report: XSD import vs model",
        "",
        "The specification (MIF tables) is the source of truth. Each difference",
        "below is resolved in favour of the specification text.",
        "",
        "## Summary",
        "",
        "| Bucket | Model | XSD | Common | Model only | XSD only |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for bucket, data in summary.items():
        lines.append(
            f"| {bucket} | {data['model']} | {data['xsd']} | {data['common']} | "
            f"{len(data['model_only'])} | {data['xsd_only_count']} |"
        )
    lines += ["", "## Differences in common nodes", ""]
    lines += sections or ["No differences."]
    lines += ["", "## Model-only nodes", ""]
    for bucket, data in summary.items():
        if data["model_only"]:
            lines.append(f"- {bucket}: {', '.join(data['model_only'])}")
    lines += ["", "## XSD-only nodes (first 20 per bucket)", ""]
    for bucket, data in summary.items():
        if data["xsd_only_sample"]:
            lines.append(f"- {bucket}: {', '.join(data['xsd_only_sample'])}")

    report = root / "import" / "reconcile-report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report, summary
