#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PIPELINE_ROOT/../../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="127.0.0.1"
PORT="8787"
SERVE_DIR="/private/tmp/nerdm-guide-preview"
BUILD=1
ENHANCED=0
ASSET_ROOT=""

usage() {
  cat <<'USAGE'
Build and serve the local NERDm guide preview.

Usage:
  serve_preview.sh [options]

Default behavior:
  Builds the preview, stages the generated files plus needed static assets
  under /private/tmp/nerdm-guide-preview, then serves:
    http://127.0.0.1:8787/

Options:
  --enhanced
      Serve the local JavaScript-enhanced preview.

  --no-build
      Reuse existing generated preview files instead of rebuilding first.

  --host HOST
      Bind host. Default: 127.0.0.1.

  --port PORT
      Bind port. Default: 8787.

  --serve-dir PATH
      Override the temporary serve directory.

  --asset-root PATH
      Use PATH for /css, /fonts, and /imgs assets. Defaults to the local
      oar-docker nginx reverse-proxy app when present, then the saved runtime
      reference copy.

  --prepare-only
      Build and stage files, print the URL, but do not start the server.

  --python PATH
      Python interpreter to use. Defaults to python3 or PYTHON_BIN.

  -h, --help
      Show this help.
USAGE
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

resolve_path() {
  local path="$1"
  case "$path" in
    /*) printf '%s\n' "$path" ;;
    *) printf '%s/%s\n' "$REPO_ROOT" "$path" ;;
  esac
}

choose_asset_root() {
  local primary="/Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy"
  local fallback="$REPO_ROOT/etc/help/reference/runtime/oar-docker-apps/apps/nginx-reverse-proxy"

  if [[ -n "$ASSET_ROOT" ]]; then
    printf '%s\n' "$(resolve_path "$ASSET_ROOT")"
    return
  fi

  if [[ -d "$primary" ]]; then
    printf '%s\n' "$primary"
    return
  fi

  if [[ -d "$fallback" ]]; then
    printf '%s\n' "$fallback"
    return
  fi

  die "could not find oar-docker asset root; pass --asset-root"
}

# Keep staged preview files disposable while serving shared static assets from
# either a local oar-docker checkout or the checked-in runtime reference copy.
stage_symlink() {
  local source="$1"
  local target="$2"

  [[ -e "$source" ]] || die "missing source: $source"
  rm -rf "$target"
  ln -s "$source" "$target"
}

stage_preview() {
  local render_dir="$PIPELINE_ROOT/renderers"
  local preview_dir="$PIPELINE_ROOT/dist/preview"
  local index_file="$preview_dir/nerdm-guide-index.json"
  local model_file="$preview_dir/nerdm-doc-model.json"
  local source_html="$preview_dir/index.html"
  local schema_layers_file="$preview_dir/nerdm-schema-layers.json"
  local record_examples_file="$preview_dir/nerdm-record-examples.json"
  local asset_root

  if [[ "$ENHANCED" -eq 1 ]]; then
    source_html="$preview_dir/index.enhanced.html"
  fi

  [[ -f "$source_html" ]] || die "missing preview HTML: $source_html"
  [[ -f "$index_file" ]] || die "missing guide index: $index_file"
  [[ -f "$model_file" ]] || die "missing documentation model: $model_file"
  [[ -f "$schema_layers_file" ]] || die "missing schema layers data: $schema_layers_file"
  [[ -f "$record_examples_file" ]] || die "missing record examples data: $record_examples_file"

  asset_root="$(choose_asset_root)"

  rm -rf "$SERVE_DIR"
  mkdir -p "$SERVE_DIR"

  cp "$source_html" "$SERVE_DIR/index.html"
  cp "$render_dir/nerdm-guide.css" "$SERVE_DIR/"
  cp "$render_dir/type-index.css" "$SERVE_DIR/"
  cp "$render_dir/type-section.css" "$SERVE_DIR/"
  cp "$index_file" "$SERVE_DIR/nerdm-guide-index.json"
  cp "$model_file" "$SERVE_DIR/nerdm-doc-model.json"
  cp "$schema_layers_file" "$SERVE_DIR/nerdm-schema-layers.json"
  cp "$record_examples_file" "$SERVE_DIR/nerdm-record-examples.json"

  if [[ "$ENHANCED" -eq 1 ]]; then
    cp "$render_dir/nerdm-guide.enhancements.js" "$SERVE_DIR/"
  fi

  stage_symlink "$REPO_ROOT/model" "$SERVE_DIR/nerdm-schema"
  stage_symlink "$asset_root/css" "$SERVE_DIR/css"
  stage_symlink "$asset_root/imgs" "$SERVE_DIR/imgs"

  if [[ -d "$asset_root/fonts" ]]; then
    stage_symlink "$asset_root/fonts" "$SERVE_DIR/fonts"
  fi
}

PREPARE_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enhanced)
      ENHANCED=1
      shift
      ;;
    --no-build)
      BUILD=0
      shift
      ;;
    --host)
      [[ $# -ge 2 ]] || die "--host requires a value"
      HOST="$2"
      shift 2
      ;;
    --port)
      [[ $# -ge 2 ]] || die "--port requires a value"
      PORT="$2"
      shift 2
      ;;
    --serve-dir)
      [[ $# -ge 2 ]] || die "--serve-dir requires a path"
      SERVE_DIR="$(resolve_path "$2")"
      shift 2
      ;;
    --asset-root)
      [[ $# -ge 2 ]] || die "--asset-root requires a path"
      ASSET_ROOT="$2"
      shift 2
      ;;
    --prepare-only)
      PREPARE_ONLY=1
      shift
      ;;
    --python)
      [[ $# -ge 2 ]] || die "--python requires a path"
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

cd "$REPO_ROOT"

if [[ "$BUILD" -eq 1 ]]; then
  "$SCRIPT_DIR/build_pipeline.sh" --preview-only --python "$PYTHON_BIN"
fi

stage_preview

printf 'Local NERDm guide preview: http://%s:%s/\n' "$HOST" "$PORT"
printf 'Serving directory: %s\n' "$SERVE_DIR"

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
  exit 0
fi

exec "$PYTHON_BIN" -m http.server "$PORT" --bind "$HOST" --directory "$SERVE_DIR"
