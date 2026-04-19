"""Load / save / mutate the session tree. Persists to sessions.json."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from falconterm.models.ids import new_id as _new_id
from falconterm.models.session import Node, SessionDocument
from falconterm.services.paths import sessions_file


class SessionStore(QObject):
    """Flat-node session tree with hierarchy via parent IDs.

    Emits `changed` whenever the tree is mutated or reloaded.
    """

    changed = Signal()

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self._path = path or sessions_file()
        self._doc = SessionDocument()
        self.reload()

    # ---------- Persistence ----------

    def reload(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._doc = SessionDocument.model_validate(data)
            except Exception:
                self._doc = SessionDocument()
        else:
            self._doc = SessionDocument()
        self.changed.emit()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            self._doc.model_dump_json(indent=2, exclude_none=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    # ---------- Read API ----------

    @property
    def document(self) -> SessionDocument:
        return self._doc

    @property
    def nodes(self) -> list[Node]:
        return list(self._doc.nodes)

    def get(self, node_id: str) -> Node | None:
        for n in self._doc.nodes:
            if n.id == node_id:
                return n
        return None

    def children(self, parent: str | None) -> list[Node]:
        return sorted(
            (n for n in self._doc.nodes if n.parent == parent),
            key=lambda n: (n.order, n.name.lower()),
        )

    def path_to(self, node_id: str) -> list[Node]:
        """Returns ancestors from root down to the node itself."""
        n = self.get(node_id)
        if n is None:
            return []
        chain = [n]
        while n.parent:
            parent = self.get(n.parent)
            if parent is None:
                break
            chain.append(parent)
            n = parent
        chain.reverse()
        return chain

    # ---------- Mutations ----------

    def add(self, node: Node) -> Node:
        if node.parent and self.get(node.parent) is None:
            raise ValueError(f"Parent {node.parent} not found")
        # Place at end of parent's order.
        siblings = self.children(node.parent)
        node.order = max((s.order for s in siblings), default=-1) + 1
        self._doc.nodes.append(node)
        self.save()
        self.changed.emit()
        return node

    def update(self, node: Node) -> None:
        for i, existing in enumerate(self._doc.nodes):
            if existing.id == node.id:
                self._doc.nodes[i] = node
                self.save()
                self.changed.emit()
                return
        raise KeyError(node.id)

    def delete(self, node_id: str) -> None:
        """Delete a node and all descendants."""
        to_remove = {node_id}
        changed = True
        while changed:
            changed = False
            for n in self._doc.nodes:
                if n.parent in to_remove and n.id not in to_remove:
                    to_remove.add(n.id)
                    changed = True
        self._doc.nodes = [n for n in self._doc.nodes if n.id not in to_remove]
        self.save()
        self.changed.emit()

    def move(self, node_id: str, new_parent: str | None, order: int | None = None) -> None:
        node = self.get(node_id)
        if node is None:
            raise KeyError(node_id)
        # Prevent moving a folder into its own subtree.
        if new_parent is not None:
            ancestor: str | None = new_parent
            while ancestor is not None:
                if ancestor == node_id:
                    raise ValueError("Cannot move a folder into its own subtree")
                parent_node = self.get(ancestor)
                ancestor = parent_node.parent if parent_node else None
        node.parent = new_parent
        if order is None:
            siblings = self.children(new_parent)
            node.order = max((s.order for s in siblings), default=-1) + 1
        else:
            node.order = order
        self.save()
        self.changed.emit()

    def duplicate(self, node_id: str) -> Node | None:
        orig = self.get(node_id)
        if orig is None:
            return None
        copy = orig.model_copy(deep=True)
        copy.id = _new_id()
        copy.name = f"{orig.name} Copy"
        self._doc.nodes.append(copy)
        self.save()
        self.changed.emit()
        return copy

    def replace_all(self, nodes: list[Node]) -> None:
        """Replace entire tree (used by Import)."""
        self._doc = SessionDocument(nodes=list(nodes))
        self.save()
        self.changed.emit()

    def merge(self, nodes: list[Node]) -> None:
        """Append nodes, regenerating IDs to avoid collisions."""
        import copy as _copy

        id_map: dict[str, str] = {}
        for n in nodes:
            new = _copy.deepcopy(n)
            old_id = new.id
            new.id = _new_id()
            id_map[old_id] = new.id
            self._doc.nodes.append(new)
        # Fix parent references within the imported batch.
        for n in self._doc.nodes:
            if n.parent in id_map:
                n.parent = id_map[n.parent]
        self.save()
        self.changed.emit()
