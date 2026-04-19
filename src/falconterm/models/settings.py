"""Global default settings and color-scheme models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from falconterm.utils.constants import (
    DEFAULT_COLS,
    DEFAULT_ENCODING,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_ROWS,
    DEFAULT_SCROLLBACK,
)


class FontSpec(BaseModel):
    family: str = DEFAULT_FONT_FAMILY
    size: int = DEFAULT_FONT_SIZE


class ColorScheme(BaseModel):
    id: str
    name: str = ""
    fg: str = "#d8d8d8"  # hex RRGGBB
    bg: str = "#1e1e22"
    cursor: str = "#50c878"
    # 16 ANSI colors, black, red, green, yellow, blue, magenta, cyan, white,
    # plus their bright variants.
    ansi: list[str] = Field(
        default_factory=lambda: [
            "#000000",
            "#c00000",
            "#00c000",
            "#c0c000",
            "#0000c0",
            "#c000c0",
            "#00c0c0",
            "#c0c0c0",
            "#555555",
            "#ff5555",
            "#55ff55",
            "#ffff55",
            "#5555ff",
            "#ff55ff",
            "#55ffff",
            "#ffffff",
        ]
    )


# Pre-baked schemes — always present.
BUILTIN_SCHEMES: list[ColorScheme] = [
    ColorScheme(
        id="default",
        name="Default Dark",
        fg="#d8d8d8",
        bg="#1e1e22",
        cursor="#50c878",
    ),
    ColorScheme(
        id="solarized-dark",
        name="Solarized Dark",
        fg="#93a1a1",
        bg="#002b36",
        cursor="#93a1a1",
        ansi=[
            "#073642",
            "#dc322f",
            "#859900",
            "#b58900",
            "#268bd2",
            "#d33682",
            "#2aa198",
            "#eee8d5",
            "#586e75",
            "#cb4b16",
            "#586e75",
            "#657b83",
            "#839496",
            "#6c71c4",
            "#93a1a1",
            "#fdf6e3",
        ],
    ),
    ColorScheme(
        id="solarized-light",
        name="Solarized Light",
        fg="#657b83",
        bg="#fdf6e3",
        cursor="#657b83",
        ansi=[
            "#073642",
            "#dc322f",
            "#859900",
            "#b58900",
            "#268bd2",
            "#d33682",
            "#2aa198",
            "#eee8d5",
            "#586e75",
            "#cb4b16",
            "#586e75",
            "#657b83",
            "#839496",
            "#6c71c4",
            "#93a1a1",
            "#fdf6e3",
        ],
    ),
    ColorScheme(
        id="monokai",
        name="Monokai",
        fg="#f8f8f2",
        bg="#272822",
        cursor="#f8f8f0",
        ansi=[
            "#272822",
            "#f92672",
            "#a6e22e",
            "#f4bf75",
            "#66d9ef",
            "#ae81ff",
            "#a1efe4",
            "#f8f8f2",
            "#75715e",
            "#f92672",
            "#a6e22e",
            "#f4bf75",
            "#66d9ef",
            "#ae81ff",
            "#a1efe4",
            "#f9f8f5",
        ],
    ),
]

BUILTIN_SCHEME_IDS = {s.id for s in BUILTIN_SCHEMES}


class GlobalDefaults(BaseModel):
    """Global session defaults inherited by newly-created sessions."""

    font: FontSpec = Field(default_factory=FontSpec)
    color_scheme_id: str = "default"
    rows: int = DEFAULT_ROWS
    cols: int = DEFAULT_COLS
    auto_fit_to_window: bool = True
    encoding: str = DEFAULT_ENCODING
    scrollback: int = DEFAULT_SCROLLBACK
    logging: bool = False
    log_retention_days: int = 90


class UIState(BaseModel):
    """Persisted non-session preferences (window geometry, etc.)."""

    sidebar_width: int = 240
    window_width: int = 1100
    window_height: int = 700


class AppSettings(BaseModel):
    """Root app settings, serialized to settings.json."""

    version: int = 1
    defaults: GlobalDefaults = Field(default_factory=GlobalDefaults)
    color_schemes: list[ColorScheme] = Field(default_factory=lambda: list(BUILTIN_SCHEMES))
    ui: UIState = Field(default_factory=UIState)

    def scheme(self, scheme_id: str) -> ColorScheme:
        for s in self.color_schemes:
            if s.id == scheme_id:
                return s
        # Fallback
        for s in BUILTIN_SCHEMES:
            if s.id == scheme_id:
                return s
        return BUILTIN_SCHEMES[0]


Protocol = Literal["ssh", "telnet", "serial"]
