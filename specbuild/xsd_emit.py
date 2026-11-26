"""Emit an XSD from the model and prove a model-level round trip."""

from __future__ import annotations

import json
from pathlib import Path

from .xsd_import import import_all

_EMIT_TYPE = {
    "integer": "xs:int",
    "string": "xs:string",
    "boolean": "xs:boolean",
    "float": "xs:float",
    "double": "xs:double",
    "NMTOKEN": "xs:NMTOKEN",
}
_CARDINALITY = {
    "1": ("1", "1"),
    "?": ("0", "1"),
    "*": ("0", "unbounded"),
    "+": ("1", "unbounded"),
}


def emit_type(name: str | None) -> str:
    return _EMIT_TYPE.get(name or "", name or "xs:string")


def _esc(value) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _simple_types(modelset: dict) -> list[str]:
    lines: list[str] = []
    for name, node in sorted(modelset["enums"].items()):
        base = emit_type(node.get("base") or "NMTOKEN")
        lines.append(f'  <xs:simpleType name="{name}">')
        if node.get("multiple"):
            lines += ["    <xs:list>", "      <xs:simpleType>"]
            indent = "        "
            lines.append(f'{indent}<xs:restriction base="{base}">')
            for value in node.get("values", []):
                lines.append(f'{indent}  <xs:enumeration value="{_esc(value["name"])}"/>')
            lines += [f"{indent}</xs:restriction>", "      </xs:simpleType>", "    </xs:list>"]
        else:
            lines.append(f'    <xs:restriction base="{base}">')
            for value in node.get("values", []):
                lines.append(f'      <xs:enumeration value="{_esc(value["name"])}"/>')
            lines.append("    </xs:restriction>")
        lines.append("  </xs:simpleType>")
    for name, node in sorted(modelset["types"].items()):
        lines.append(f'  <xs:simpleType name="{name}">')
        if node.get("itemType"):
            lines.append(f'    <xs:list itemType="{node["itemType"]}"/>')
        elif node.get("union"):
            lines.append(f'    <xs:union memberTypes="{" ".join(node["union"])}"/>')
        else:
            base = emit_type(node.get("base") or "string")
            facets = node.get("facets") or {}
            if facets:
                lines.append(f'    <xs:restriction base="{base}">')
                for key in ("length", "minLength", "maxLength", "minInclusive", "maxInclusive"):
                    if key in facets:
                        lines.append(f'      <xs:{key} value="{_esc(facets[key])}"/>')
                if "pattern" in facets:
                    lines.append(f'      <xs:pattern value="{_esc(facets["pattern"])}"/>')
                lines.append("    </xs:restriction>")
            else:
                lines.append(f'    <xs:restriction base="{base}"/>')
        lines.append("  </xs:simpleType>")
    return lines


def _attribute(attribute: dict) -> list[str]:
    name = attribute["name"]
    use = ' use="required"' if attribute.get("required") else ""
    values = attribute.get("values") or {}
    if values.get("multiple"):
        return [
            f'      <xs:attribute name="{name}"{use}>',
            "        <xs:simpleType>",
            f'          <xs:list itemType="{values.get("from")}"/>',
            "        </xs:simpleType>",
            "      </xs:attribute>",
        ]
    if values.get("from"):
        return [f'      <xs:attribute name="{name}" type="{values["from"]}"{use}/>']
    if values.get("list"):
        lines = [
            f'      <xs:attribute name="{name}"{use}>',
            "        <xs:simpleType>",
            '          <xs:restriction base="xs:NMTOKEN">',
        ]
        for value in values["list"]:
            lines.append(f'            <xs:enumeration value="{_esc(value)}"/>')
        lines += ["          </xs:restriction>", "        </xs:simpleType>", "      </xs:attribute>"]
        return lines
    return [f'      <xs:attribute name="{name}" type="{emit_type(attribute.get("type"))}"{use}/>']


def _child(child: dict) -> str:
    minimum, maximum = _CARDINALITY.get(child.get("cardinality", "1"), ("1", "1"))
    return (
        f'      <xs:element ref="{child["name"]}" '
        f'minOccurs="{minimum}" maxOccurs="{maximum}"/>'
    )


def _element(node: dict) -> list[str]:
    flags = ""
    if node.get("abstract"):
        flags += ' abstract="true"'
    if node.get("substitutes"):
        flags += f' substitutionGroup="{node["substitutes"]}"'
    lines = [f'  <xs:element name="{node["name"]}"{flags}>', "    <xs:complexType>"]
    children = node.get("elements") or []
    if children:
        lines.append("      <xs:sequence>")
        lines += [_child(child) for child in children]
        lines.append("      </xs:sequence>")
    for attribute in node.get("attributes") or []:
        lines += _attribute(attribute)
    lines += ["    </xs:complexType>", "  </xs:element>"]
    return lines


def emit_document(modelset: dict, target_namespace: str = "http://www.CIP4.org/JDFSchema_2_0") -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!-- Generated from the JDF/XJDF model by specbuild. Do not edit. -->",
        (
            f'<xs:schema targetNamespace="{target_namespace}" '
            f'xmlns="{target_namespace}" xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'elementFormDefault="qualified" attributeFormDefault="unqualified">'
        ),
    ]
    lines += _simple_types(modelset)
    for _, node in sorted(modelset["elements"].items()):
        lines += _element(node)
    lines.append("</xs:schema>")
    return "\n".join(lines) + "\n"


def canonical(modelset: dict) -> str:
    return json.dumps(modelset, sort_keys=True, ensure_ascii=False)


def diff(a, b, path: str = "") -> list[str]:
    differences: list[str] = []
    if type(a) is not type(b):
        return [f"{path or '<root>'}: {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            child_path = f"{path}/{key}" if path else key
            if key not in a:
                differences.append(f"{child_path}: only in generated")
            elif key not in b:
                differences.append(f"{child_path}: only in original")
            else:
                differences += diff(a[key], b[key], child_path)
    elif isinstance(a, list):
        if len(a) != len(b):
            differences.append(f"{path}: length {len(a)} != {len(b)}")
        for index, (left, right) in enumerate(zip(a, b)):
            differences += diff(left, right, f"{path}[{index}]")
    elif a != b:
        differences.append(f"{path}: {a!r} != {b!r}")
    return differences


def roundtrip(source_xsd: Path, work_dir: Path) -> tuple[dict, dict, list[str], Path]:
    """Import -> emit XSD -> re-import; return (first, second, differences, xsd)."""
    first = import_all(source_xsd)
    document = emit_document(first)
    work_dir.mkdir(parents=True, exist_ok=True)
    generated = work_dir / f"{source_xsd.stem}.generated.xsd"
    generated.write_text(document, encoding="utf-8")
    second = import_all(generated)
    return first, second, diff(first, second), generated
