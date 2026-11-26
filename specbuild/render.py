"""Render model nodes as GitHub-flavoured Markdown tables."""

from __future__ import annotations

BEGIN = (
    "<!-- BEGIN GENERATED model:{name} - do not edit; "
    "edit model/{name}.yaml -->"
)
END = "<!-- END GENERATED model:{name} -->"


def _cell(text: str | None) -> str:
    text = (text or "").strip().replace("\r", "").replace("\n", " ")
    return text.replace("|", "\\|")


def _variant_tag(item: dict, parent: dict) -> str:
    variants = item.get("variants", parent.get("variants", ["jdf", "xjdf"]))
    selected = set(variants)
    if selected == {"jdf"}:
        return " *(JDF 1.x only)*"
    if selected == {"xjdf"}:
        return " *(XJDF only)*"
    return ""


def _attribute_row(model: dict, attribute: dict) -> str:
    name = attribute["name"]
    if attribute.get("required"):
        name += " (required)"
    name += _variant_tag(attribute, model)

    values = attribute.get("values") or {}
    if values.get("from"):
        data_type = "enumerations" if values.get("multiple") else "enumeration"
    elif values.get("list"):
        data_type = "enumeration"
    else:
        data_type = attribute.get("type", "")

    description = _cell(attribute.get("description", ""))
    if attribute.get("default"):
        description += f" Default value is: {_cell(attribute['default'])}."
    if values.get("list"):
        description += " Allowed values are: " + ", ".join(values["list"]) + "."
    if values.get("from"):
        description += f" Allowed values are from: {values['from']}."

    return f"| {_cell(name)} | {_cell(data_type)} | {description.strip()} |"


def _child_row(model: dict, child: dict) -> str:
    name = child["name"]
    cardinality = child.get("cardinality", "1")
    if cardinality != "1":
        name += f" {cardinality}"
    name += _variant_tag(child, model)
    return f"| {_cell(name)} | element | {_cell(child.get('description', ''))} |"


def render_node(model: dict) -> str:
    rows = [_attribute_row(model, attr) for attr in model.get("attributes", [])]
    rows += [_child_row(model, child) for child in model.get("elements", [])]
    if not rows:
        return "_No attributes or elements defined._"
    header = ["| Name | Data Type | Description |", "| --- | --- | --- |"]
    return "\n".join(header + rows)


def render_enum(model: dict) -> str:
    values = model.get("values", [])
    if not values:
        return "_No values defined._"
    rows = ["| Value | Description |", "| --- | --- |"]
    for value in values:
        rows.append(f"| {_cell(value['name'])} | {_cell(value.get('description', ''))} |")
    return "\n".join(rows)


def render(model: dict) -> str:
    if model.get("kind") == "enum":
        return render_enum(model)
    return render_node(model)


def block(name: str, body: str) -> str:
    return f"{BEGIN.format(name=name)}\n{body}\n{END.format(name=name)}"
