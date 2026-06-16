# NERDm Guide Pipeline

This folder contains the isolated build system for the redesigned NERDm guide.
It is separate from the current production guide files in `etc/help` and from
the existing jq workflow under `jq/`.

For the shortest command path, use `QUICK_USE_GUIDE.md`.

## Purpose

The pipeline turns the current NERDm documentation view into:

- a validated documentation model
- a compact guide index
- curated companion JSON data for record examples
- a rendered guide body fragment
- runtime CSS
- an oar-docker-compatible `nerdm-docs.tgz` package

Generated output is written under `dist/` and is not intended to be checked in.

## Main Commands

Build the local preview and runtime package:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh
```

Build only the local preview:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --preview-only
```

Build only the runtime tarball:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --package-only
```

Build and copy the tarball into oar-docker for local testing:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
  --package-only \
  --copy-to /path/to/oar-docker/apps/nginx-reverse-proxy/nerdm-docs.tgz
```

Serve the guide locally without Docker:

```sh
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh
```

Then open:

```text
http://127.0.0.1:8787/
```

Useful preview options:

```sh
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --enhanced
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --port 8791
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --no-build
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --prepare-only
```

## Script Reference

All scripts can be run from the repository root. Most paths may be absolute or
relative to the repository root.

### `scripts/build_pipeline.sh`

Top-level build entry point. It runs the preview build, the runtime package
build, or both.

Important flags:

- `--preview-only`: build only `dist/preview/`.
- `--package-only`: build only the oar-docker runtime package.
- `--tarball PATH`: write the runtime tarball to a custom path.
- `--copy-to PATH`: copy the generated tarball after packaging. If `PATH` is a
  directory, the tarball keeps its default filename inside that directory.
- `--move-to PATH`: move the generated tarball after packaging.
- `--python PATH`: run the pipeline with a specific Python interpreter.

Use `--package-only --copy-to .../nerdm-docs.tgz` when testing the generated
package in a local `oar-docker` setup.

### `scripts/serve_preview.sh`

Builds and serves a disposable local preview without Docker. It stages preview
HTML, CSS, JSON artifacts, schema files, and static oar-docker assets under a
temporary serve directory, then starts a Python HTTP server.

Important flags:

- `--enhanced`: serve `index.enhanced.html`, which includes the optional local
  JavaScript enhancements.
- `--no-build`: serve the existing files under `dist/preview/` without
  rebuilding first.
- `--prepare-only`: build and stage files, print the URL, and exit without
  starting the HTTP server.
- `--host HOST`: bind to a host other than `127.0.0.1`.
- `--port PORT`: bind to a port other than `8787`.
- `--serve-dir PATH`: stage files in a custom temporary directory.
- `--asset-root PATH`: use a specific oar-docker nginx reverse-proxy directory
  for `/css`, `/fonts`, and `/imgs`.
- `--python PATH`: run the server with a specific Python interpreter.

### `scripts/build_preview.py`

Lower-level preview builder used by `build_pipeline.sh --preview-only`. It
builds the documentation model, validates it, builds the guide index, loads
record examples, renders preview HTML, and validates generated HTML and CSS.

Important flags:

- `--source PATH`: source `nerdm-view.json`.
- `--model-output PATH`: output path for `nerdm-doc-model.json`.
- `--index-output PATH`: output path for `nerdm-guide-index.json`.
- `--preview-dir PATH`: directory for preview companion files.
- `--full-guide-output PATH`: output path for `index.html`.
- `--enhanced-guide-output PATH`: output path for `index.enhanced.html`.
- `--section-type TYPE`: render an additional named-type review page. Repeat
  the flag for multiple types.
- `--record-examples PATH`: curated record examples JSON input.

### `scripts/build_runtime_package.py`

Lower-level package builder used by `build_pipeline.sh --package-only`. It
builds the runtime body fragment, copies schema and JSON-LD support files,
writes runtime CSS and JSON artifacts, validates the generated output, and
creates `nerdm-docs.tgz`.

Important flags:

- `--output-dir PATH`: staging directory for the package contents.
- `--tarball PATH`: tarball output path.
- `--model-source-dir PATH`: directory containing schema and JSON-LD context
  files.
- `--render-dir PATH`: renderer CSS source directory.
- `--record-examples PATH`: curated record examples JSON input.

### Single-purpose helper scripts

These are mainly useful when inspecting intermediate artifacts or rendering a
single review page:

- `build_doc_model.py`: build only `nerdm-doc-model.json` from
  `nerdm-view.json`.
- `build_guide_index.py`: build only `nerdm-guide-index.json` from a
  documentation model.
- `render_full_guide.py`: render a standalone full-guide HTML page from an
  existing model and index.
- `render_type_index.py`: render a standalone Named Types index page.
- `render_type_section.py`: render one named-type detail page.

## Runtime Package

The runtime handoff artifact is:

```text
etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz
```

The tarball keeps the oar-docker docs package contract:

```text
docs/nerdm-context.jsonld
docs/nerdm-pub-context.jsonld
docs/nerdm-schema-context.jsonld
docs/nerdm-schema/
docs/nerdm/nerdm-guide-body.html
docs/nerdm/helpview.css
docs/nerdm/type-index.css
docs/nerdm/type-section.css
docs/nerdm/nerdm-guide-index.json
docs/nerdm/nerdm-doc-model.json
docs/nerdm/nerdm-record-examples.json
```

`nerdm-guide-body.html` is a body fragment. oar-docker provides the page shell,
header, footer, and routing.

## Source Inputs

The current pipeline reads:

- `etc/help/nerdm-view.json`
- `etc/help/nerdm-guide-pipeline/fragments/nerdm-intro-body.html`
- `etc/help/nerdm-guide-pipeline/fragments/nerdm-glossary-body.html`
- `model/nerdm-schema.json`
- `model/nerdm-schema-*.json`
- `model/nerdm-pub-schema.json`
- `model/nerdm-pub-schema-*.json`
- `model/*.jsonld`
- `etc/help/nerdm-guide-pipeline/data/record-examples.json`
- renderer assets under `etc/help/nerdm-guide-pipeline/renderers/`
- preview-only oar-docker shell fragments under
  `etc/help/reference/runtime/oar-docker-apps/apps/nginx-reverse-proxy/docs/`

`nerdm-view.json` is the current manually edited documentation view. It is not
the raw JSON Schema.

When the source view becomes fully regenerated, human guide edits should move
into a checked-in documentation-model overlay that is applied before index and
HTML rendering.

## Current Layout

```text
etc/help/nerdm-guide-pipeline/
  .gitignore
  QUICK_USE_GUIDE.md
  README.md
  model/
    nerdm-doc-model.schema.json
  data/
    record-examples.json
  fragments/
    nerdm-glossary-body.html
    nerdm-intro-body.html
  python/
    nerdm_pipeline/
  renderers/
    nerdm-guide.css
    nerdm-guide.enhancements.js
    type-index.css
    type-section.css
  scripts/
    build_doc_model.py
    build_guide_index.py
    build_pipeline.sh
    build_preview.py
    build_runtime_package.py
    render_full_guide.py
    render_type_index.py
    render_type_section.py
    serve_preview.sh
```

## Generated Output

Preview output:

```text
dist/preview/index.html
dist/preview/index.enhanced.html
dist/preview/type-index.html
dist/preview/type-section.Resource.html
dist/preview/type-section.DataFile.html
dist/preview/nerdm-doc-model.json
dist/preview/nerdm-guide-index.json
dist/preview/nerdm-record-examples.json
```

Runtime package staging:

```text
dist/nerdm-docs/
dist/nerdm-docs.tgz
```

These files are regenerated by the scripts and ignored by git.

## Validation

The build validates:

- documentation model shape
- duplicate HTML IDs
- unresolved same-page fragment links
- script elements in generated runtime HTML
- inline style attributes
- inline event handlers
- `javascript:` URLs
- CSP-hostile CSS URL patterns

Validation code lives in:

```text
python/nerdm_pipeline/validate.py
```
