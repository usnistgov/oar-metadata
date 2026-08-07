"""Load and validate curated guide data inputs."""

from __future__ import annotations

from typing import Any

from .io import load_json


def load_curated_data(
    *,
    record_examples_path: str,
    model: dict[str, Any],
) -> dict[str, Any]:
    """Return validated curated data for optional rendered guide sections."""

    record_examples = load_json(record_examples_path)
    type_names = {item["name"] for item in model["types"]}

    _validate_record_examples(record_examples, type_names)

    return {
        "recordExamples": record_examples,
    }


def _validate_record_examples(data: dict[str, Any], type_names: set[str]) -> None:
    """Ensure example cards have required links and valid type references."""

    errors: list[str] = []

    examples = data.get("examples")
    if not isinstance(examples, list):
        raise ValueError("Invalid record example data: examples must be a list")

    for example in examples:
        label = str(example.get("label") or example.get("id") or "unknown example")
        for field in ["title", "summary", "recordUrl", "landingPageUrl"]:
            if not str(example.get(field) or "").strip():
                errors.append(f"{label}: missing {field}")

        for url_field in ["recordUrl", "landingPageUrl"]:
            value = str(example.get(url_field) or "")
            if value and not value.startswith(("http://", "https://")):
                errors.append(f"{label}: {url_field} must be an HTTP URL")

        for name in example.get("types") or []:
            if str(name) not in type_names:
                errors.append(f"{label}: unknown type {name}")

    if errors:
        raise ValueError("Invalid record example data:\n  " + "\n  ".join(errors))
