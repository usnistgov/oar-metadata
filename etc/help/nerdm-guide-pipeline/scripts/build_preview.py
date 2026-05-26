#!/usr/bin/env python3
"""Build and validate the local NERDm guide preview artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.dont_write_bytecode = True

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import (  # noqa: E402
    build_doc_model,
    build_guide_index,
    render_full_guide_html,
    render_type_index_html,
    render_type_section_html,
)
from nerdm_pipeline.fragments import (  # noqa: E402
    extract_glossary_fragment,
    extract_intro_fragment,
)
from nerdm_pipeline.io import load_json, write_json, write_text  # noqa: E402
from nerdm_pipeline.schema_artifacts import build_schema_artifact  # noqa: E402
from nerdm_pipeline.validate import (  # noqa: E402
    validate_css_files,
    validate_generated_html,
    validate_model_contract,
)


def main() -> None:
    args = _parse_args()

    source = _resolve(args.source)
    schema_path = _resolve(args.schema)
    model_output = _resolve(args.model_output)
    index_output = _resolve(args.index_output)
    render_dir = _resolve(args.render_dir)
    preview_dir = _resolve(args.preview_dir)
    full_guide_output = _resolve(args.full_guide_output)
    enhanced_guide_output = _resolve(args.enhanced_guide_output)
    type_index_output = _resolve(args.type_index_output)
    intro = _resolve(args.intro)
    glossary = _resolve(args.glossary)
    header = _resolve(args.header)
    footer = _resolve(args.footer)
    nerdm_schema = _resolve(args.nerdm_schema)

    print("Building documentation model")
    model = build_doc_model(load_json(source))
    write_json(model_output, model)

    print("Validating documentation model")
    validate_model_contract(model, load_json(schema_path))

    print("Building structured guide index")
    guide_index = build_guide_index(model)
    write_json(index_output, guide_index)

    print("Rendering full guide preview")
    schema_artifact = build_schema_artifact(load_json(nerdm_schema))
    full_guide_html = render_full_guide_html(
        model,
        guide_index,
        intro_html=extract_intro_fragment(intro.read_text(encoding="utf-8")),
        glossary_html=extract_glossary_fragment(glossary.read_text(encoding="utf-8")),
        header_html=header.read_text(encoding="utf-8"),
        footer_html=footer.read_text(encoding="utf-8"),
        schema_artifact=schema_artifact,
    )
    write_text(full_guide_output, full_guide_html)

    print("Rendering local JS enhancement test preview")
    write_text(
        enhanced_guide_output,
        _with_enhancement_script(full_guide_html, "nerdm-guide.enhancements.js"),
    )

    print("Rendering Type Index preview")
    write_text(type_index_output, render_type_index_html(guide_index))

    for type_name in args.section_type:
        output = preview_dir / f"type-section.{type_name}.html"
        print(f"Rendering Named Type preview: {type_name}")
        write_text(output, render_type_section_html(model, type_name))

    print("Checking generated HTML")
    html_result = validate_generated_html(full_guide_output)
    _raise_if_html_failed(html_result)

    print("Checking generated CSS")
    css_issues = validate_css_files(
        [
            render_dir / "nerdm-guide.css",
            render_dir / "type-index.css",
            render_dir / "type-section.css",
        ]
    )
    if css_issues:
        raise RuntimeError("\n".join(css_issues))

    print("")
    print("Preview build complete")
    print(f"  Model: {model_output.relative_to(REPO_ROOT)}")
    print(f"  Index: {index_output.relative_to(REPO_ROOT)}")
    print(f"  Full guide: {full_guide_output.relative_to(REPO_ROOT)}")
    print(f"  JS test guide: {enhanced_guide_output.relative_to(REPO_ROOT)}")
    print(f"  Types: {guide_index['counts']['types']}")
    print(f"  Properties: {guide_index['counts']['properties']}")
    print(f"  HTML IDs: {html_result.id_count}")
    print(f"  Internal links: {html_result.fragment_link_count}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and validate the local NERDm guide preview."
    )
    parser.add_argument(
        "--source",
        default="etc/help/nerdm-view.json",
        help="Source nerdm-view.json path",
    )
    parser.add_argument(
        "--schema",
        default="etc/help/nerdm-guide-pipeline/model/nerdm-doc-model.schema.json",
        help="Documentation model JSON Schema path",
    )
    parser.add_argument(
        "--model-output",
        default="etc/help/nerdm-guide-pipeline/dist/preview/nerdm-doc-model.json",
        help="Generated documentation model path",
    )
    parser.add_argument(
        "--index-output",
        default="etc/help/nerdm-guide-pipeline/dist/preview/nerdm-guide-index.json",
        help="Generated structured guide index path",
    )
    parser.add_argument(
        "--render-dir",
        default="etc/help/nerdm-guide-pipeline/renderers",
        help="Preview renderer output directory",
    )
    parser.add_argument(
        "--preview-dir",
        default="etc/help/nerdm-guide-pipeline/dist/preview",
        help="Generated preview output directory",
    )
    parser.add_argument(
        "--full-guide-output",
        default="etc/help/nerdm-guide-pipeline/dist/preview/index.html",
        help="Generated full-guide preview path",
    )
    parser.add_argument(
        "--enhanced-guide-output",
        default="etc/help/nerdm-guide-pipeline/dist/preview/index.enhanced.html",
        help="Generated local-only preview path that loads optional JS enhancements",
    )
    parser.add_argument(
        "--type-index-output",
        default="etc/help/nerdm-guide-pipeline/dist/preview/type-index.html",
        help="Generated Type Index preview path",
    )
    parser.add_argument(
        "--section-type",
        action="append",
        default=["Resource", "DataFile"],
        help="Named Type section preview to render. Repeat for more types.",
    )
    parser.add_argument(
        "--intro",
        default="etc/help/nerdm-guide-pipeline/fragments/nerdm-intro-body.html",
        help="Hand-authored intro fragment path",
    )
    parser.add_argument(
        "--glossary",
        default="etc/help/nerdm-guide-pipeline/fragments/nerdm-glossary-body.html",
        help="Hand-authored glossary fragment path",
    )
    parser.add_argument(
        "--header",
        default=(
            "etc/help/reference/runtime/oar-docker-apps/apps/"
            "nginx-reverse-proxy/docs/headbar.html"
        ),
        help="Original oar-docker headbar fragment path",
    )
    parser.add_argument(
        "--footer",
        default=(
            "etc/help/reference/runtime/oar-docker-apps/apps/"
            "nginx-reverse-proxy/docs/footbar.html"
        ),
        help="Original oar-docker footbar fragment path",
    )
    parser.add_argument(
        "--nerdm-schema",
        default="model/nerdm-schema.json",
        help="Current NERDm JSON Schema path",
    )
    return parser.parse_args()


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _with_enhancement_script(html: str, script_href: str) -> str:
    script = f'  <script src="{script_href}" defer></script>\n'
    return html.replace("</body>", f"{script}</body>")


def _raise_if_html_failed(html_result) -> None:
    failures: list[str] = []

    if html_result.duplicate_ids:
        failures.append(
            "Duplicate IDs:\n  " + "\n  ".join(html_result.duplicate_ids)
        )
    if html_result.unresolved_fragments:
        failures.append(
            "Unresolved fragment links:\n  "
            + "\n  ".join(html_result.unresolved_fragments)
        )
    if html_result.csp_issues:
        failures.append(
            "CSP-sensitive markup:\n  " + "\n  ".join(html_result.csp_issues)
        )

    if failures:
        raise RuntimeError("\n\n".join(failures))


if __name__ == "__main__":
    main()
