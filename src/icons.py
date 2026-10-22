"""Custom map marker icons for the flora & fauna overlay.

Icons live in ``assets/icons/`` and are matched to a taxon key by file name::

    assets/icons/orangutan.svg
    assets/icons/proboscis-monkey.png
    assets/icons/rafflesia.svg
    assets/icons/nepenthes.svg
    assets/icons/default.svg      # fallback for any other taxon

Any of ``.png .webp .jpg .jpeg .svg`` is accepted (first match in that order),
so a custom image can be dropped in without touching the code. Files are
embedded as data URIs, which keeps the Folium map self-contained in the
browser and avoids Streamlit static-file routing.

The module has no Streamlit dependency and imports Folium lazily so the
non-Streamlit fallback path still works if Folium is not installed.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

# ``<repo>/assets/icons`` — src/ lives directly under the repo root.
ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

# Lower-case extensions in order of preference.
_EXTENSIONS = (".png", ".webp", ".jpg", ".jpeg", ".svg")


def icon_folder() -> Path:
    """Return the directory users can drop custom icons into."""
    return ICON_DIR


def _normalise(name: str) -> str:
    """``Proboscis_monkey`` / ``proboscis-monkey`` -> ``proboscismonkey``."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


@lru_cache(maxsize=8)
def _registry(dir_mtime: float) -> Dict[str, str]:
    """Map normalised icon stem -> path, rebuilt when the folder changes."""
    table: Dict[str, str] = {}
    try:
        entries = sorted(os.listdir(ICON_DIR))
    except OSError:
        return table
    for filename in entries:
        stem, ext = os.path.splitext(filename)
        if ext.lower() not in _EXTENSIONS:
            continue
        key = _normalise(stem)
        candidate = ICON_DIR / filename
        # Keep the highest-priority extension (earlier in _EXTENSIONS wins).
        current = table.get(key)
        if current is None or _EXTENSIONS.index(ext.lower()) < _EXTENSIONS.index(
            os.path.splitext(current)[1].lower()
        ):
            table[key] = str(candidate)
    return table


def icon_registry() -> Dict[str, str]:
    """Return the current icon table (refreshes when files change)."""
    try:
        mtime = ICON_DIR.stat().st_mtime
    except OSError:
        return {}
    return _registry(mtime)


def icon_path_for(taxon_key: str) -> Optional[str]:
    """Return the icon path for *taxon_key*, falling back to ``default.*``."""
    table = icon_registry()
    return table.get(_normalise(taxon_key)) or table.get("default")


@lru_cache(maxsize=64)
def _icon_data_url(path: str, mtime: float) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def icon_data_url(taxon_key: str) -> Optional[str]:
    """Return a data URI for *taxon_key*'s icon, or None if unavailable."""
    path = icon_path_for(taxon_key)
    if not path:
        return None
    try:
        mtime = os.path.getmtime(path)
        return _icon_data_url(path, mtime)
    except OSError:
        return None


def bio_icon(taxon_key: str, size: int = 28) -> Optional[object]:
    """Build a Folium ``CustomIcon`` for *taxon_key*.

    Returns ``None`` when Folium is unavailable or no icon file exists, so the
    caller can fall back to a plain geometric marker.
    """
    url = icon_data_url(taxon_key)
    if not url:
        return None
    try:
        import folium
    except Exception:
        return None
    return folium.CustomIcon(
        url,
        icon_size=(size, size),
        icon_anchor=(size // 2, size // 2),
        popup_anchor=(0, -size // 2),
    )
