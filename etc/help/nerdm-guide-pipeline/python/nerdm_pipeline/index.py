"""Build the compact structured NERDm guide index."""

from __future__ import annotations

from typing import Any


INDEX_VERSION = "0.1"
MODEL_PATH = "nerdm-doc-model.json"


def build_guide_index(model: dict[str, Any]) -> dict[str, Any]:
    anchors = _canonical_anchor_records(model)
    inherited_references = _inherited_reference_records(model)

    return {
        "indexVersion": INDEX_VERSION,
        "title": model["title"],
        "sourceModel": {
            "path": MODEL_PATH,
            "modelVersion": model["modelVersion"],
            "source": model["generatedFrom"]["source"],
        },
        "counts": {
            "typeGroups": len(model["typeGroups"]),
            "types": len(model["types"]),
            "properties": sum(len(item["properties"]) for item in model["types"]),
            "inheritedProperties": len(inherited_references),
            "anchors": len(anchors),
            "inheritedReferences": len(inherited_references),
        },
        "groups": _groups(model),
        "types": [_compact_type(item) for item in model["types"]],
        "anchors": anchors,
        "inheritedReferences": inherited_references,
    }


def _groups(model: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": group["id"],
            "label": group["label"],
            "anchor": group["anchor"],
            "types": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "anchor": item["anchor"],
                    "propertyCount": len(item["properties"]),
                }
                for item in model["types"]
                if item["group"] == group["id"]
            ],
        }
        for group in model["typeGroups"]
    ]


def _compact_type(item: dict[str, Any]) -> dict[str, Any]:
    properties = item["properties"]
    inherited = [prop for prop in properties if prop.get("inheritedFrom")]

    return {
        "id": item["id"],
        "name": item["name"],
        "label": item["label"],
        "group": item["group"],
        "anchor": item["anchor"],
        "brief": item["brief"],
        "valueType": item["displayType"],
        "inheritsFrom": item.get("inheritsFrom") or [],
        "propertyCount": len(properties),
        "ownPropertyCount": len(properties) - len(inherited),
        "inheritedPropertyCount": len(inherited),
        "usage": item.get("usage") or [],
        "properties": [_compact_property(prop) for prop in properties],
    }


def _compact_property(prop: dict[str, Any]) -> dict[str, Any]:
    value = prop["value"]
    compact: dict[str, Any] = {
        "name": prop["name"],
        "label": prop["label"],
        "anchor": prop["anchor"],
        "brief": prop["brief"],
        "valueType": value["display"],
        "jsonType": value["jsonType"],
        "required": prop["required"],
        "inheritedFrom": prop.get("inheritedFrom"),
    }

    if value.get("itemType") is not None:
        compact["itemType"] = value["itemType"]
    if value.get("objectType") is not None:
        compact["objectType"] = value["objectType"]
    if prop.get("allowedValues") is not None:
        compact["allowedValues"] = prop["allowedValues"]

    return compact


def _canonical_anchor_records(model: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for group in model["typeGroups"]:
        records.append(
            {
                "anchor": group["anchor"],
                "kind": "type-group",
                "label": group["label"],
            }
        )

    for item in model["types"]:
        records.append(
            {
                "anchor": item["anchor"],
                "kind": "type",
                "label": item["label"],
                "type": item["name"],
            }
        )

        for prop in item["properties"]:
            if prop.get("inheritedFrom") is not None:
                continue
            records.append(
                {
                    "anchor": prop["anchor"],
                    "kind": "property",
                    "label": prop["label"],
                    "type": item["name"],
                    "property": prop["name"],
                }
            )

    return _unique_by_anchor(records)


def _inherited_reference_records(model: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for item in model["types"]:
        for prop in item["properties"]:
            inherited = prop.get("inheritedFrom")
            if inherited is None:
                continue
            records.append(
                {
                    "type": item["name"],
                    "property": prop["name"],
                    "label": prop["label"],
                    "sourceType": inherited["type"],
                    "sourceProperty": inherited["property"],
                    "sourceAnchor": inherited["anchor"],
                }
            )

    return records


def _unique_by_anchor(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for record in records:
        anchor = record["anchor"]
        if anchor in seen:
            continue
        seen.add(anchor)
        unique.append(record)

    return unique
