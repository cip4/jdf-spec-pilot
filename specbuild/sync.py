"""Keep the generated Markdown blocks in sync with the YAML model."""

from __future__ import annotations

import re
from pathlib import Path

from .model import find_model
from .render import block, render

BLOCK_RE = re.compile(
    r"<!-- BEGIN GENERATED model:(?P<name>[A-Za-z0-9_./-]+)[^\n]*-->"
    r".*?"
    r"<!-- END GENERATED[^\n]*-->",
    re.DOTALL,
)


def _spec_files(root: Path):
    return sorted((root / "spec").rglob("*.md"))


def render_all(root: Path) -> dict[Path, str]:
    """Return the expected contents of every spec file, with blocks regenerated."""
    expected: dict[Path, str] = {}
    for path in _spec_files(root):
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match) -> str:
            name = match.group("name")
            return block(name, render(find_model(root, name)))

        expected[path] = BLOCK_RE.sub(replace, text)
    return expected


def sync(root: Path) -> list[Path]:
    """Rewrite any spec file whose generated blocks are out of date."""
    changed: list[Path] = []
    for path, expected in render_all(root).items():
        current = path.read_text(encoding="utf-8")
        if expected != current:
            path.write_text(expected, encoding="utf-8")
            changed.append(path)
    return changed


def check(root: Path) -> list[str]:
    """Report spec files whose generated blocks differ from the model."""
    errors: list[str] = []
    for path, expected in render_all(root).items():
        if expected != path.read_text(encoding="utf-8"):
            errors.append(
                f"{path.relative_to(root)}: generated block is out of date "
                "(run 'specbuild sync')"
            )
    return errors
