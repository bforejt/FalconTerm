"""Tests for SessionStore CRUD + hierarchy."""

from __future__ import annotations

import sys

from falconterm.models.session import new_folder, new_ssh_session

# Qt's QObject is required by SessionStore; skip the whole module if Qt can't load.
try:
    from PySide6.QtCore import QCoreApplication

    _app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    from falconterm.services.session_store import SessionStore

    _QT_OK = True
except Exception:
    _QT_OK = False

import pytest

pytestmark = pytest.mark.skipif(not _QT_OK, reason="Qt platform plugin unavailable")


def test_add_and_get(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "sessions.json")
    n = new_ssh_session("web01", "10.0.0.1", "admin")
    store.add(n)
    assert store.get(n.id) is not None
    assert store.get(n.id).name == "web01"


def test_persistence(tmp_path) -> None:
    p = tmp_path / "sessions.json"
    store = SessionStore(path=p)
    store.add(new_ssh_session("a", "h1", "u"))
    store.add(new_ssh_session("b", "h2", "u"))
    # Reload from disk
    store2 = SessionStore(path=p)
    assert len(store2.nodes) == 2


def test_hierarchy(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "s.json")
    root = store.add(new_folder("Core"))
    child = store.add(new_folder("Switches", parent=root.id))
    sess = store.add(new_ssh_session("sw1", "10.1.1.1", "admin", parent=child.id))
    # children()
    assert store.children(None) == [root]
    assert store.children(root.id) == [child]
    assert store.children(child.id) == [sess]
    # path_to
    path = store.path_to(sess.id)
    assert [p.id for p in path] == [root.id, child.id, sess.id]


def test_delete_cascades(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "s.json")
    root = store.add(new_folder("Core"))
    child = store.add(new_folder("Nested", parent=root.id))
    sess = store.add(new_ssh_session("s", "h", "u", parent=child.id))
    store.delete(root.id)
    assert store.get(root.id) is None
    assert store.get(child.id) is None
    assert store.get(sess.id) is None


def test_move_detects_cycles(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "s.json")
    a = store.add(new_folder("A"))
    b = store.add(new_folder("B", parent=a.id))
    # Moving A into B's subtree should raise.
    import pytest

    with pytest.raises(ValueError):
        store.move(a.id, b.id)


def test_duplicate(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "s.json")
    orig = store.add(new_ssh_session("original", "h", "u"))
    dup = store.duplicate(orig.id)
    assert dup is not None
    assert dup.id != orig.id
    assert "Copy" in dup.name


def test_merge_regenerates_ids(tmp_path) -> None:
    store = SessionStore(path=tmp_path / "s.json")
    folder = new_folder("X")
    sess = new_ssh_session("y", "h", "u", parent=folder.id)
    store.merge([folder, sess])
    # Parent ref fixed
    by_name = {n.name: n for n in store.nodes}
    assert by_name["y"].parent == by_name["X"].id
