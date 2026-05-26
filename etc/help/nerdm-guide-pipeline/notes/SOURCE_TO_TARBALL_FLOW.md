# Source To Tarball Flow

This note describes the pipeline from source files to the `nerdm-docs.tgz`
runtime package used by oar-docker.

## Short Version

Run:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh
```

That script runs two stages:

1. Preview rendering through `scripts/build_preview.py`.
2. Runtime packaging through `scripts/build_runtime_package.py`.

For oar-docker testing, run:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
  --package-only \
  --copy-to /Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy/nerdm-docs.tgz
```

That builds the runtime tarball and copies it into the nginx reverse-proxy app.

## Pipeline Steps

### 1. Start With Source Inputs

The runtime packaging stage starts from these source files:

- `etc/help/nerdm-view.json`
  - Main structured source for generated NERDm named types and properties.
  - Existing checked-in file from the old NERDm documentation workflow.
  - It is a manually edited schema-view document, not the schema itself.
  - The unedited generated counterpart is `etc/help/nerdm-view-unedited.json`.
  - The old workflow generated that schema-view shape from
    `model/nerdm-schema.json` and `model/nerdm-pub-schema.json` with
    `jq/schema2viewhelp.jq`, then edited the view for reader-facing content.
- `etc/help/nerdm-guide-pipeline/fragments/nerdm-intro-body.html`
  - Hand-authored Introduction content for the redesigned guide.
  - Kept inside the isolated pipeline so the current production guide files
    can remain unchanged until integration.
- `etc/help/nerdm-guide-pipeline/fragments/nerdm-glossary-body.html`
  - Hand-authored Glossary content for the redesigned guide.
  - Kept inside the isolated pipeline so the current production guide files
    can remain unchanged until integration.
- `model/nerdm-schema.json`
  - Current NERDm JSON Schema.
  - Used to expose the schema artifact and read the visible schema version.
  - Existing checked-in schema file under `model/`.
- `model/nerdm-schema-*.json`
  - Versioned NERDm schemas copied into the runtime package.
  - Existing checked-in schema snapshots under `model/`.
- `model/nerdm-pub-schema.json` and `model/nerdm-pub-schema-*.json`
  - Public-data extension schemas copied into the runtime package.
  - Existing checked-in extension schema files under `model/`.
- `model/*.jsonld`
  - JSON-LD context files copied into the runtime package.
  - Existing checked-in context files under `model/`.
  - The runtime package copies `nerdm-context.jsonld`,
    `nerdm-pub-context.jsonld`, and `nerdm-schema-context.jsonld`.
- `renderers/*.css`
  - Source CSS for the generated guide.
  - New local CSS files in the isolated `nerdm-guide-pipeline`.
  - These are maintained as renderer assets and converted to runtime CSS
    during packaging.

### 2. Build The Documentation Model

`scripts/build_runtime_package.py` loads `etc/help/nerdm-view.json` and passes
it to:

```text
python/nerdm_pipeline/model.py
```

That produces an in-memory documentation model with:

- model metadata
- ordered type groups
- named types
- direct properties
- inherited properties
- descriptions
- examples
- anchors
- source pointers

The same shape is written by the preview stage to:

```text
dist/preview/nerdm-doc-model.json
```

During runtime packaging, a copy is written to:

```text
dist/nerdm-docs/docs/nerdm/nerdm-doc-model.json
```

The model is validated against:

```text
model/nerdm-doc-model.schema.json
```

### 3. Build The Guide Index

The documentation model is then passed to:

```text
python/nerdm_pipeline/index.py
```

That produces a compact guide index with:

- type group order
- type anchors
- property counts
- direct-property anchors
- inherited-property references
- source anchors for inherited links

The preview stage writes this to:

```text
dist/preview/nerdm-guide-index.json
```

Runtime packaging writes a copy to:

```text
dist/nerdm-docs/docs/nerdm/nerdm-guide-index.json
```

### 4. Extract Existing Hand-authored Content

The packaging stage reads the existing guide fragments:

```text
etc/help/nerdm-guide-pipeline/fragments/nerdm-intro-body.html
etc/help/nerdm-guide-pipeline/fragments/nerdm-glossary-body.html
```

It passes them through:

```text
python/nerdm_pipeline/fragments.py
```

That extracts only the reusable Introduction and Glossary body content. Those
fragments are then fed into the renderer next to the generated NERDm reference
content.

### 5. Read Schema Artifact Metadata

The packaging stage reads:

```text
model/nerdm-schema.json
```

It passes that schema to:

```text
python/nerdm_pipeline/schema_artifacts.py
```

That reads the schema `id`, extracts the current version, and returns the Data
artifacts metadata used by the renderer. For the current schema, this produces:

```text
v0.7
```

### 6. Render The Runtime Guide Body

The renderer receives:

- the documentation model
- the guide index
- the extracted Introduction fragment
- the extracted Glossary fragment
- the schema artifact metadata

Those inputs are passed to:

```text
python/nerdm_pipeline/render.py
```

The renderer produces:

```text
dist/nerdm-docs/docs/nerdm/nerdm-guide-body.html
```

That file is a body fragment, not a full HTML document. oar-docker wraps it
with the existing guide head, header, footer, and page shell.

### 7. Convert Renderer CSS To Runtime CSS

The packaging stage reads:

```text
renderers/nerdm-guide.css
renderers/type-index.css
renderers/type-section.css
```

It writes runtime CSS to:

```text
dist/nerdm-docs/docs/nerdm/helpview.css
dist/nerdm-docs/docs/nerdm/type-index.css
dist/nerdm-docs/docs/nerdm/type-section.css
```

The main CSS imports the renderer CSS companion files by their runtime names.

### 8. Copy Schema And Context Files

The packaging stage copies JSON-LD context files from `model/` into:

```text
dist/nerdm-docs/docs/
```

It also copies current and versioned schemas into:

```text
dist/nerdm-docs/docs/nerdm-schema/
dist/nerdm-docs/docs/nerdm-schema/pub/
```

For each schema, the script reads the schema `id` and creates a version link.
For example, `model/nerdm-schema.json` has an id ending in `/v0.7#`, so the
package includes:

```text
docs/nerdm-schema/nerdm-schema.json
docs/nerdm-schema/v0.7
```

### 9. Validate Generated Output

Before creating the tarball, the packaging stage validates:

- model structure
- duplicate HTML IDs
- broken same-page fragment links
- script elements in generated HTML
- inline style attributes
- inline event handlers
- `javascript:` URLs
- CSP-hostile CSS URL patterns

The validation code lives in:

```text
python/nerdm_pipeline/validate.py
```

### 10. Create The Runtime Tarball

After staging and validation, the packaging stage creates:

```text
etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz
```

The tarball contains the oar-docker-compatible layout:

```text
docs/nerdm/nerdm-guide-body.html
docs/nerdm/helpview.css
docs/nerdm/type-index.css
docs/nerdm/type-section.css
docs/nerdm/nerdm-guide-index.json
docs/nerdm/nerdm-doc-model.json
docs/nerdm-schema/nerdm-schema.json
docs/nerdm-schema/v0.7
docs/nerdm-context.jsonld
docs/nerdm-pub-context.jsonld
docs/nerdm-schema-context.jsonld
```

### 11. Copy Or Move The Tarball

If `--copy-to` is provided, `scripts/build_pipeline.sh` copies the generated
tarball to the requested destination.

If `--move-to` is provided, it moves the generated tarball instead.

Example:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
  --package-only \
  --copy-to /Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy/nerdm-docs.tgz
```

That copies the tarball into the oar-docker nginx reverse-proxy app for local
testing.

### 12. Build And Run oar-docker

After copying the tarball, use the existing oar-docker flow:

```sh
../scripts/oarctl local build nginxreverseproxy
../scripts/oarctl local up
```

The nginx reverse-proxy image unpacks `nerdm-docs.tgz` using the same path
layout as the old guide package.

## Preview Flow

For source review without Docker, run:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --preview-only
```

That calls:

```text
scripts/build_preview.py
```

The preview stage follows the same model and index generation path, then
renders standalone review files under `dist/preview/`:

```text
dist/preview/index.html
dist/preview/index.enhanced.html
dist/preview/type-index.html
dist/preview/type-section.Resource.html
dist/preview/type-section.DataFile.html
```

The enhanced preview includes:

```text
renderers/nerdm-guide.enhancements.js
```

That script is for local testing only. It is not included in the runtime
tarball while CSP does not allow the guide script.

## Source And Output Summary

The flow is:

```text
etc/help/nerdm-view.json
  -> python/nerdm_pipeline/model.py
  -> nerdm-doc-model.json
  -> python/nerdm_pipeline/index.py
  -> nerdm-guide-index.json

nerdm-doc-model.json
nerdm-guide-index.json
intro fragment
glossary fragment
schema artifact metadata
  -> python/nerdm_pipeline/render.py
  -> docs/nerdm/nerdm-guide-body.html

renderer CSS
  -> runtime CSS

schema and context files
  -> docs/nerdm-schema/ and docs/*.jsonld

staged runtime files
  -> dist/nerdm-docs.tgz
  -> optional --copy-to or --move-to destination
```

## Current Rule

The new system remains self-contained under `etc/help/nerdm-guide-pipeline/`.
Existing production guide files and remote repositories are not changed by the
build commands.
