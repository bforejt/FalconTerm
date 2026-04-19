"""Tests for .ftsessions bundle import/export."""

from __future__ import annotations

from falconterm.models.session import SessionDocument, new_folder, new_ssh_session
from falconterm.models.settings import BUILTIN_SCHEMES
from falconterm.services.import_export import export_bundle, load_bundle


def test_roundtrip(tmp_path) -> None:
    doc = SessionDocument()
    f = new_folder("Prod")
    s = new_ssh_session("web01", "web.example.com", "root", parent=f.id)
    doc.nodes.extend([f, s])

    path = tmp_path / "out.ftsessions"
    export_bundle(doc, list(BUILTIN_SCHEMES), path)

    bundle = load_bundle(path)
    assert bundle.kind == "falconterm-bundle"
    assert len(bundle.nodes) == 2
    assert len(bundle.color_schemes) == len(BUILTIN_SCHEMES)

    # Tree structure preserved
    names = {n.name for n in bundle.nodes}
    assert names == {"Prod", "web01"}


def test_bundle_has_version(tmp_path) -> None:
    doc = SessionDocument()
    path = tmp_path / "empty.ftsessions"
    export_bundle(doc, [], path)
    bundle = load_bundle(path)
    assert bundle.version >= 1
