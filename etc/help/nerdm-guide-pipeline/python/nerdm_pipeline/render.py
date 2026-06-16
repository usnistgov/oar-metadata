"""Static HTML renderers for NERDm guide pages and runtime fragments."""

from __future__ import annotations

from html import escape
from typing import Any

from .sanitize import sanitize_inline_html


def _svg_icon(class_name: str, path: str, *, view_box: str = "0 0 24 24") -> str:
    return (
        f'<svg class="{class_name}" viewBox="{view_box}" fill="none" '
        'stroke="currentColor" aria-hidden="true" focusable="false">'
        f'<path d="{path}" stroke-linecap="round" stroke-linejoin="round"></path>'
        "</svg>"
    )


CHEVRON_DOWN_ICON = _svg_icon("nerdm-caret__icon", "M17 9.5L12 14.5L7 9.5")
CHEVRON_UP_ICON = _svg_icon(
    "nerdm-back-to-top__icon",
    "M7 14.5L12 9.5L17 14.5",
)
CHEVRON_RIGHT_ICON = _svg_icon(
    "type-index-card__arrow-icon",
    "M9.5 7L14.5 12L9.5 17",
)
DETAIL_CARET = f'<span class="nerdm-caret" aria-hidden="true">{CHEVRON_DOWN_ICON}</span>'
EYE_ICON = (
    '<svg class="property-row__goto-icon" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="13" r="2" stroke-linejoin="round"></circle>'
    '<path d="M12 7.5C7.69517 7.5 4.47617 11.0833 3.39473 12.4653'
    'C3.14595 12.7832 3.14595 13.2168 3.39473 13.5347'
    'C4.47617 14.9167 7.69517 18.5 12 18.5'
    'C16.3048 18.5 19.5238 14.9167 20.6053 13.5347'
    'C20.8541 13.2168 20.8541 12.7832 20.6053 12.4653'
    'C19.5238 11.0833 16.3048 7.5 12 7.5Z" '
    'stroke-linecap="round" stroke-linejoin="round"></path>'
    "</svg>"
)
SEARCH_ICON = (
    '<svg class="type-index-filter__search-svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" aria-hidden="true" focusable="false">'
    '<circle cx="10.5" cy="10.5" r="6.5" stroke-linejoin="round"></circle>'
    '<path d="M15 15L20 20" stroke-linecap="round" stroke-linejoin="round"></path>'
    "</svg>"
)
INFO_ICON = (
    '<svg class="nerdm-data-artifact__info-icon" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="9" stroke-linecap="round" stroke-linejoin="round"></circle>'
    '<path d="M12 11V17" stroke-linecap="round" stroke-linejoin="round"></path>'
    '<path d="M11.75 8V7H12.25V8H11.75Z" stroke-linecap="round" stroke-linejoin="round"></path>'
    "</svg>"
)


def render_type_index_html(
    guide_index: dict[str, Any],
    *,
    stylesheet: str = "type-index.css",
) -> str:
    """Render a standalone static Type Index review page."""

    group_markup = "\n".join(_render_group(group) for group in guide_index["groups"])

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>NERDm Named Types</title>",
            f'  <link rel="stylesheet" href="{escape(stylesheet)}">',
            "</head>",
            "<body>",
            '  <main class="preview-shell nerdm-docs nerdm-article">',
            '    <section class="type-index-view" aria-labelledby="type-index-title">',
            '      <header class="type-index-view__header">',
            "        <div>",
            '          <p class="type-index-view__eyebrow">NERDm reference</p>',
            '          <h1 id="type-index-title">Named Types</h1>',
            "        </div>",
            "      </header>",
            '      <div class="type-index-view__groups">',
            group_markup,
            "      </div>",
            "    </section>",
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _render_group(group: dict[str, Any]) -> str:
    type_items = "\n".join(_render_type_item(item) for item in group["types"])
    count = len(group["types"])

    return "\n".join(
        [
            '        <section class="type-index-group">',
            '          <header class="type-index-group__header">',
            f'            <h2>{escape(group["label"])}</h2>',
            f"            <span>{count} {_plural(count, 'type')}</span>",
            "          </header>",
            '          <ol class="type-index-list">',
            type_items,
            "          </ol>",
            "        </section>",
        ]
    )


def _render_type_item(item: dict[str, Any]) -> str:
    label = escape(item["label"])
    anchor = escape(item["anchor"])
    count = item["propertyCount"]

    return "\n".join(
        [
            '            <li class="type-index-list__item">',
            f'              <a href="#{anchor}" class="type-index-card">',
            '                <span class="type-index-card__name">'
            f"{label}</span>",
            '                <span class="type-index-card__meta">'
            f"{count} {_plural(count, 'property')}</span>",
            f'                <span class="type-index-card__arrow" aria-hidden="true">{CHEVRON_RIGHT_ICON}</span>',
            "              </a>",
            "            </li>",
        ]
    )


def _plural(count: int, noun: str) -> str:
    if noun == "property":
        return "property" if count == 1 else "properties"
    return noun if count == 1 else f"{noun}s"


def render_type_section_html(
    model: dict[str, Any],
    type_name: str,
    *,
    stylesheet: str = "type-section.css",
) -> str:
    """Render a standalone static review page for one named type section."""

    type_doc = _find_type(model, type_name)

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>NERDm Type - {escape(type_doc['name'])}</title>",
            f'  <link rel="stylesheet" href="{escape(stylesheet)}">',
            "</head>",
            "<body>",
            '  <main class="preview-shell">',
            _render_type_article(type_doc),
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _find_type(model: dict[str, Any], type_name: str) -> dict[str, Any]:
    for item in model["types"]:
        if item["name"] == type_name:
            return item
    raise ValueError(f"Unknown NERDm type: {type_name}")


def render_full_guide_html(
    model: dict[str, Any],
    guide_index: dict[str, Any],
    *,
    stylesheet: str = "nerdm-guide.css",
    intro_html: str = "",
    glossary_html: str = "",
    header_html: str = "",
    footer_html: str = "",
    schema_artifact: dict[str, str] | None = None,
    schema_layers: dict[str, Any] | None = None,
    record_examples: dict[str, Any] | None = None,
) -> str:
    """Render a standalone static preview for the full generated guide."""

    header = _runtime_header_fragment(header_html)
    footer = _runtime_footer_fragment(footer_html)
    body = render_guide_body_html(
        model,
        guide_index,
        intro_html=intro_html,
        glossary_html=glossary_html,
        schema_artifact=schema_artifact,
        schema_layers=schema_layers,
        record_examples=record_examples,
    ).rstrip()

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>NERDm Reader's Guide</title>",
            '  <link rel="alternate" type="application/json" href="nerdm-guide-index.json" title="NERDm Guide Index">',
            '  <link rel="alternate" type="application/json" href="nerdm-doc-model.json" title="NERDm Documentation Model">',
            '  <link rel="alternate" type="application/json" href="nerdm-schema-layers.json" title="NERDm Schema Layers">',
            '  <link rel="alternate" type="application/json" href="nerdm-record-examples.json" title="NERDm Record Examples">',
            '  <link rel="alternate" type="application/schema+json" href="../nerdm-schema/nerdm-schema.json" title="NERDm JSON Schema">',
            '  <link rel="stylesheet" href="/css/font-awesome.min.css">',
            f'  <link rel="stylesheet" href="{escape(stylesheet)}">',
            "</head>",
            "<body>",
            header,
            body,
            footer,
            "</body>",
            "</html>",
            "",
        ]
    )


def render_guide_body_html(
    model: dict[str, Any],
    guide_index: dict[str, Any],
    *,
    intro_html: str = "",
    glossary_html: str = "",
    schema_artifact: dict[str, str] | None = None,
    schema_layers: dict[str, Any] | None = None,
    record_examples: dict[str, Any] | None = None,
) -> str:
    """Render the oar-docker runtime body fragment for the generated guide."""

    duplicate_property_ids = _duplicate_property_ids(model)
    fragment_ids = _fragment_ids(model, duplicate_property_ids)
    sections = _render_reference_sections(
        model,
        guide_index,
        schema_layers=schema_layers,
        duplicate_property_ids=duplicate_property_ids,
        available_fragment_ids=fragment_ids,
    )

    return "\n".join(
        [
            '  <a class="nerdm-back-to-top" href="#guide-title">'
            f'{CHEVRON_UP_ICON}<span class="visually-hidden">Back to top</span></a>',
            '    <div id="top" class="nerdm-guide-shell nerdm-docs nerdm-docs--sticky-toc">',
            '      <aside class="nerdm-guide-rail" aria-label="Guide navigation and data artifacts">',
            _render_guide_toc(guide_index),
            _render_data_artifacts_card(
                model,
                guide_index,
                schema_artifact=schema_artifact,
                schema_layers=schema_layers,
                record_examples=record_examples,
            ),
            "      </aside>",
            '      <main class="nerdm-article nerdm-guide-content" id="nerdm-main">',
            _render_guide_hero(model, guide_index),
            _render_hand_authored_fragment(
                "guide-introduction",
                "Introduction",
                intro_html,
            ),
            sections,
            _render_hand_authored_fragment(
                "guide-glossary",
                "Glossary",
                glossary_html,
            ),
            _render_record_examples_section(record_examples),
            "      </main>",
            "    </div>",
            "",
        ]
    )


def _render_guide_hero(model: dict[str, Any], guide_index: dict[str, Any]) -> str:
    model_version = escape(model.get("modelVersion", ""))
    version_badge = (
        f'          <div><dt>Model</dt><dd>{model_version}</dd></div>'
        if model_version
        else ""
    )

    return "\n".join(
        [
            '      <header class="nerdm-hero nerdm-guide-hero" aria-labelledby="guide-title">',
            '        <p class="nerdm-kicker nerdm-guide-hero__eyebrow">NIST metadata reference</p>',
            '        <h1 id="guide-title" class="nerdm-guide-title">'
            '<span class="nerdm-term">NERDm</span>: '
            '<span class="nerdm-acronym-word"><span class="nerdm-acronym-letter nerdm-acronym-letter--n">N</span>IST</span> '
            '<span class="nerdm-acronym-word"><span class="nerdm-acronym-letter nerdm-acronym-letter--e">E</span>xtensible</span> '
            '<span class="nerdm-acronym-word"><span class="nerdm-acronym-letter nerdm-acronym-letter--r">R</span>esource</span> '
            '<span class="nerdm-acronym-word"><span class="nerdm-acronym-letter nerdm-acronym-letter--d">D</span>ata</span> '
            '<span class="nerdm-acronym-word"><span class="nerdm-acronym-letter nerdm-acronym-letter--m">m</span>odel</span>.'
            "</h1>",
            '        <p class="nerdm-dek nerdm-guide-hero__brief">'
            "A guide to NERDm records, named types, properties, and JSON "
            "structure.</p>",
            '        <dl class="nerdm-guide-hero__stats" aria-label="Guide summary">',
            f"          <div><dt>Groups</dt><dd>{guide_index['counts']['typeGroups']}</dd></div>",
            f"          <div><dt>Types</dt><dd>{guide_index['counts']['types']}</dd></div>",
            f"          <div><dt>Properties</dt><dd>{guide_index['counts']['properties']}</dd></div>",
            version_badge,
            "        </dl>",
            "      </header>",
        ]
    )

def _runtime_header_fragment(header_html: str) -> str:
    """Use the oar-docker header when present, otherwise open the content shell."""

    fragment = header_html.strip()
    return fragment if fragment else '<div id="content">'


def _runtime_footer_fragment(footer_html: str) -> str:
    """Use the oar-docker footer when present, otherwise close the content shell."""

    fragment = footer_html.strip()
    return fragment if fragment else "</div>"


def _render_reference_sections(
    model: dict[str, Any],
    guide_index: dict[str, Any],
    *,
    schema_layers: dict[str, Any] | None,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str],
) -> str:
    """Render the generated reference section and its curated companion content."""

    type_by_id = {item["id"]: item for item in model["types"]}
    group_sections = "\n".join(
        _render_type_group_section(
            group,
            [type_by_id[item["id"]] for item in group["types"] if item["id"] in type_by_id],
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        )
        for group in guide_index["groups"]
    )

    return "\n".join(
        [
            '        <section class="generated-reference" id="named-types-reference" aria-labelledby="named-types-reference-title">',
            '          <div class="nerdm-section-heading nerdm-section-heading--reference">',
            "            <p>Reference</p>",
            '            <h2 id="named-types-reference-title">NERDm Reference</h2>',
            "          </div>",
            _render_schema_layers_section(schema_layers),
            '          <div class="nerdm-subsection-heading nerdm-subsection-heading--reference nerdm-subsection-heading--types">',
            '            <h3 id="named-types-index">Named Types</h3>',
            "          </div>",
            _render_type_index_panel(guide_index),
            group_sections,
            "        </section>",
        ]
    )


def _render_type_group_section(
    group: dict[str, Any],
    types: list[dict[str, Any]],
    *,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str],
) -> str:
    if not types:
        return ""

    label = f"{group['label']} Types"
    articles = "\n".join(
        _render_type_article(
            item,
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        )
        for item in types
    )

    return "\n".join(
        [
            f'          <div class="nerdm-subsection-heading nerdm-subsection-heading--reference nerdm-subsection-heading--types" id="{escape(group["anchor"])}">',
            f"            <h3>{escape(label)}</h3>",
            f'            <p>{len(types)} {_plural(len(types), "type")}</p>',
            "          </div>",
            articles,
        ]
    )


def _render_hand_authored_fragment(section_id: str, label: str, markup: str) -> str:
    """Wrap existing guide prose so it can sit beside generated reference HTML."""

    if not markup.strip():
        return ""

    return "\n".join(
        [
            f'        <section class="handauthored-section" id="{escape(section_id)}" aria-label="{escape(label)}">',
            _inject_fragment_carets(markup.strip()),
            "        </section>",
        ]
    )


def _inject_fragment_carets(markup: str) -> str:
    """Match copied details summaries to the generated accordion controls."""

    replacements = {
        '<summary class="annotated-example__summary">JSON syntax example</summary>':
            f'<summary class="annotated-example__summary">'
            f'<span>JSON syntax example</span>{DETAIL_CARET}</summary>',
        '<summary class="annotated-example__summary">NERDm resource example</summary>':
            f'<summary class="annotated-example__summary">'
            f'<span>NERDm resource example</span>{DETAIL_CARET}</summary>',
    }
    output = markup
    for old, new in replacements.items():
        output = output.replace(old, new)
    return output


def _render_type_article(
    type_doc: dict[str, Any],
    *,
    duplicate_property_ids: set[str] | None = None,
    available_fragment_ids: set[str] | None = None,
) -> str:
    duplicate_property_ids = duplicate_property_ids or set()
    own_properties = [
        prop for prop in type_doc["properties"] if prop.get("inheritedFrom") is None
    ]
    inherited_properties = [
        prop for prop in type_doc["properties"] if prop.get("inheritedFrom") is not None
    ]

    property_groups = [
        _render_property_group(
            "Direct properties",
            own_properties,
            description="Defined directly on this named type.",
            modifier="direct",
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        ),
        _render_inherited_property_groups(
            inherited_properties,
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        ),
    ]
    description = "\n".join(
        f'          <p>{sanitize_inline_html(item)}</p>'
        for item in type_doc["description"]
    )
    usage = _render_usage(type_doc.get("usage") or [])
    inherits = _render_inherits(type_doc.get("inheritsFrom") or [])
    title_id = f"type-title-{type_doc['anchor']}"
    type_stats = _render_type_summary_stats(
        total_properties=len(type_doc["properties"]),
        inherited_properties=len(inherited_properties),
    )

    return "\n".join(
        [
            f'    <a id="{escape(type_doc["anchor"])}" name="{escape(type_doc["anchor"])}"></a>',
            '    <details class="md_entry md_type md_type--property-rows">',
            '      <summary class="type_summary">',
            '        <h3 class="type-summary__title">',
            '          <span class="type-summary__heading">',
            '            <span class="preheading"><a href="#def:named_type" title="definition: named type">Named Type</a></span>',
            f'            <span class="Type heading" id="{escape(title_id)}">{escape(type_doc["label"])}</span>',
            "          </span>",
            f"          {type_stats}",
            "        </h3>",
            f"        {DETAIL_CARET}",
            "      </summary>",
            '      <div class="type_body">',
            '        <div class="type-detail-list">',
            '          <div class="type-detail-row">',
            '            <div class="type-detail-label">JSON type</div>',
            f'            <div class="type-detail-value">{escape(type_doc["displayType"])}</div>',
            "          </div>",
            '          <div class="type-detail-row">',
            '            <div class="type-detail-label">What it represents</div>',
            '            <div class="type-detail-value">',
            description,
            "            </div>",
            "          </div>",
            usage,
            inherits,
            "        </div>",
            "      </div>",
            '      <div class="md_props">',
            *property_groups,
            "      </div>",
            "    </details>",
        ]
    )


def _render_type_summary_stats(
    *,
    total_properties: int,
    inherited_properties: int,
) -> str:
    inherited_text = (
        f" ({inherited_properties} inherited)" if inherited_properties else ""
    )
    return (
        '<span class="type-summary__stats">'
        f"{total_properties} {_plural(total_properties, 'property')}{inherited_text}"
        "</span>"
    )


def _render_type_index_panel(guide_index: dict[str, Any]) -> str:
    group_markup = "\n".join(_render_group(group) for group in guide_index["groups"])

    return "\n".join(
        [
            '        <details class="type-index type-index-view" id="schema-reference" aria-labelledby="type-index-title" open>',
            '          <summary class="type-index__header type-index-view__header">',
            "            <div>",
            '              <h2 id="type-index-title">Type Index</h2>',
            "            </div>",
            f"            {DETAIL_CARET}",
            "          </summary>",
            _render_type_index_filter(guide_index),
            '          <div class="type-index-view__groups">',
            group_markup,
            "          </div>",
            "        </details>",
        ]
    )


def _render_type_index_filter(guide_index: dict[str, Any]) -> str:
    type_count = guide_index["counts"]["types"]

    return "\n".join(
        [
            '          <div class="type-index-view__tools nerdm-enhancement" data-nerdm-enhancement="type-index-filter" hidden>',
            '            <label class="type-index-filter__label" for="type-index-filter-input">Filter types</label>',
            '            <div class="type-index-filter__field">',
            f'              <span class="type-index-filter__search-icon" aria-hidden="true">{SEARCH_ICON}</span>',
            '              <input id="type-index-filter-input" class="type-index-filter__input" data-nerdm-type-filter type="text" autocomplete="off" spellcheck="false" placeholder="Search named types">',
            '              <button class="type-index-filter__clear" data-nerdm-type-filter-clear type="button" aria-label="Clear filter"><span class="visually-hidden">Clear filter</span></button>',
            "            </div>",
            f'            <span class="type-index-filter__count" data-nerdm-type-filter-count aria-live="polite">{type_count} types</span>',
            '            <p class="type-index-filter__empty" data-nerdm-type-filter-empty hidden>No matching named types.</p>',
            "          </div>",
        ]
    )


def _render_guide_toc(guide_index: dict[str, Any]) -> str:
    reference_items = "\n".join(
        _render_guide_toc_type_group(group) for group in guide_index["groups"]
    )

    return "\n".join(
        [
            '        <div class="nerdm-toc nerdm-guide-toc" aria-label="Guide sections">',
            '        <h2>Contents</h2>',
            '        <nav aria-label="NERDm guide contents">',
            '          <ol class="nerdm-toc-tree">',
            '            <li class="nerdm-toc-section">',
            '              <div class="nerdm-toc-section__header">',
            '                <a class="nerdm-toc-section__title" href="#sec:intro">Introduction</a>',
            "              </div>",
            '              <ol class="nerdm-toc-section__links">',
            '                <li><a class="nerdm-toc-link nerdm-toc-link--subtle" href="#nerdm-record-shape">Record shape</a></li>',
            '                <li><a class="nerdm-toc-link nerdm-toc-link--subtle" href="#nerdm-record-contents">Record contents</a></li>',
            "              </ol>",
            "            </li>",
            '            <li class="nerdm-toc-section">',
            '              <div class="nerdm-toc-section__header nerdm-toc-section__header--reference">',
            '                <a class="nerdm-toc-section__title" href="#named-types-reference">NERDm Reference</a>',
            "              </div>",
            '              <ol class="nerdm-toc-section__groups">',
            '                <li><a class="nerdm-toc-link nerdm-toc-link--subtle" href="#schema-layers">Schema layers</a></li>',
            '                <li><a class="nerdm-toc-link nerdm-toc-link--subtle" href="#named-types-index">Named Types</a></li>',
            reference_items,
            "              </ol>",
            "            </li>",
            '            <li class="nerdm-toc-section">',
            '              <div class="nerdm-toc-section__header nerdm-toc-section__header--glossary">',
            '                <a class="nerdm-toc-section__title" href="#sec:glossary">Glossary</a>',
            "              </div>",
            "            </li>",
            '            <li class="nerdm-toc-section">',
            '              <div class="nerdm-toc-section__header nerdm-toc-section__header--examples">',
            '                <a class="nerdm-toc-section__title" href="#record-examples">Examples</a>',
            "              </div>",
            "            </li>",
            "          </ol>",
            "        </nav>",
            "        </div>",
        ]
    )


def _render_data_artifacts_card(
    model: dict[str, Any],
    guide_index: dict[str, Any],
    *,
    schema_artifact: dict[str, str] | None = None,
    schema_layers: dict[str, Any] | None = None,
    record_examples: dict[str, Any] | None = None,
) -> str:
    """Render links to the machine-readable artifacts shipped with the guide."""

    model_version = model.get("modelVersion", "")
    index_version = guide_index.get("indexVersion", "")
    schema_layers_version = (schema_layers or {}).get("version", "")
    record_examples_version = (record_examples or {}).get("version", "")
    schema_item = {
        "label": "NERDm JSON Schema",
        "href": "../nerdm-schema/nerdm-schema.json",
        "version": "",
        "description": (
            "Current NERDm JSON Schema used by systems to validate NERDm "
            "metadata records."
        ),
    }
    if schema_artifact is not None:
        schema_item.update(
            {
                key: value
                for key, value in schema_artifact.items()
                if key in {"href", "version", "description"} and value
            }
        )
    artifacts = [
        {
            "label": "Guide index",
            "href": "nerdm-guide-index.json",
            "version": _artifact_version(index_version),
            "description": (
                "Compact lookup data for named types, groups, property counts, "
                "inherited references, and guide anchors."
            ),
        },
        {
            "label": "Documentation model",
            "href": "nerdm-doc-model.json",
            "version": _artifact_version(model_version),
            "description": (
                "Full structured guide model used to render this page, including "
                "types, properties, descriptions, inheritance, and anchors."
            ),
        },
        {
            "label": "Schema layers",
            "href": "nerdm-schema-layers.json",
            "version": _artifact_version(schema_layers_version),
            "description": (
                "Curated layer data showing how the core NERDm schema and "
                "public-data extension relate to named types."
            ),
        },
        {
            "label": "Record examples",
            "href": "nerdm-record-examples.json",
            "version": _artifact_version(record_examples_version),
            "description": (
                "Curated examples from the NIST records service used by the "
                "examples section."
            ),
        },
        schema_item,
    ]
    items = "\n".join(_render_data_artifact_item(item) for item in artifacts)

    return "\n".join(
        [
            '        <section class="nerdm-data-artifacts" aria-labelledby="nerdm-data-artifacts-title">',
            '          <div class="nerdm-data-artifacts__header">',
            '            <h3 id="nerdm-data-artifacts-title">Data artifacts</h3>',
            "          </div>",
            '          <ul class="nerdm-data-artifacts__list">',
            items,
            "          </ul>",
            "        </section>",
        ]
    )


def _render_schema_layers_section(data: dict[str, Any] | None) -> str:
    """Render the curated overview of core and extension schema layers."""

    if not data or not data.get("layers"):
        return ""

    layers = "\n".join(_render_schema_layer(layer) for layer in data["layers"])
    chains = "\n".join(_render_schema_chain(chain) for chain in data.get("chains") or [])
    chain_block = (
        "\n".join(
            [
                '            <div class="schema-chain-panel">',
                "              <h4>How NERDm types build on each other</h4>",
                '              <p>Read each row left to right. The row title names a common record or component shape; the type cards show the base schema type, any extension type, and the most specific type used for that shape.</p>',
                '              <dl class="schema-chain-legend" aria-label="Extension chain legend">',
                "                <div><dt>Base type</dt><dd>Defines the generic NERDm shape.</dd></div>",
                "                <div><dt>Extension type</dt><dd>Adds public-data behavior.</dd></div>",
                "                <div><dt>Specific type</dt><dd>Names the concrete record or component pattern.</dd></div>",
                "              </dl>",
                '              <div class="schema-chain-list">',
                chains,
                "              </div>",
                '              <p class="schema-chain-panel__examples">Want to see these patterns in real metadata? <a href="#record-examples">Jump to curated record examples</a>.</p>',
                "            </div>",
            ]
        )
        if chains
        else ""
    )

    return "\n".join(
        [
            '          <div class="nerdm-subsection-heading nerdm-subsection-heading--reference nerdm-subsection-heading--types">',
            f'            <h3 id="schema-layers">{escape(data.get("title") or "Schema layers")}</h3>',
            "          </div>",
            '          <section class="schema-layers" aria-labelledby="schema-layers">',
            f'            <p class="schema-layers__intro">{escape(data.get("description") or "")}</p>',
            '            <div class="schema-layer-grid">',
            layers,
            "            </div>",
            chain_block,
            "          </section>",
        ]
    )


def _render_schema_layer(layer: dict[str, Any]) -> str:
    type_items = "\n".join(
        _render_schema_layer_type(item) for item in layer.get("types") or []
    )
    artifact = str(layer.get("artifact") or "")
    artifact_markup = (
        f'              <code>{escape(artifact)}</code>' if artifact else ""
    )

    return "\n".join(
        [
            '              <article class="schema-layer-card">',
            '                <header class="schema-layer-card__header">',
            f'                  <h4>{escape(layer.get("label") or layer.get("id") or "Schema layer")}</h4>',
            artifact_markup,
            "                </header>",
            f'                <p>{escape(layer.get("summary") or "")}</p>',
            '                <p class="schema-layer-card__list-label">Representative named types</p>',
            '                <ul class="schema-layer-types">',
            type_items,
            "                </ul>",
            "              </article>",
        ]
    )


def _render_schema_layer_type(item: dict[str, Any]) -> str:
    name = str(item.get("name") or "")
    return (
        '<li>'
        f'<a href="#{escape(name)}">{escape(name)}</a>'
        "</li>"
    )


def _render_schema_chain(chain: dict[str, Any]) -> str:
    type_names = [str(name) for name in chain.get("types") or []]
    type_links = "\n".join(
        _render_schema_chain_type(name, index, len(type_names))
        for index, name in enumerate(type_names)
    )
    return "\n".join(
        [
            '                <div class="schema-chain">',
            f'                  <h5>{escape(chain.get("label") or "Extension path")}</h5>',
            '                  <ol>',
            type_links,
            "                  </ol>",
            "                </div>",
        ]
    )


def _render_schema_chain_type(name: str, index: int, count: int) -> str:
    if index == 0:
        role = "Base type"
    elif index == count - 1:
        role = "Specific type"
    else:
        role = "Extension type"

    return "\n".join(
        [
            "                  <li>",
            f'                    <span class="schema-chain__role">{escape(role)}</span>',
            f'                    <a href="#{escape(name)}">{escape(name)}</a>',
            "                  </li>",
        ]
    )


def _render_record_examples_section(data: dict[str, Any] | None) -> str:
    """Render curated examples that show NERDm types in live record patterns."""

    if not data or not data.get("examples"):
        return ""

    cards = "\n".join(_render_record_example_card(item) for item in data["examples"])
    return "\n".join(
        [
            '        <section class="record-examples-section" id="record-examples" aria-labelledby="record-examples-title">',
            '          <div class="nerdm-section-heading nerdm-section-heading--examples">',
            "            <p>Examples</p>",
            f'            <h2 id="record-examples-title">{escape(data.get("title") or "NERDm record examples")}</h2>',
            "          </div>",
            f'          <p class="record-examples-section__intro">{escape(data.get("description") or "")}</p>',
            '          <div class="record-example-grid">',
            cards,
            "          </div>",
            "        </section>",
        ]
    )


def _render_record_example_card(item: dict[str, Any]) -> str:
    types = "\n".join(
        f'              <a href="#{escape(str(name))}">{escape(str(name))}</a>'
        for name in item.get("types") or []
    )
    features = "\n".join(
        f"              <li>{escape(str(feature))}</li>"
        for feature in item.get("features") or []
    )
    return "\n".join(
        [
            '            <article class="record-example-card">',
            '              <p class="record-example-card__label">'
            f'{escape(item.get("label") or "Record example")}</p>',
            f'              <h3>{escape(item.get("title") or "")}</h3>',
            f'              <p>{escape(item.get("summary") or "")}</p>',
            '              <div class="record-example-card__types" aria-label="NERDm types shown">',
            types,
            "              </div>",
            '              <ul class="record-example-card__features">',
            features,
            "              </ul>",
            '              <div class="record-example-card__actions">',
            f'                <a href="{escape(item.get("recordUrl") or "")}" target="_blank" rel="noopener noreferrer">JSON record</a>',
            f'                <a href="{escape(item.get("landingPageUrl") or "")}" target="_blank" rel="noopener noreferrer">Landing page</a>',
            "              </div>",
            "            </article>",
        ]
    )


def _artifact_version(version: str) -> str:
    value = str(version or "").strip()
    if not value:
        return ""
    return value if value.startswith("v") else f"v{value}"


def _render_data_artifact_item(item: dict[str, str]) -> str:
    label = escape(item["label"])
    href = escape(item["href"])
    description = escape(item["description"])
    version = escape(item.get("version", ""))
    version_badge = (
        f'                  <span class="nerdm-data-artifact__version">{version}</span>'
        if version
        else ""
    )

    return "\n".join(
        [
            '            <li class="nerdm-data-artifact">',
            f'              <a class="nerdm-data-artifact__link" href="{href}" target="_blank" rel="noopener noreferrer">',
            f'                <span class="nerdm-data-artifact__label">{label}</span>',
            '                <span class="nerdm-data-artifact__meta">',
            '                  <span class="nerdm-data-artifact__format">JSON</span>',
            version_badge,
            "                </span>",
            f'                <span class="nerdm-data-artifact__info" aria-label="{description}">',
            f"                {INFO_ICON}",
            f'                <span class="nerdm-data-artifact__tooltip" role="tooltip">{description}</span>',
            "                </span>",
            "              </a>",
            "            </li>",
        ]
    )


def _render_guide_toc_type_group(group: dict[str, Any]) -> str:
    types = group.get("types") or []
    if not types:
        return ""

    label = f"{group['label']} types"
    anchor = escape(group["anchor"])
    count = len(types)
    open_attr = " open" if group["label"] == "Resource" else ""
    type_links = "\n".join(
        f'                      <li><a class="nerdm-toc-link nerdm-toc-link--type" href="#{escape(item["anchor"])}">{escape(item["label"])}</a></li>'
        for item in types
    )
    return "\n".join(
        [
            '                <li class="nerdm-toc-tree__item nerdm-toc-tree__item--group">',
            f'                    <details class="nerdm-toc-node nerdm-toc-node--group"{open_attr}>',
            '                      <summary class="nerdm-toc-node__summary nerdm-toc-node__summary--group">',
            f'                        <a class="nerdm-toc-node__summary-link" href="#{anchor}">{escape(label)}</a>',
            f'                        <span class="nerdm-toc-node__count">{count}</span>',
            f"                        {DETAIL_CARET}",
            "                      </summary>",
            '                      <ol class="nerdm-toc-node__children nerdm-toc-node__children--types">',
            type_links,
            "                      </ol>",
            "                    </details>",
            "                </li>",
        ]
    )


def _render_usage(usage: list[dict[str, Any]]) -> str:
    if not usage:
        return ""

    items = "\n".join(
        f"              <p>{escape(_render_template(item))}</p>"
        for item in usage
    )
    return "\n".join(
        [
            '          <div class="type-detail-row">',
            '            <div class="type-detail-label">Where it is used</div>',
            '            <div class="type-detail-value type-use-list">',
            items,
            "            </div>",
            "          </div>",
        ]
    )


def _render_inherits(type_names: list[str]) -> str:
    if not type_names:
        return ""

    items = "\n".join(
        f'              <p><span class="Type reference"><a href="#{escape(name)}">{escape(name)}</a></span></p>'
        for name in type_names
    )
    return "\n".join(
        [
            '          <div class="type-detail-row">',
            '            <div class="type-detail-label">Extends</div>',
            '            <div class="type-detail-value type-use-list">',
            items,
            "            </div>",
            "          </div>",
        ]
    )


def _render_property_group(
    label: str,
    properties: list[dict[str, Any]],
    *,
    description: str = "",
    modifier: str = "",
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str] | None,
) -> str:
    if not properties:
        return ""

    cards = "\n".join(
        _render_property_card(prop, duplicate_property_ids=duplicate_property_ids)
        if available_fragment_ids is None
        else _render_property_card(
            prop,
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        )
        for prop in properties
    )
    header_class = "property-list-header"
    if modifier:
        header_class += f" property-list-header--{modifier}"
    description_markup = (
        f"            <p>{escape(description)}</p>"
        if description
        else f"            <p>{len(properties)} {_plural(len(properties), 'property')}</p>"
    )
    return "\n".join(
        [
            f'        <div class="{header_class}">',
            '          <div class="property-list-header__text">',
            f"            <h4>{escape(label)}</h4>",
            description_markup,
            "          </div>",
            f'          <span class="property-list-header__count">{len(properties)}</span>',
            "        </div>",
            '        <div class="property-list">',
            cards,
            "        </div>",
        ]
    )


def _render_inherited_property_groups(
    properties: list[dict[str, Any]],
    *,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str] | None,
) -> str:
    if not properties:
        return ""

    properties_by_source: dict[str, list[dict[str, Any]]] = {}
    for prop in properties:
        source = prop.get("inheritedFrom") or {}
        properties_by_source.setdefault(source.get("type", "Unknown"), []).append(prop)

    groups = "\n".join(
        _render_inherited_property_group(
            source,
            source_properties,
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        )
        for source, source_properties in properties_by_source.items()
    )
    count = len(properties)

    return "\n".join(
        [
            '        <div class="property-list-header property-list-header--inherited">',
            '          <div class="property-list-header__text">',
            "            <h4>Inherited properties</h4>",
            "            <p>Linked back to their source definitions.</p>",
            "          </div>",
            f'          <span class="property-list-header__count">{count}</span>',
            "        </div>",
            groups,
        ]
    )


def _render_inherited_property_group(
    source: str,
    properties: list[dict[str, Any]],
    *,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str] | None,
) -> str:
    count = len(properties)
    cards = "\n".join(
        _render_inherited_property_link(
            prop,
            duplicate_property_ids=duplicate_property_ids,
            available_fragment_ids=available_fragment_ids,
        )
        for prop in properties
    )
    source_label = escape(source)
    source_heading = (
        f'<span>Inherited from <a href="#{source_label}">{source_label}</a></span>'
        if available_fragment_ids is None or source in available_fragment_ids
        else f"<span>Inherited from {source_label}</span>"
    )

    return "\n".join(
        [
            '        <details class="property-inherited-group">',
            '          <summary class="property-inherited-group__header">',
            f"            {source_heading}",
            f'            <span class="property-inherited-group__count">{count}</span>',
            f"            {DETAIL_CARET}",
            "          </summary>",
            '          <div class="property-list property-list--inherited">',
            cards,
            "          </div>",
            "        </details>",
        ]
    )


def _render_inherited_property_link(
    prop: dict[str, Any],
    *,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str] | None,
) -> str:
    inherited = prop.get("inheritedFrom") or {}
    source_anchor = inherited.get("anchor") or prop["anchor"]
    row_id = _property_card_id(prop, duplicate_property_ids)
    target_anchor = (
        source_anchor
        if available_fragment_ids is None or source_anchor in available_fragment_ids
        else row_id
    )

    return "\n".join(
        [
            f'            <div class="md_entry md_prop md_prop--row md_prop--inherited property-card" id="{escape(row_id)}">',
            f'              <a class="property-row__summary property-row__summary--link property-card__summary" href="#{escape(target_anchor)}">',
            '                <span class="property-row__identity property-card__identity">',
            f'                  <span class="Property heading property-row__name property-card__name">{escape(prop["name"])}</span>',
            f'                  <span class="property-row__description property-card__brief">{sanitize_inline_html(prop["brief"])}</span>',
            "                </span>",
            '                <span class="property-row__badges property-card__badges">',
            f'                  <span class="property-row__badge property-card__badge">{escape(prop["value"]["display"])}</span>',
            '                  <span class="property-row__badge property-row__badge--inherited property-card__badge property-card__badge--inherited">Inherited</span>',
            "                </span>",
            f'                <span class="property-row__goto" aria-hidden="true">{EYE_ICON}</span>',
            "              </a>",
            "            </div>",
        ]
    )


def _render_property_card(
    prop: dict[str, Any],
    *,
    duplicate_property_ids: set[str],
    available_fragment_ids: set[str] | None = None,
) -> str:
    inherited = prop.get("inheritedFrom")
    inherited_badge = ""
    inherited_link = ""
    if inherited:
        inherited_badge = (
            '<span class="property-row__badge property-row__badge--inherited '
            'property-card__badge property-card__badge--inherited">'
            f"Inherited</span>"
        )
        source_label = f"{inherited['type']}.{inherited['property']}"
        if available_fragment_ids is None or inherited["anchor"] in available_fragment_ids:
            inherited_link = (
                '                <div class="property-detail-row">'
                '<div class="property-detail-label">Inherited from</div>'
                f'<div class="property-detail-value"><a class="property-card__source" href="#{escape(inherited["anchor"])}">'
                f"{escape(source_label)}</a></div></div>"
            )
        else:
            inherited_link = (
                '                <div class="property-detail-row">'
                '<div class="property-detail-label">Inherited from</div>'
                '<div class="property-detail-value"><span class="property-card__source '
                'property-card__source--missing">'
                f"{escape(source_label)}</span></div></div>"
            )

    extras = "\n".join(
        block
        for block in [
            _render_text_list("Reader notes", prop.get("readerNotes") or []),
            _render_text_list("Schema notes", prop.get("schemaNotes") or []),
            _render_text_list("Examples", prop.get("examples") or [], code=True),
            _render_allowed_values(prop.get("allowedValues") or []),
        ]
        if block
    )

    return "\n".join(
        [
            f'          <details class="md_entry md_prop md_prop--row property-card" id="{escape(_property_card_id(prop, duplicate_property_ids))}">',
            '            <summary class="property-row__summary property-card__summary">',
            '              <span class="property-row__identity property-card__identity">',
            f'                <span class="Property heading property-row__name property-card__name">{escape(prop["name"])}</span>',
            f'                <span class="property-row__description property-card__brief">{sanitize_inline_html(prop["brief"])}</span>',
            "              </span>",
            '              <span class="property-row__badges property-card__badges">',
            f'                <span class="property-row__badge property-card__badge">{escape(prop["value"]["display"])}</span>',
            f"                {inherited_badge}",
            "              </span>",
            f"              {DETAIL_CARET}",
            "            </summary>",
            '            <div class="property-row__details property-card__body">',
            '              <div class="property-detail-list">',
            '                <div class="property-detail-row">',
            '                  <div class="property-detail-label">What it represents</div>',
            f'                  <div class="property-detail-value"><p>{sanitize_inline_html(prop["brief"])}</p></div>',
            "                </div>",
            '                <div class="property-detail-row">',
            '                  <div class="property-detail-label">Value type</div>',
            f'                  <div class="property-detail-value">{escape(prop["value"]["display"])}</div>',
            "                </div>",
            '                <div class="property-detail-row">',
            '                  <div class="property-detail-label">Anchor</div>',
            f'                  <div class="property-detail-value"><code>{escape(prop["anchor"])}</code></div>',
            "                </div>",
            inherited_link,
            extras,
            "              </div>",
            "            </div>",
            "          </details>",
        ]
    )


def _property_card_id(prop: dict[str, Any], duplicate_property_ids: set[str]) -> str:
    """Return a unique DOM ID for property rows that share a model property ID."""

    inherited = prop.get("inheritedFrom")
    if inherited is None or prop["id"] not in duplicate_property_ids:
        return prop["id"]
    return f"{prop['id']}--inherited-from-{inherited['type']}"


def _duplicate_property_ids(model: dict[str, Any]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for type_doc in model["types"]:
        for prop in type_doc["properties"]:
            prop_id = prop["id"]
            if prop_id in seen:
                duplicates.add(prop_id)
            seen.add(prop_id)

    return duplicates


def _fragment_ids(model: dict[str, Any], duplicate_property_ids: set[str]) -> set[str]:
    """Return generated IDs used to keep intra-page links resolvable."""

    fragments = {
        "guide-title",
        "schema-reference",
        "type-index-title",
    }

    for type_doc in model["types"]:
        fragments.add(type_doc["anchor"])
        fragments.add(f"type-title-{type_doc['anchor']}")
        for prop in type_doc["properties"]:
            fragments.add(_property_card_id(prop, duplicate_property_ids))

    return fragments


def _render_text_list(label: str, values: list[str], *, code: bool = False) -> str:
    if not values:
        return ""

    items = "\n".join(
        f"                  <code>{escape(value)}</code>"
        if code
        else f"                  <li>{sanitize_inline_html(value)}</li>"
        for value in values
    )
    value_markup = (
        f'                <div class="property-examples">\n{items}\n                </div>'
        if code
        else f'                <ul class="property-notes">\n{items}\n                </ul>'
    )
    return "\n".join(
        [
            '                <div class="property-detail-row">',
            f'                  <div class="property-detail-label">{escape(label)}</div>',
            '                  <div class="property-detail-value">',
            value_markup,
            "                  </div>",
            "                </div>",
        ]
    )


def _render_allowed_values(values: list[dict[str, str]]) -> str:
    if not values:
        return ""

    items = "\n".join(
        "\n".join(
            [
            '                  <div class="allowed-value-row">',
            f"                    <dt><code>{escape(item['value'])}</code></dt>",
            f"                    <dd>{sanitize_inline_html(item['description'])}</dd>",
            "                  </div>",
            ]
        )
        for item in values
    )
    return "\n".join(
        [
            '                <div class="property-detail-row">',
            '                  <div class="property-detail-label">Allowed values</div>',
            '                  <div class="property-detail-value">',
            '                <dl class="allowed-values">',
            items,
            "                </dl>",
            "                  </div>",
            "                </div>",
        ]
    )


def _render_template(item: dict[str, Any]) -> str:
    text = item.get("template") or ""
    for key, value in (item.get("data") or {}).items():
        text = text.replace("{" + str(key) + "}", str(value))
    return text
