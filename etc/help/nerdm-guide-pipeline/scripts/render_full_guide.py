#!/usr/bin/env python3
"""Render a standalone static full NERDm guide HTML preview."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import render_full_guide_html  # noqa: E402
from nerdm_pipeline.fragments import (  # noqa: E402
    extract_glossary_fragment,
    extract_intro_fragment,
)
from nerdm_pipeline.io import load_json, write_text  # noqa: E402
from nerdm_pipeline.schema_artifacts import build_schema_artifact  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to doc model JSON")
    parser.add_argument("--index", required=True, help="Path to guide index JSON")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--intro", help="Optional current intro body fragment")
    parser.add_argument("--glossary", help="Optional current glossary body fragment")
    parser.add_argument("--header", help="Optional original oar-docker headbar fragment")
    parser.add_argument("--footer", help="Optional original oar-docker footbar fragment")
    parser.add_argument(
        "--nerdm-schema",
        default="model/nerdm-schema.json",
        help="Current NERDm JSON Schema path",
    )
    parser.add_argument(
        "--stylesheet",
        default="nerdm-guide.css",
        help="Stylesheet href to include in the rendered HTML",
    )
    args = parser.parse_args()

    html = render_full_guide_html(
        load_json(args.model),
        load_json(args.index),
        stylesheet=args.stylesheet,
        intro_html=_load_intro(args.intro),
        glossary_html=_load_glossary(args.glossary),
        header_html=_load_text(args.header),
        footer_html=_load_text(args.footer),
        schema_artifact=build_schema_artifact(load_json(_resolve(args.nerdm_schema))),
    )
    write_text(args.output, html)


def _load_intro(path: str | None) -> str:
    if path is None:
        return ""
    return extract_intro_fragment(Path(path).read_text(encoding="utf-8"))


def _load_glossary(path: str | None) -> str:
    if path is None:
        return ""
    return extract_glossary_fragment(Path(path).read_text(encoding="utf-8"))


def _load_text(path: str | None) -> str:
    if path is None:
        return ""
    candidate = _resolve(path)
    return candidate.read_text(encoding="utf-8")


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate


if __name__ == "__main__":
    main()
