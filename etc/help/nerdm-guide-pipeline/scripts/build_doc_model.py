#!/usr/bin/env python3
"""Build nerdm-doc-model.json from nerdm-view.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import build_doc_model  # noqa: E402
from nerdm_pipeline.io import load_json, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the NERDm documentation model from nerdm-view.json."
    )
    parser.add_argument("--source", required=True, help="Path to nerdm-view.json")
    parser.add_argument("--output", required=True, help="Output model JSON path")
    args = parser.parse_args()

    write_json(args.output, build_doc_model(load_json(args.source)))


if __name__ == "__main__":
    main()
