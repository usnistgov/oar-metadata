# NERDm Guide Pipeline Quick Use Guide

Run commands from the repository root unless noted otherwise.

## Build Everything

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh
```

This builds:

- `dist/preview/`
- `dist/nerdm-docs/`
- `dist/nerdm-docs.tgz`

The build validates the documentation model, generated HTML, and runtime CSS.

## Preview Locally

```sh
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh
```

Open:

```text
http://127.0.0.1:8787/
```

Common preview options:

```sh
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --port 8791
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --enhanced
etc/help/nerdm-guide-pipeline/scripts/serve_preview.sh --prepare-only
```

`--prepare-only` builds and stages the preview files, prints the URL, and does
not start the HTTP server.

## Build Only One Output

Preview only:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --preview-only
```

Runtime package only:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --package-only
```

## Hand Off To oar-docker

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
  --package-only \
  --copy-to /Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy/nerdm-docs.tgz
```

The tarball contains the oar-docker docs package contract, including:

- `docs/nerdm/nerdm-guide-body.html`
- `docs/nerdm/helpview.css`
- `docs/nerdm/type-index.css`
- `docs/nerdm/type-section.css`
- `docs/nerdm/nerdm-guide-index.json`
- `docs/nerdm/nerdm-doc-model.json`
- `docs/nerdm/nerdm-record-examples.json`
- `docs/nerdm-schema/`
- `docs/*.jsonld`

## Edit Source, Not Output

Do not edit files under `dist/`. They are generated and ignored by git.

Use these source locations instead:

- Guide fragments: `fragments/`
- Curated companion data: `data/`
- Python build and render logic: `python/nerdm_pipeline/`
- CSS and optional preview JavaScript: `renderers/`
- Build and preview commands: `scripts/`
