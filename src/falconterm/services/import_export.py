"""Export / import session tree + color schemes as a portable .ftsessions bundle.

Passwords are deliberately NOT exported. On import we record which sessions
referenced keyring entries but leave the ref strings in place — the user will
be prompted on next connect.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from falconterm.models.session import Node, SessionDocument
from falconterm.models.settings import ColorScheme
from falconterm.utils.constants import CONFIG_VERSION


class Bundle(BaseModel):
    version: int = CONFIG_VERSION
    kind: Literal["falconterm-bundle"] = "falconterm-bundle"
    nodes: list[Node] = Field(default_factory=list)
    color_schemes: list[ColorScheme] = Field(default_factory=list)


def export_bundle(
    document: SessionDocument,
    color_schemes: list[ColorScheme],
    path: Path,
) -> None:
    bundle = Bundle(nodes=list(document.nodes), color_schemes=list(color_schemes))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")


def load_bundle(path: Path) -> Bundle:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Bundle.model_validate(data)
