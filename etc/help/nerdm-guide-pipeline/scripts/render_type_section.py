#!/usr/bin/env python3
"""Render a standalone static Named Type section HTML review page."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import render_type_section_html  # noqa: E402
from nerdm_pipeline.io import load_json, write_text  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to doc model JSON")
    parser.add_argument("--type", required=True, help="NERDm type name to render")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument(
        "--stylesheet",
        default="type-section.css",
        help="Stylesheet href to include in the rendered HTML",
    )
    args = parser.parse_args()

    html = render_type_section_html(
        load_json(args.model),
        args.type,
        stylesheet=args.stylesheet,
    )
    write_text(args.output, html)


if __name__ == "__main__":
    main()
