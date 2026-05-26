# Generated JSON Anatomy

This note explains the two generated JSON files that drive the NERDm guide
renderer and are exposed from the guide page as Data artifacts.

## Files

- `dist/preview/nerdm-doc-model.json`
  - Full documentation model.
  - Used as the main input for rendering the page.
  - Contains the complete generated view of NERDm types, properties,
    descriptions, examples, inheritance, anchors, and source pointers.
- `dist/preview/nerdm-guide-index.json`
  - Compact guide index.
  - Used by the renderer for navigation-oriented structures.
  - Exposes smaller lookup data for anchors, type groups, property counts, and
    inherited-property references.

Runtime copies are written to:

- `dist/nerdm-docs/docs/nerdm/nerdm-doc-model.json`
- `dist/nerdm-docs/docs/nerdm/nerdm-guide-index.json`

The generated guide links to those runtime copies from the Data artifacts card.

## Documentation Model

`nerdm-doc-model.json` is the richer file. It is meant to preserve enough
structured information to render the full human guide without re-reading
`etc/help/nerdm-view.json`.

Top-level fields:

- `modelVersion`
  - Version of the documentation-model format.
  - This is not the NERDm schema version.
- `title`
  - Human-readable source title.
- `description`
  - Source-level description lines.
- `generatedFrom`
  - Metadata about the source file and generator.
  - Records that the current model came from `etc/help/nerdm-view.json`.
- `typeGroups`
  - Ordered group definitions for Resource, Component, and Other.
- `types`
  - Full named type records.
  - This is the main body of the model.
- `toc`
  - Structured table-of-contents data from the model builder.
  - The current guide renderer primarily uses the guide index for the visible
    table of contents.
- `glossary`
  - Reserved model-level glossary list.
  - The current glossary content is still extracted from
    `etc/help/nerdm-guide-pipeline/fragments/nerdm-glossary-body.html`.

## Type Group Records

Each `typeGroups[]` record has:

- `id`
  - Stable group id, such as `Resource`.
- `label`
  - Display label.
- `description`
  - Short group explanation.
- `anchor`
  - Page anchor for the group section, such as `group-Resource`.

The renderer uses these records to order the generated Named Type sections.

## Type Records

Each `types[]` record describes one NERDm named type.

Important fields:

- `id`
  - Stable type id.
- `name`
  - Type name used in the source data.
- `label`
  - Display label.
- `group`
  - One of the type group ids.
- `valueType`
  - Raw JSON value category from the source.
- `displayType`
  - Human-readable type label shown in the guide.
- `description`
  - Full description lines.
- `brief`
  - Short description used in compact cards and indexes.
- `anchor`
  - Page anchor for the named type.
- `usage`
  - Structured usage records for where this type appears.
- `inheritsFrom`
  - List of parent named types.
- `properties`
  - Full property records for this type.
  - Includes direct and inherited properties.
- `source`
  - Source pointer back to the source view record.

The renderer uses type records for collapsible Named Type panels, type
headings, direct-property groups, inherited-property groups, and type-level
statistics.

## Property Records

Each `types[].properties[]` record describes one property as it appears under a
named type.

Important fields:

- `id`
  - Stable property id in `Type.property` form.
- `name`
  - Property name.
- `label`
  - Human-readable label.
- `parentType`
  - Type that currently displays this property.
- `value`
  - Structured value type data.
- `description`
  - Full description lines.
- `brief`
  - Short property description.
- `anchor`
  - Canonical page anchor for direct properties.
- `required`
  - Boolean required marker.
  - Current source data does not expose this fully, so generated values are
    currently false.
- `inheritedFrom`
  - Null for direct properties.
  - For inherited properties, points to the source type, property, and anchor.
- `schemaNotes`
  - Notes from schema-oriented source metadata.
- `readerNotes`
  - Notes meant for guide readers.
- `examples`
  - Example values.
- `source`
  - Source pointer back to the source view property record.

The renderer uses direct properties as expandable property rows. It groups
inherited properties by `inheritedFrom.type` and links each inherited row back
to the source property anchor.

## Value Records

Each property has a `value` object.

Common fields:

- `jsonType`
  - Raw JSON kind, such as `string`, `array`, `object`, or `boolean`.
- `display`
  - Human-readable value type, such as `text`, `text (URL)`, or
    `list of VersionRelease objects`.
- `itemType`
  - Present for arrays whose items refer to another named type.
- `objectType`
  - Present for object values that refer to another named type.

The renderer uses `display` for the visible value-type badge and uses
`itemType` or `objectType` when linking to named types.

## Guide Index

`nerdm-guide-index.json` is the compact companion to the full model. It should
be used when a caller needs navigation or lookup data without loading every
description, example, and note.

Top-level fields:

- `indexVersion`
  - Version of the guide-index format.
- `title`
  - Guide title.
- `sourceModel`
  - Pointer to the model used to build the index.
- `counts`
  - Summary counts for groups, types, properties, inherited properties,
    anchors, and inherited references.
- `groups`
  - Compact group list with child type links.
- `types`
  - Compact type records.
- `anchors`
  - Canonical anchors for type groups, types, and direct properties.
- `inheritedReferences`
  - Lookup table from inherited property appearances back to source property
    anchors.

## Index Group Records

Each `groups[]` record has:

- `id`
  - Group id.
- `label`
  - Display label.
- `anchor`
  - Group anchor.
- `types`
  - Compact list of child types in display order.

The renderer uses these records for the Type Index and the reference portion
of the table of contents.

## Index Type Records

Each `types[]` record is a compact version of a full model type.

Important fields:

- `id`, `name`, `label`, `group`, `anchor`
  - Core identity and navigation fields.
- `brief`
  - Short display description.
- `valueType`
  - Display value type.
- `inheritsFrom`
  - Parent type names.
- `propertyCount`
  - Total properties shown under the type.
- `ownPropertyCount`
  - Direct properties only.
- `inheritedPropertyCount`
  - Inherited properties only.
- `usage`
  - Compact usage records.
- `properties`
  - Compact property summaries.

The renderer uses these records for compact index cards and visible type stats.

## Anchor Records

Each `anchors[]` record declares a canonical anchor.

Common fields:

- `anchor`
  - Hash target without the `#`.
- `kind`
  - One of `type-group`, `type`, or `property`.
- `label`
  - Display label.
- `type`
  - Present for type and property anchors.
- `property`
  - Present for property anchors.

The index keeps inherited properties out of `anchors[]` because their visible
rows should point back to canonical direct-property anchors.

## Inherited Reference Records

Each `inheritedReferences[]` record maps an inherited property appearance to
the original source property.

Fields:

- `type`
  - Type where the inherited property appears.
- `property`
  - Inherited property name.
- `label`
  - Property label.
- `sourceType`
  - Type that owns the canonical property.
- `sourceProperty`
  - Canonical property name.
- `sourceAnchor`
  - Canonical property anchor, such as `Resource.title`.

The renderer uses this relationship to send inherited-property links to the
source property and to apply the visible target highlight after navigation.

## How The Renderer Uses Both Files

The Python renderer receives both objects:

- `model`
  - Supplies the full content for type sections, property rows, descriptions,
    examples, inherited groups, glossary layout decisions, and guide stats.
- `guide_index`
  - Supplies compact navigation structures, Type Index grouping, table of
    contents groups, counts, and anchor lookup data.

The runtime HTML is static after generation. The two JSON files are still
published beside the guide so tools, tests, and future integrations can inspect
the same structured data that produced the page.

## Relationship To The NERDm JSON Schema

These files are documentation artifacts, not replacements for the NERDm JSON
Schema.

- `model/nerdm-schema.json`
  - Defines valid NERDm record structure for validation.
- `nerdm-doc-model.json`
  - Defines the guide content and rendering data extracted from the current
    schema view.
- `nerdm-guide-index.json`
  - Defines compact lookup and navigation data derived from the documentation
    model.

The schema answers whether a metadata record is valid. The documentation model
and guide index answer how the guide should explain and navigate the schema.
