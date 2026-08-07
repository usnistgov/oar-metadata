# OAR Docker Integration Guide

This guide describes how the isolated NERDm guide pipeline can be plugged into
`oar-docker-apps` without changing the existing Docker assembly pattern.

## Runtime Contract

The existing nginx reverse-proxy image already expects a `nerdm-docs.tgz`
archive with guide files under `docs/nerdm/`.

The new pipeline preserves that contract by generating:

```text
etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz
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
```

`nerdm-guide-body.html` is intentionally a body fragment, not a complete HTML
document. `oar-docker-apps` should continue wrapping it with the existing
`nerdm-guide-head.html`, `headbar.html`, `footbar.html`, and
`nerdm-guide-foot.html` fragments.

## Build The Package

From the `oar-metadata` repository root:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --package-only
```

The command rebuilds the structured documentation model, structured guide
index, runtime body fragment, runtime CSS, and tarball. It also checks:

- Model contract.
- Duplicate HTML IDs.
- Broken same-page fragment links.
- CSP-sensitive generated markup.
- CSP-hostile CSS URL patterns.

## Local oar-docker Swap

To build the package and copy the generated tarball into the existing nginx
reverse-proxy app location:

```sh
etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
  --package-only \
  --copy-to /Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy/nerdm-docs.tgz
```

Then rebuild or restart the local Docker flow the same way the current guide is
tested. No Dockerfile change is required for the guide body and CSS swap,
because the archive keeps the old package layout, including schema/context
files and version symlinks.

After the archive is installed, the guide should expose the generated JSON
artifacts beside the page and the current schema beside the schema docs:

```text
/od/dm/nerdm/nerdm-guide-index.json
/od/dm/nerdm/nerdm-doc-model.json
/od/dm/nerdm-schema/nerdm-schema.json
```

The guide body links to these files from a `Data artifacts` card below the
right-side table of contents. Each artifact item carries its own version pill.

## What Stays In oar-docker

Keep these runtime assets in `oar-docker-apps`:

- `apps/nginx-reverse-proxy/docs/nerdm-guide/nerdm-guide-head.html`
- `apps/nginx-reverse-proxy/docs/nerdm-guide/nerdm-guide-foot.html`
- `apps/nginx-reverse-proxy/docs/headbar.html`
- `apps/nginx-reverse-proxy/docs/footbar.html`
- `apps/nginx-reverse-proxy/css/oardm.css`
- `apps/nginx-reverse-proxy/font-awesome.tgz`

The new guide package relies on those existing wrapper assets. Font Awesome is
still needed by the original footer social icons, even though the redesigned
guide content uses inline SVG icons for its own controls.

## JavaScript Policy

The runtime package does not enable JavaScript. The Type Index filter and
scroll-spy behavior remain optional progressive enhancements in the source
pipeline, but they should not be shipped until the site CSP allows the guide
script.

The local enhancement script keeps table-of-contents auto-open behavior off by
default through `AUTO_OPEN_TOC_GROUPS = false`, so normal scrolling does not
expand collapsed type groups. The setting can be changed later if that behavior
is wanted.

Future script-gated UI work should remain dormant until CSP allows the guide
script.

The standalone preview already emits JSON discovery links in its head. Runtime
integration should add the same `rel="alternate"` links to the oar-docker guide
head wrapper when the new package becomes the normal source of the page.

When CSP is ready for scripts, the integration should be explicit:

- Include `nerdm-guide.enhancements.js` in the runtime package.
- Add a normal external script tag in the page wrapper.
- Update CSP in the owning runtime configuration to allow that script.

Until then, collapsible sections, the table of contents, and back-to-top link
work without JavaScript.

## Migration Rule

The isolated pipeline should remain self-contained until the replacement is
intentional. Do not overwrite the existing source guide files in `etc/help/`
from this pipeline; use the generated tarball as the integration boundary.
