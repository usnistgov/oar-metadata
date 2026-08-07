"""Validation helpers for generated NERDm guide previews."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any


ID_PATTERN = re.compile(r"^[A-Za-z0-9@][A-Za-z0-9_.:@-]*$")
ANCHOR_PATTERN = re.compile(r"^[A-Za-z@][A-Za-z0-9_.:@-]*$")


@dataclass(frozen=True)
class HtmlValidationResult:
    """Structural checks for a generated HTML document."""

    duplicate_ids: list[str]
    unresolved_fragments: list[str]
    csp_issues: list[str]
    id_count: int
    fragment_link_count: int


class _GuideHtmlInspector(HTMLParser):
    """Collect anchors, same-page links, and CSP-sensitive constructs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.fragment_links: list[str] = []
        self.csp_issues: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self._inspect_tag(tag, attrs)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self._inspect_tag(tag, attrs)

    def _inspect_tag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag_name = tag.lower()
        line, column = self.getpos()

        if tag_name == "script":
            self.csp_issues.append(f"{line}:{column}: script element")

        for name, value in attrs:
            attr = name.lower()
            attr_value = value or ""
            normalized_value = attr_value.strip().lower()

            if attr == "id" and attr_value:
                self.ids.append(attr_value)
            elif attr == "href" and attr_value.startswith("#"):
                self.fragment_links.append(attr_value[1:])

            if attr == "style":
                self.csp_issues.append(f"{line}:{column}: inline style attribute")
            elif attr.startswith("on"):
                self.csp_issues.append(f"{line}:{column}: inline event attribute {name}")
            elif normalized_value.startswith("javascript:"):
                self.csp_issues.append(f"{line}:{column}: javascript URL in {name}")


def validate_model_contract(
    model: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate the generated documentation model without external packages."""

    issues: list[str] = []

    _expect_object(model, "<root>", issues)
    if issues:
        _raise_model_issues(issues)

    _check_keys(
        model,
        "<root>",
        {
            "modelVersion",
            "title",
            "description",
            "generatedFrom",
            "typeGroups",
            "types",
            "toc",
        },
        {"glossary"},
        issues,
    )
    _expect_string(model.get("modelVersion"), "modelVersion", issues)
    _expect_string(model.get("title"), "title", issues)
    _expect_string_array(model.get("description"), "description", issues)
    _validate_generated_from(model.get("generatedFrom"), "generatedFrom", issues)
    _validate_type_groups(model.get("typeGroups"), "typeGroups", issues)
    _validate_types(model.get("types"), "types", issues)
    _validate_toc(model.get("toc"), "toc", issues)
    if "glossary" in model:
        _validate_glossary(model.get("glossary"), "glossary", issues)

    _validate_model_relationships(model, issues)

    if schema is not None:
        _expect_object(schema, "schema", issues)
        if schema.get("title") != "NERDm Documentation Model":
            issues.append("schema.title: expected NERDm Documentation Model")

    if issues:
        _raise_model_issues(issues)


def validate_generated_html(path: str | Path) -> HtmlValidationResult:
    """Validate generated HTML IDs, fragment links, and CSP-sensitive markup."""

    html_path = Path(path)
    inspector = _GuideHtmlInspector()
    inspector.feed(html_path.read_text(encoding="utf-8"))

    id_counts = Counter(inspector.ids)
    ids = set(inspector.ids)

    return HtmlValidationResult(
        duplicate_ids=sorted(id_ for id_, count in id_counts.items() if count > 1),
        unresolved_fragments=sorted(
            fragment for fragment in set(inspector.fragment_links) if fragment not in ids
        ),
        csp_issues=inspector.csp_issues,
        id_count=len(inspector.ids),
        fragment_link_count=len(inspector.fragment_links),
    )


def raise_for_html_validation_errors(result: HtmlValidationResult) -> None:
    """Raise a build error when generated HTML validation found blocking issues."""

    failures: list[str] = []

    if result.duplicate_ids:
        failures.append("Duplicate IDs:\n  " + "\n  ".join(result.duplicate_ids))
    if result.unresolved_fragments:
        failures.append(
            "Unresolved fragment links:\n  "
            + "\n  ".join(result.unresolved_fragments)
        )
    if result.csp_issues:
        failures.append("CSP-sensitive markup:\n  " + "\n  ".join(result.csp_issues))

    if failures:
        raise RuntimeError("\n\n".join(failures))


def validate_css_files(paths: list[str | Path]) -> list[str]:
    """Check generated CSS files for URL patterns that would undermine CSP."""

    issues: list[str] = []
    forbidden = ("javascript:", "expression(")

    for path in paths:
        css_path = Path(path)
        text = css_path.read_text(encoding="utf-8").lower()
        for pattern in forbidden:
            if pattern in text:
                issues.append(f"{css_path}: contains {pattern}")

    return issues


def _validate_generated_from(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_object(value, path, issues):
        return
    _check_keys(value, path, {"source", "sourceFormat"}, {"generator", "notes"}, issues)
    _expect_string(value.get("source"), f"{path}.source", issues)
    _expect_string(value.get("sourceFormat"), f"{path}.sourceFormat", issues)
    if value.get("sourceFormat") not in {"nerdm-view", "json-schema", "manual"}:
        issues.append(f"{path}.sourceFormat: unsupported value")
    if "generator" in value:
        _expect_string(value.get("generator"), f"{path}.generator", issues)
    if "notes" in value:
        _expect_string_array(value.get("notes"), f"{path}.notes", issues)


def _validate_type_groups(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, group in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(group, item_path, issues):
            continue
        _check_keys(group, item_path, {"id", "label", "description"}, {"anchor"}, issues)
        _expect_pattern(group.get("id"), f"{item_path}.id", ID_PATTERN, issues)
        _expect_string(group.get("label"), f"{item_path}.label", issues)
        _expect_string(group.get("description"), f"{item_path}.description", issues)
        if "anchor" in group:
            _expect_pattern(group.get("anchor"), f"{item_path}.anchor", ANCHOR_PATTERN, issues)


def _validate_types(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, type_doc in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(type_doc, item_path, issues):
            continue
        _check_keys(
            type_doc,
            item_path,
            {
                "id",
                "name",
                "label",
                "group",
                "valueType",
                "displayType",
                "description",
                "brief",
                "anchor",
                "properties",
            },
            {"usage", "inheritsFrom", "source"},
            issues,
        )
        _expect_pattern(type_doc.get("id"), f"{item_path}.id", ID_PATTERN, issues)
        _expect_string(type_doc.get("name"), f"{item_path}.name", issues)
        _expect_string(type_doc.get("label"), f"{item_path}.label", issues)
        _expect_pattern(type_doc.get("group"), f"{item_path}.group", ID_PATTERN, issues)
        _expect_string(type_doc.get("valueType"), f"{item_path}.valueType", issues)
        _expect_string(type_doc.get("displayType"), f"{item_path}.displayType", issues)
        _expect_string_array(type_doc.get("description"), f"{item_path}.description", issues)
        _expect_string(type_doc.get("brief"), f"{item_path}.brief", issues)
        _expect_pattern(
            type_doc.get("anchor"), f"{item_path}.anchor", ANCHOR_PATTERN, issues
        )
        if "usage" in type_doc:
            _validate_usage_array(type_doc.get("usage"), f"{item_path}.usage", issues)
        if "inheritsFrom" in type_doc:
            _expect_string_array(
                type_doc.get("inheritsFrom"), f"{item_path}.inheritsFrom", issues
            )
        if "source" in type_doc:
            _validate_source_ref(type_doc.get("source"), f"{item_path}.source", issues)
        _validate_properties(type_doc.get("properties"), f"{item_path}.properties", issues)


def _validate_properties(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, prop in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(prop, item_path, issues):
            continue
        _check_keys(
            prop,
            item_path,
            {
                "id",
                "name",
                "label",
                "parentType",
                "value",
                "description",
                "brief",
                "anchor",
            },
            {
                "required",
                "inheritedFrom",
                "schemaNotes",
                "readerNotes",
                "examples",
                "allowedValues",
                "source",
            },
            issues,
        )
        _expect_pattern(prop.get("id"), f"{item_path}.id", ID_PATTERN, issues)
        _expect_string(prop.get("name"), f"{item_path}.name", issues)
        _expect_string(prop.get("label"), f"{item_path}.label", issues)
        _expect_string(prop.get("parentType"), f"{item_path}.parentType", issues)
        _validate_value_descriptor(prop.get("value"), f"{item_path}.value", issues)
        _expect_string_array(prop.get("description"), f"{item_path}.description", issues)
        _expect_string(prop.get("brief"), f"{item_path}.brief", issues)
        _expect_pattern(prop.get("anchor"), f"{item_path}.anchor", ANCHOR_PATTERN, issues)
        if "required" in prop:
            _expect_bool(prop.get("required"), f"{item_path}.required", issues)
        if prop.get("inheritedFrom") is not None:
            _validate_inheritance_ref(
                prop.get("inheritedFrom"), f"{item_path}.inheritedFrom", issues
            )
        for key in ("schemaNotes", "readerNotes", "examples"):
            if key in prop:
                _expect_string_array(prop.get(key), f"{item_path}.{key}", issues)
        if "allowedValues" in prop:
            _validate_allowed_values(
                prop.get("allowedValues"), f"{item_path}.allowedValues", issues
            )
        if "source" in prop:
            _validate_source_ref(prop.get("source"), f"{item_path}.source", issues)


def _validate_value_descriptor(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_object(value, path, issues):
        return
    _check_keys(value, path, {"jsonType", "display"}, {"itemType", "objectType"}, issues)
    _expect_string(value.get("jsonType"), f"{path}.jsonType", issues)
    _expect_string(value.get("display"), f"{path}.display", issues)
    for key in ("itemType", "objectType"):
        if key in value and value.get(key) is not None:
            _expect_string(value.get(key), f"{path}.{key}", issues)


def _validate_usage_array(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, usage in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(usage, item_path, issues):
            continue
        _check_keys(usage, item_path, {"id", "template", "data"}, set(), issues)
        _expect_string(usage.get("id"), f"{item_path}.id", issues)
        _expect_string(usage.get("template"), f"{item_path}.template", issues)
        if _expect_object(usage.get("data"), f"{item_path}.data", issues):
            for key, data_value in usage["data"].items():
                _expect_string(data_value, f"{item_path}.data.{key}", issues)


def _validate_allowed_values(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(item, item_path, issues):
            continue
        _check_keys(item, item_path, {"value", "description"}, set(), issues)
        _expect_string(item.get("value"), f"{item_path}.value", issues)
        _expect_string(item.get("description"), f"{item_path}.description", issues)


def _validate_inheritance_ref(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_object(value, path, issues):
        return
    _check_keys(value, path, {"type", "property", "anchor"}, set(), issues)
    _expect_string(value.get("type"), f"{path}.type", issues)
    _expect_string(value.get("property"), f"{path}.property", issues)
    _expect_pattern(value.get("anchor"), f"{path}.anchor", ANCHOR_PATTERN, issues)


def _validate_source_ref(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_object(value, path, issues):
        return
    _check_keys(value, path, set(), {"path", "jsonPointer", "notes"}, issues)
    if "path" in value:
        _expect_string(value.get("path"), f"{path}.path", issues)
    if "jsonPointer" in value:
        _expect_string(value.get("jsonPointer"), f"{path}.jsonPointer", issues)
    if "notes" in value:
        _expect_string_array(value.get("notes"), f"{path}.notes", issues)


def _validate_toc(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, item in enumerate(value):
        _validate_toc_entry(item, f"{path}[{index}]", issues)


def _validate_toc_entry(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_object(value, path, issues):
        return
    _check_keys(value, path, {"id", "label", "anchor", "level"}, {"children"}, issues)
    _expect_pattern(value.get("id"), f"{path}.id", ID_PATTERN, issues)
    _expect_string(value.get("label"), f"{path}.label", issues)
    _expect_pattern(value.get("anchor"), f"{path}.anchor", ANCHOR_PATTERN, issues)
    _expect_int(value.get("level"), f"{path}.level", issues)
    if isinstance(value.get("level"), int) and value["level"] < 1:
        issues.append(f"{path}.level: expected value >= 1")
    if "children" in value:
        _validate_toc(value.get("children"), f"{path}.children", issues)


def _validate_glossary(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not _expect_object(item, item_path, issues):
            continue
        _check_keys(item, item_path, {"id", "term", "definition", "anchor"}, set(), issues)
        _expect_pattern(item.get("id"), f"{item_path}.id", ID_PATTERN, issues)
        _expect_string(item.get("term"), f"{item_path}.term", issues)
        _expect_string_array(item.get("definition"), f"{item_path}.definition", issues)
        _expect_pattern(item.get("anchor"), f"{item_path}.anchor", ANCHOR_PATTERN, issues)


def _validate_model_relationships(model: dict[str, Any], issues: list[str]) -> None:
    groups = {group["id"] for group in model.get("typeGroups", []) if isinstance(group, dict)}
    types = {type_doc["name"] for type_doc in model.get("types", []) if isinstance(type_doc, dict)}
    for type_doc in model.get("types", []):
        if not isinstance(type_doc, dict):
            continue
        if type_doc.get("group") not in groups:
            issues.append(f"types.{type_doc.get('name')}.group: unknown group")
        for parent in type_doc.get("inheritsFrom", []):
            if parent not in types:
                issues.append(f"types.{type_doc.get('name')}.inheritsFrom: unknown {parent}")


def _check_keys(
    value: dict[str, Any],
    path: str,
    required: set[str],
    optional: set[str],
    issues: list[str],
) -> None:
    keys = set(value)
    missing = required - keys
    extra = keys - required - optional
    for key in sorted(missing):
        issues.append(f"{path}: missing required key {key}")
    for key in sorted(extra):
        issues.append(f"{path}: unexpected key {key}")


def _expect_object(value: Any, path: str, issues: list[str]) -> bool:
    if not isinstance(value, dict):
        issues.append(f"{path}: expected object")
        return False
    return True


def _expect_array(value: Any, path: str, issues: list[str]) -> bool:
    if not isinstance(value, list):
        issues.append(f"{path}: expected array")
        return False
    return True


def _expect_string(value: Any, path: str, issues: list[str]) -> bool:
    if not isinstance(value, str):
        issues.append(f"{path}: expected string")
        return False
    return True


def _expect_string_array(value: Any, path: str, issues: list[str]) -> None:
    if not _expect_array(value, path, issues):
        return
    for index, item in enumerate(value):
        _expect_string(item, f"{path}[{index}]", issues)


def _expect_bool(value: Any, path: str, issues: list[str]) -> bool:
    if not isinstance(value, bool):
        issues.append(f"{path}: expected boolean")
        return False
    return True


def _expect_int(value: Any, path: str, issues: list[str]) -> bool:
    if not isinstance(value, int) or isinstance(value, bool):
        issues.append(f"{path}: expected integer")
        return False
    return True


def _expect_pattern(
    value: Any,
    path: str,
    pattern: re.Pattern[str],
    issues: list[str],
) -> bool:
    if not _expect_string(value, path, issues):
        return False
    if pattern.match(value) is None:
        issues.append(f"{path}: invalid value {value!r}")
        return False
    return True


def _raise_model_issues(issues: list[str]) -> None:
    limit = 80
    visible = issues[:limit]
    suffix = ""
    if len(issues) > limit:
        suffix = f"\n  ... {len(issues) - limit} more"
    raise RuntimeError("Model contract validation failed:\n  " + "\n  ".join(visible) + suffix)
