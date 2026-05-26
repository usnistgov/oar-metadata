#!/usr/bin/env python3
"""Build nerdm-guide-index.json from nerdm-doc-model.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import build_guide_index  # noqa: E402
from nerdm_pipeline.io import load_json, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to doc model JSON")
    parser.add_argument("--output", required=True, help="Output index JSON path")
    args = parser.parse_args()

    write_json(args.output, build_guide_index(load_json(args.model)))


if __name__ == "__main__":
    main()
