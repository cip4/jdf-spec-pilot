"""Import an XSD into the YAML model (staging).

Inheritance is flattened so that each element node is self-contained, which
matches the per-element tables in the specification. Substitution groups and
abstract flags are preserved.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

XS = "{http://www.w3.org/2001/XMLSchema}"

_TYPE_ALIASES = {
    "integer": ("int", "integer", "Integer"),
    "string": ("string", "String"),
    "boolean": ("boolean", "Boolean"),
    "float": ("float", "Float", "Number"),
    "double": ("double", "decimal"),
    "NMTOKEN": ("NMTOKEN",),
}
_ALIAS_TO_KIND = {
    alias: kind for kind, aliases in _TYPE_ALIASES.items() for alias in aliases
}


def local(name: str | None) -> str:
    return name.split(":")[-1] if name else (name or "")


def normalize_type(name: str | None) -> str | None:
    if not name:
        return name
    return _ALIAS_TO_KIND.get(name) or _ALIAS_TO_KIND.get(local(name)) or local(name)


def _facets(restriction: ET.Element) -> dict:
    result: dict = {}
    for tag in ("length", "minLength", "maxLength", "pattern", "minInclusive", "maxInclusive"):
        found = restriction.find(XS + tag)
        if found is not None:
            result[tag] = found.get("value")
    return result


def _cardinality(min_occurs: str, max_occurs: str) -> str:
    if min_occurs == "0" and max_occurs == "1":
        return "?"
    if min_occurs == "0" and max_occurs == "unbounded":
        return "*"
    if min_occurs == "1" and max_occurs == "unbounded":
        return "+"
    if min_occurs == "1" and max_occurs == "1":
        return "1"
    return "*" if min_occurs == "0" else "+"


def _parse_child(element: ET.Element) -> dict:
    name = local(element.get("ref") or element.get("name"))
    card = _cardinality(element.get("minOccurs", "1"), element.get("maxOccurs", "1"))
    node: dict = {"name": name}
    if card != "1":
        node["cardinality"] = card
    return node


def _parse_attribute(element: ET.Element, simple_kinds: dict) -> dict:
    node: dict = {"name": element.get("name")}
    declared = element.get("type")
    inline = element.find(XS + "simpleType")

    if declared:
        kind = local(declared)
        declared_kind = simple_kinds.get(kind, (None, None))
        if declared_kind[0] == "enum":
            node["type"] = "enumeration"
            node["values"] = {"from": kind}
        elif declared_kind[0] == "list" and simple_kinds.get(declared_kind[1], (None, None))[0] == "enum":
            node["type"] = "enumerations"
            node["values"] = {"from": declared_kind[1], "multiple": True}
        else:
            node["type"] = normalize_type(declared)
    elif inline is not None:
        restriction = inline.find(XS + "restriction")
        list_type = inline.find(XS + "list")
        if list_type is not None:
            node["type"] = "enumerations"
            node["values"] = {"from": local(list_type.get("itemType")), "multiple": True}
        elif restriction is not None:
            values = [e.get("value") for e in restriction.findall(XS + "enumeration")]
            if values:
                node["type"] = "enumeration"
                node["values"] = {"list": values}
            else:
                node["type"] = normalize_type(restriction.get("base"))
        else:
            node["type"] = "string"
    else:
        node["type"] = "string"

    if element.get("use") == "required":
        node["required"] = True
    return node


def _extension(complex_type: ET.Element) -> ET.Element | None:
    for tag in ("complexContent", "simpleContent"):
        found = complex_type.find(f"{XS}{tag}/{XS}extension")
        if found is not None:
            return found
    return None


def _walk_children(node: ET.Element) -> list[dict]:
    children: list[dict] = []
    for child in node:
        if child.tag in (XS + "sequence", XS + "choice"):
            children.extend(_walk_children(child))
        elif child.tag == XS + "element" and (child.get("ref") or child.get("name")):
            children.append(_parse_child(child))
    return children


def _members(container: ET.Element, simple_kinds: dict) -> tuple[list, list]:
    attributes = [_parse_attribute(a, simple_kinds) for a in container.findall(XS + "attribute")]
    children: list[dict] = []
    for child in container:
        if child.tag in (XS + "sequence", XS + "choice"):
            children.extend(_walk_children(child))
    return attributes, children


def _collect_members(complex_type, complex_types, simple_kinds) -> tuple[list, list]:
    if complex_type is None:
        return [], []
    extension = _extension(complex_type)
    if extension is not None:
        base_attributes, base_children = [], []
        base = extension.get("base")
        if base:
            base_type = complex_types.get(local(base))
            if base_type is not None:
                base_attributes, base_children = _collect_members(base_type, complex_types, simple_kinds)
        own_attributes, own_children = _members(extension, simple_kinds)
        return base_attributes + own_attributes, base_children + own_children
    return _members(complex_type, simple_kinds)


def _dedupe(items: list[dict]) -> list[dict]:
    order: list[str] = []
    latest: dict[str, dict] = {}
    for item in items:
        if item["name"] not in latest:
            order.append(item["name"])
        latest[item["name"]] = item
    return [latest[name] for name in order]


def _import_element(element: ET.Element, complex_types: dict, simple_kinds: dict) -> dict:
    node: dict = {"name": element.get("name"), "kind": "element"}
    if element.get("abstract") == "true":
        node["abstract"] = True
    if element.get("substitutionGroup"):
        node["substitutes"] = local(element.get("substitutionGroup"))

    complex_type = element.find(XS + "complexType")
    if complex_type is None and element.get("type"):
        complex_type = complex_types.get(local(element.get("type")))

    attributes, children = _collect_members(complex_type, complex_types, simple_kinds)
    attributes, children = _dedupe(attributes), _dedupe(children)
    if attributes:
        node["attributes"] = attributes
    if children:
        node["elements"] = children
    return node


def _enum_node(name: str, restriction: ET.Element, multiple: bool = False) -> dict:
    node: dict = {
        "name": name,
        "kind": "enum",
        "base": normalize_type(restriction.get("base")),
        "values": [{"name": e.get("value")} for e in restriction.findall(XS + "enumeration")],
    }
    if multiple:
        node["multiple"] = True
    return node


def _import_simple_type(simple_type: ET.Element) -> tuple[str, dict]:
    name = simple_type.get("name")
    restriction = simple_type.find(XS + "restriction")
    list_type = simple_type.find(XS + "list")
    union = simple_type.find(XS + "union")

    if restriction is not None:
        base = restriction.get("base")
        values = [e.get("value") for e in restriction.findall(XS + "enumeration")]
        if values:
            return "enums", _enum_node(name, restriction)
        node: dict = {"name": name, "kind": "type", "base": normalize_type(base)}
        facets = _facets(restriction)
        if facets:
            node["facets"] = facets
        return "types", node
    if list_type is not None:
        # A list of an inline enumeration behaves like an enumeration of values.
        nested = list_type.find(XS + "simpleType")
        if nested is not None:
            nested_restriction = nested.find(XS + "restriction")
            if nested_restriction is not None and nested_restriction.find(XS + "enumeration") is not None:
                return "enums", _enum_node(name, nested_restriction, multiple=True)
        return "types", {
            "name": name,
            "kind": "type",
            "itemType": local(list_type.get("itemType")),
        }
    if union is not None:
        return "types", {
            "name": name,
            "kind": "type",
            "union": [local(m) for m in (union.get("memberTypes") or "").split()],
        }
    return "types", {"name": name, "kind": "type", "base": "string"}


def import_all(xsd_path: Path) -> dict:
    """Return ``{elements, enums, types}`` keyed by name."""
    root = ET.parse(xsd_path).getroot()
    complex_types = {
        ct.get("name"): ct for ct in root.findall(XS + "complexType") if ct.get("name")
    }

    simple_kinds: dict[str, tuple[str, str | None]] = {}
    simple_types = root.findall(XS + "simpleType")
    for simple_type in simple_types:
        name = simple_type.get("name")
        restriction = simple_type.find(XS + "restriction")
        list_type = simple_type.find(XS + "list")
        if restriction is not None and restriction.find(XS + "enumeration") is not None:
            simple_kinds[name] = ("enum", None)
        elif list_type is not None:
            simple_kinds[name] = ("list", local(list_type.get("itemType")))
        else:
            simple_kinds[name] = ("type", None)

    result: dict = {"elements": {}, "enums": {}, "types": {}}
    for element in root.findall(XS + "element"):
        name = element.get("name")
        if name:
            result["elements"][name] = _import_element(element, complex_types, simple_kinds)
    for simple_type in simple_types:
        bucket, node = _import_simple_type(simple_type)
        result[bucket][node["name"]] = node
    return result


def write_staging(modelset: dict, out_dir: Path, source: str) -> dict:
    """Write imported nodes as YAML under ``out_dir/{elements,enums,types}``."""
    counts = {}
    for bucket in ("elements", "enums", "types"):
        folder = out_dir / bucket
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.glob("*.yaml"):
            stale.unlink()
        for name, node in sorted(modelset[bucket].items()):
            text = yaml.safe_dump(node, sort_keys=False, allow_unicode=True, width=1000)
            (folder / f"{name}.yaml").write_text(text, encoding="utf-8")
        counts[bucket] = len(modelset[bucket])
    (out_dir / "manifest.json").write_text(
        json.dumps({"source": source, "counts": counts}, indent=2) + "\n",
        encoding="utf-8",
    )
    return counts
