#!/usr/bin/env python3
"""Build an oar-docker-compatible NERDm guide runtime package."""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
from pathlib import Path


sys.dont_write_bytecode = True

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PIPELINE_ROOT / "python"))

from nerdm_pipeline import (  # noqa: E402
    build_doc_model,
    build_guide_index,
    load_curated_data,
    render_guide_body_html,
)
from nerdm_pipeline.fragments import (  # noqa: E402
    extract_glossary_fragment,
    extract_intro_fragment,
)
from nerdm_pipeline.io import load_json, write_json, write_text  # noqa: E402
from nerdm_pipeline.schema_artifacts import build_schema_artifact  # noqa: E402
from nerdm_pipeline.validate import (  # noqa: E402
    raise_for_html_validation_errors,
    validate_css_files,
    validate_generated_html,
    validate_model_contract,
)


RUNTIME_DOC_ROOT = Path("docs/nerdm")


def main() -> None:
    args = _parse_args()

    source = _resolve(args.source)
    schema_path = _resolve(args.schema)
    model_source_dir = _resolve(args.model_source_dir)
    output_dir = _resolve(args.output_dir)
    tarball = _resolve(args.tarball)
    render_dir = _resolve(args.render_dir)
    package_root = output_dir / "docs"
    package_doc_dir = output_dir / RUNTIME_DOC_ROOT
    body_output = package_doc_dir / "nerdm-guide-body.html"
    model_output = package_doc_dir / "nerdm-doc-model.json"
    index_output = package_doc_dir / "nerdm-guide-index.json"
    help_css_output = package_doc_dir / "helpview.css"
    type_index_css_output = package_doc_dir / "type-index.css"
    type_section_css_output = package_doc_dir / "type-section.css"
    record_examples_output = package_doc_dir / "nerdm-record-examples.json"

    print("Building documentation model")
    model = build_doc_model(load_json(source))
    validate_model_contract(model, load_json(schema_path))

    print("Building structured guide index")
    guide_index = build_guide_index(model)

    print("Loading curated guide data")
    curated_data = load_curated_data(
        record_examples_path=str(_resolve(args.record_examples)),
        model=model,
    )

    print("Rendering runtime guide body")
    schema_artifact = build_schema_artifact(
        load_json(model_source_dir / "nerdm-schema.json")
    )
    guide_body = render_guide_body_html(
        model,
        guide_index,
        intro_html=extract_intro_fragment(
            _resolve(args.intro).read_text(encoding="utf-8")
        ),
        glossary_html=extract_glossary_fragment(
            _resolve(args.glossary).read_text(encoding="utf-8")
        ),
        schema_artifact=schema_artifact,
        record_examples=curated_data["recordExamples"],
    )

    print("Writing runtime package files")
    support_files = _write_support_docs(model_source_dir, package_root)
    write_text(body_output, guide_body)
    write_json(model_output, model)
    write_json(index_output, guide_index)
    write_json(record_examples_output, curated_data["recordExamples"])
    write_text(help_css_output, _runtime_helpview_css(render_dir))
    write_text(type_index_css_output, _runtime_css(render_dir / "type-index.css"))
    write_text(type_section_css_output, _runtime_css(render_dir / "type-section.css"))

    print("Checking runtime HTML")
    html_result = validate_generated_html(body_output)
    raise_for_html_validation_errors(html_result)

    print("Checking runtime CSS")
    css_issues = validate_css_files(
        [help_css_output, type_index_css_output, type_section_css_output]
    )
    if css_issues:
        raise RuntimeError("\n".join(css_issues))

    print("Creating oar-docker tarball")
    package_files = [
        *support_files,
        body_output,
        help_css_output,
        type_index_css_output,
        type_section_css_output,
        index_output,
        model_output,
        record_examples_output,
    ]
    _write_tarball(tarball, output_dir, package_files)

    print("")
    print("Runtime package build complete")
    print(f"  Package dir: {_display_path(output_dir)}")
    print(f"  Tarball: {_display_path(tarball)}")
    print(f"  Body: {_display_path(body_output)}")
    print(f"  Index: {_display_path(index_output)}")
    print(f"  Model: {_display_path(model_output)}")
    print(f"  Types: {guide_index['counts']['types']}")
    print(f"  Properties: {guide_index['counts']['properties']}")
    print(f"  HTML IDs: {html_result.id_count}")
    print(f"  Internal links: {html_result.fragment_link_count}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an oar-docker-compatible NERDm guide runtime package."
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
        "--render-dir",
        default="etc/help/nerdm-guide-pipeline/renderers",
        help="Renderer source asset directory",
    )
    parser.add_argument(
        "--model-source-dir",
        default="model",
        help="Source directory containing current schema and JSON-LD context files",
    )
    parser.add_argument(
        "--record-examples",
        default="etc/help/nerdm-guide-pipeline/data/record-examples.json",
        help="Curated record examples JSON path",
    )
    parser.add_argument(
        "--output-dir",
        default="etc/help/nerdm-guide-pipeline/dist/nerdm-docs",
        help="Runtime package staging directory",
    )
    parser.add_argument(
        "--tarball",
        default="etc/help/nerdm-guide-pipeline/dist/nerdm-docs.tgz",
        help="Runtime tarball output path",
    )
    return parser.parse_args()


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _runtime_helpview_css(render_dir: Path) -> str:
    return _runtime_css(render_dir / "nerdm-guide.css")


def _runtime_css(path: Path) -> str:
    """Return CSS suitable for the oar-docker package."""

    text = path.read_text(encoding="utf-8")
    return text.replace("/* preview-only */", "").rstrip() + "\n"


def _write_support_docs(model_source_dir: Path, package_root: Path) -> list[Path]:
    """Copy schema and JSON-LD files required by the published docs route."""

    package_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    for name in [
        "nerdm-schema-context.jsonld",
        "nerdm-pub-context.jsonld",
        "nerdm-context.jsonld",
    ]:
        source = model_source_dir / name
        output = package_root / name
        _copy_file(source, output)
        outputs.append(output)

    for schema_name in ["nerdm", "nerdm-pub"]:
        sources = sorted(model_source_dir.glob(f"{schema_name}-schema-*.json"))
        current = model_source_dir / f"{schema_name}-schema.json"
        if current.exists():
            sources.append(current)

        for source in sources:
            schema_output, version_link = _install_schema(source, package_root)
            outputs.extend([schema_output, version_link])

    return outputs


def _copy_file(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)


def _install_schema(source: Path, package_root: Path) -> tuple[Path, Path]:
    """Copy one schema file and create the version alias used by oar-docker."""

    schema = load_json(source)
    identifier = schema.get("@id") or schema.get("id")
    if not isinstance(identifier, str) or "/od/dm/" not in identifier:
        raise ValueError(f"{source}: schema id must include /od/dm/")

    id_path = identifier.split("/od/dm/", 1)[1].strip("#/")
    path_part, version = id_path.rsplit("/", 1)
    output_dir = package_root / path_part
    output = output_dir / source.name
    version_link = output_dir / version

    _copy_file(source, output)
    _replace_symlink(version_link, source.name)
    return output, version_link


def _replace_symlink(path: Path, target_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.exists():
        path.unlink()
    path.symlink_to(target_name)


def _write_tarball(tarball: Path, package_root: Path, package_files: list[Path]) -> None:
    tarball.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "w:gz") as archive:
        for path in package_files:
            archive.add(path, arcname=path.relative_to(package_root))


if __name__ == "__main__":
    main()
