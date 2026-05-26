#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PIPELINE_ROOT/../../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_PREVIEW=1
RUN_PACKAGE=1
TARBALL_PATH="etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz"
COPY_DEST=""
MOVE_DEST=""

usage() {
  cat <<'USAGE'
Build the isolated NERDm guide pipeline.

Usage:
  build_pipeline.sh [options]

Default behavior:
  Runs the preview renderer, builds the runtime package, and writes:
    etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz

Options:
  --preview-only
      Run only the preview renderer.

  --package-only
      Run only the runtime package builder.

  --tarball PATH
      Override runtime tarball output path. Relative paths are resolved from
      the oar-metadata repository root.

  --copy-to PATH
      Copy the generated tarball to PATH after packaging. If PATH is an
      existing directory, the tarball is copied into that directory.

  --move-to PATH
      Move the generated tarball to PATH after packaging. If PATH is an
      existing directory, the tarball is moved into that directory.

  --python PATH
      Python interpreter to use. Defaults to python3 or PYTHON_BIN.

  -h, --help
      Show this help.

Examples:
  etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh

  etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh --package-only

  etc/help/nerdm-guide-pipeline/scripts/build_pipeline.sh \
    --copy-to /Users/one1/projects/oar/oar-docker-apps/apps/nginx-reverse-proxy/nerdm-docs.tgz
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

destination_path() {
  local dest="$1"
  local source="$2"

  if [[ -d "$dest" ]]; then
    printf '%s/%s\n' "${dest%/}" "$(basename "$source")"
    return
  fi

  case "$dest" in
    */) printf '%s%s\n' "$dest" "$(basename "$source")" ;;
    *) printf '%s\n' "$dest" ;;
  esac
}

copy_or_move_tarball() {
  local action="$1"
  local dest="$2"
  local source
  local target
  local parent

  source="$(resolve_path "$TARBALL_PATH")"
  [[ -f "$source" ]] || die "tarball was not found: $source"

  target="$(destination_path "$dest" "$source")"
  parent="$(dirname "$target")"
  mkdir -p "$parent"

  if [[ "$action" == "copy" ]]; then
    cp "$source" "$target"
    printf 'Copied tarball to: %s\n' "$target"
  else
    mv "$source" "$target"
    printf 'Moved tarball to: %s\n' "$target"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preview-only)
      RUN_PREVIEW=1
      RUN_PACKAGE=0
      shift
      ;;
    --package-only)
      RUN_PREVIEW=0
      RUN_PACKAGE=1
      shift
      ;;
    --tarball)
      [[ $# -ge 2 ]] || die "--tarball requires a path"
      TARBALL_PATH="$2"
      shift 2
      ;;
    --copy-to)
      [[ $# -ge 2 ]] || die "--copy-to requires a path"
      COPY_DEST="$2"
      shift 2
      ;;
    --move-to)
      [[ $# -ge 2 ]] || die "--move-to requires a path"
      MOVE_DEST="$2"
      shift 2
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

if [[ -n "$COPY_DEST" && -n "$MOVE_DEST" ]]; then
  die "use only one of --copy-to or --move-to"
fi

if [[ -n "$COPY_DEST$MOVE_DEST" && "$RUN_PACKAGE" -ne 1 ]]; then
  die "tarball destination flags require package generation"
fi

cd "$REPO_ROOT"

if [[ "$RUN_PREVIEW" -eq 1 ]]; then
  "$PYTHON_BIN" etc/help/nerdm-guide-pipeline/scripts/build_preview.py
fi

if [[ "$RUN_PACKAGE" -eq 1 ]]; then
  "$PYTHON_BIN" etc/help/nerdm-guide-pipeline/scripts/build_runtime_package.py \
    --tarball "$TARBALL_PATH"
fi

if [[ -n "$COPY_DEST" ]]; then
  copy_or_move_tarball copy "$COPY_DEST"
fi

if [[ -n "$MOVE_DEST" ]]; then
  copy_or_move_tarball move "$MOVE_DEST"
fi
