"""Build the structured NERDm documentation model from nerdm-view.json."""

from __future__ import annotations

from typing import Any


MODEL_VERSION = "0.1"
SOURCE_PATH = "etc/help/nerdm-view.json"
GENERATOR_PATH = (
    "etc/help/nerdm-guide-pipeline/python/nerdm_pipeline/model.py"
)
GROUP_ORDER = ("Resource", "Component", "Other")


def build_doc_model(source: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized documentation model from the current schema view."""

    groups = _type_groups(source)
    types = _order_types(
        [_type_doc(entry, index) for index, entry in enumerate(source["types"])],
        groups,
    )

    return {
        "modelVersion": MODEL_VERSION,
        "title": str(source.get("title") or "NERDm Reader's Guide"),
        "description": _string_list(source.get("description")),
        "generatedFrom": {
            "source": SOURCE_PATH,
            "sourceFormat": "nerdm-view",
            "generator": GENERATOR_PATH,
            "notes": [
                "Generated from the current NERDm schema view without "
                "changing production guide files.",
                "Required-field metadata is not present in nerdm-view.json "
                "and is therefore emitted as false in the generated model.",
            ],
        },
        "typeGroups": groups,
        "types": types,
        "toc": _toc(groups, types),
        "glossary": [],
    }


def _type_doc(entry: dict[str, Any], index: int) -> dict[str, Any]:
    type_name = str(entry.get("name") or "")
    group = str(entry.get("cat") or "Other")
    description = _string_list(entry.get("description"))

    return {
        "id": type_name,
        "name": type_name,
        "label": type_name,
        "group": group,
        "valueType": str(entry.get("jtype") or "unknown"),
        "displayType": _render_template(entry.get("show") or ""),
        "description": description,
        "brief": _text(entry.get("brief") or _first(description)),
        "anchor": _anchor(type_name),
        "usage": _usage_list(entry.get("use")),
        "inheritsFrom": _string_list(entry.get("inheritsFrom")),
        "properties": (
            _own_properties(entry, type_name, index)
            + _inherited_properties(entry, type_name, index)
        ),
        "source": _source_ref(f"/types/{index}"),
    }


def _order_types(
    types: list[dict[str, Any]],
    groups: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Keep configured type groups first while preserving source order in groups."""

    group_order = {group["id"]: index for index, group in enumerate(groups)}
    return [
        item
        for _, item in sorted(
            enumerate(types),
            key=lambda entry: (
                group_order.get(entry[1]["group"], len(group_order)),
                entry[0],
            ),
        )
    ]


def _own_properties(
    entry: dict[str, Any],
    type_name: str,
    type_index: int,
) -> list[dict[str, Any]]:
    properties = entry.get("properties") or []
    return [
        _property_doc(
            prop,
            owner=type_name,
            inherited_from=None,
            source_pointer=f"/types/{type_index}/properties/{prop_index}",
        )
        for prop_index, prop in enumerate(properties)
    ]


def _inherited_properties(
    entry: dict[str, Any],
    type_name: str,
    type_index: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for group_index, group in enumerate(entry.get("inheritedProperties") or []):
        source_type = str(group.get("from") or "")
        for prop_index, prop in enumerate(group.get("properties") or []):
            property_name = str(prop.get("name") or "")
            records.append(
                _property_doc(
                    prop,
                    owner=type_name,
                    inherited_from={
                        "type": source_type,
                        "property": property_name,
                        "anchor": _anchor(source_type, property_name),
                    },
                    source_pointer=(
                        f"/types/{type_index}/inheritedProperties/"
                        f"{group_index}/properties/{prop_index}"
                    ),
                )
            )

    return records


def _property_doc(
    prop: dict[str, Any],
    *,
    owner: str,
    inherited_from: dict[str, str] | None,
    source_pointer: str,
) -> dict[str, Any]:
    """Return the normalized model record for an owned or inherited property."""

    property_name = str(prop.get("name") or "")
    source_type = str(prop.get("parent") or owner)
    description = _string_list(prop.get("description"))

    record: dict[str, Any] = {
        "id": f"{owner}.{property_name}",
        "name": property_name,
        "label": str(prop.get("label") or property_name),
        "parentType": owner,
        "value": _value_descriptor(prop.get("type") or {}),
        "description": description,
        "brief": _text(prop.get("brief") or _first(description)),
        # Inherited properties link back to the original declaring type. This
        # avoids duplicate anchors when several child types inherit the same
        # parent property.
        "anchor": (
            _anchor(owner, property_name)
            if inherited_from is None
            else _anchor(source_type, property_name)
        ),
        "required": False,
        "inheritedFrom": inherited_from,
        "schemaNotes": _string_list(prop.get("schema_notes")),
        "readerNotes": _string_list(prop.get("notes")),
        "examples": _string_list(prop.get("examples")),
        "source": _source_ref(source_pointer),
    }

    if prop.get("allowed") is not None:
        record["allowedValues"] = [
            {"value": str(value), "description": _text(description)}
            for value, description in prop["allowed"].items()
        ]

    return record


def _value_descriptor(value: dict[str, Any]) -> dict[str, Any]:
    raw_type = value.get("type", "unknown")
    descriptor: dict[str, Any] = {
        "jsonType": _json_type(raw_type),
        "display": _render_template(value.get("show") or ""),
    }

    item_type = value.get("each") or _first_nested_type(raw_type, "array", "each")
    object_type = value.get("of") or _first_nested_type(raw_type, "object", "of")

    if item_type is not None:
        descriptor["itemType"] = str(item_type)
    if object_type is not None:
        descriptor["objectType"] = str(object_type)

    return descriptor


def _json_type(raw_type: Any) -> str:
    if isinstance(raw_type, list):
        values = sorted(
            {
                str(item.get("type") if isinstance(item, dict) else item)
                for item in raw_type
            }
        )
        return " | ".join(values)

    return str(raw_type)


def _first_nested_type(raw_type: Any, json_type: str, key: str) -> Any | None:
    if not isinstance(raw_type, list):
        return None

    for item in raw_type:
        if isinstance(item, dict) and item.get("type") == json_type:
            if item.get(key) is not None:
                return item[key]

    return None


def _usage_list(usage: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": str(item.get("id") or ""),
            "template": str(item.get("template") or ""),
            "data": {
                str(key): str(value)
                for key, value in (item.get("data") or {}).items()
            },
        }
        for item in _array(usage)
        if isinstance(item, dict)
    ]


def _type_groups(source: dict[str, Any]) -> list[dict[str, str]]:
    groups = {str(entry.get("cat") or "Other") for entry in source["types"]}
    ordered = [group for group in GROUP_ORDER if group in groups]
    ordered.extend(sorted(groups - set(ordered)))

    return [
        {
            "id": group,
            "label": group,
            "description": _type_group_description(group),
            "anchor": f"group-{group}",
        }
        for group in ordered
    ]


def _type_group_description(group: str) -> str:
    if group == "Resource":
        return "Resource-level metadata types."
    if group == "Component":
        return (
            "Component-level metadata types for files, pages, tools, and "
            "related resource parts."
        )
    return "Supporting named types used by resource and component metadata."


def _toc(groups: list[dict[str, str]], types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "toc-schema-reference",
            "label": "Schema Reference",
            "anchor": "schema-reference",
            "level": 1,
            "children": [
                {
                    "id": f"toc-group-{group['id']}",
                    "label": group["label"],
                    "anchor": group["anchor"],
                    "level": 2,
                    "children": [
                        {
                            "id": f"toc-type-{item['id']}",
                            "label": item["label"],
                            "anchor": item["anchor"],
                            "level": 3,
                        }
                        for item in types
                        if item["group"] == group["id"]
                    ],
                }
                for group in groups
            ],
        }
    ]


def _source_ref(pointer: str) -> dict[str, str]:
    return {"path": SOURCE_PATH, "jsonPointer": pointer}


def _anchor(type_name: str, property_name: str | None = None) -> str:
    if property_name:
        return f"{type_name}.{property_name}"
    return type_name


def _render_template(value: Any) -> str:
    """Render the small template objects used by the legacy view JSON."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "template" in value:
        rendered = str(value["template"])
        for key, replacement in (value.get("data") or {}).items():
            rendered = rendered.replace("{" + str(key) + "}", str(replacement))
        return rendered
    return str(value)


def _string_list(value: Any) -> list[str]:
    return [_text(item) for item in _array(value) if item is not None]


def _array(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _first(values: list[str]) -> str:
    return values[0] if values else ""
