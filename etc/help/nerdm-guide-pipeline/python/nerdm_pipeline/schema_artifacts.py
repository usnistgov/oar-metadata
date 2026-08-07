"""Helpers for publishing schema metadata in the generated guide."""

from __future__ import annotations

from typing import Any


DEFAULT_SCHEMA_HREF = "../nerdm-schema/nerdm-schema.json"


def build_schema_artifact(
    schema: dict[str, Any],
    *,
    href: str = DEFAULT_SCHEMA_HREF,
) -> dict[str, str]:
    """Return display metadata for the current NERDm JSON Schema artifact."""

    version = _schema_version(schema)
    return {
        "href": href,
        "version": version,
    }


def _schema_version(schema: dict[str, Any]) -> str:
    identifier = schema.get("@id") or schema.get("id")
    if not isinstance(identifier, str):
        return ""

    normalized = identifier.rstrip("#/")
    if "/" not in normalized:
        return ""
    return normalized.rsplit("/", 1)[1]
