"""Build an HTML rendering of the specification for one variant.

This is the first step of the build pipeline. PDF output (WeasyPrint or Typst)
and XSD/JSON Schema generation plug in here later.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown
import yaml

VARIANT_RULES = {
    "jdf": {"keep": {"jdf"}, "drop": {"xjdf", "both-only"}},
    "xjdf": {"keep": {"xjdf"}, "drop": {"jdf", "both-only"}},
    "both": {"keep": {"jdf", "xjdf", "both-only"}, "drop": set()},
}

_VARIANT_MARKERS = ("jdf", "xjdf", "both-only", "draft")

CSS = """
body { font-family: system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #ccc; padding: 0.3rem 0.5rem; text-align: left; vertical-align: top; }
code { background: #f3f3f3; padding: 0 0.2rem; }
"""


def filter_variants(text: str, variant: str, release: bool) -> str:
    """Strip conditional prose markers for the requested variant."""
    rule = VARIANT_RULES[variant]
    for kind in rule["drop"]:
        text = re.sub(
            rf"<!--\s*{kind}\s*-->.*?<!--\s*/{kind}\s*-->",
            "",
            text,
            flags=re.DOTALL,
        )
    keep = set(rule["keep"])
    if not release:
        keep.add("draft")
    for kind in _VARIANT_MARKERS:
        if kind in keep:
            text = re.sub(rf"<!--\s*/?{kind}\s*-->", "", text)
        else:
            text = re.sub(
                rf"<!--\s*{kind}\s*-->.*?<!--\s*/{kind}\s*-->",
                "",
                text,
                flags=re.DOTALL,
            )
    return text


def _chapters(root: Path) -> list[Path]:
    config = yaml.safe_load((root / "spec" / "book.yaml").read_text(encoding="utf-8"))
    files: list[Path] = []
    for chapter in config.get("chapters", []):
        base = root / chapter["dir"]
        files.extend(base / name for name in chapter.get("files", []))
    return files


def build(root: Path, variant: str, release: bool, out: str) -> Path:
    out_dir = Path(out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    articles: list[str] = []
    for path in _chapters(root):
        text = filter_variants(path.read_text(encoding="utf-8"), variant, release)
        body = markdown.markdown(
            text, extensions=["tables", "fenced_code", "toc"]
        )
        articles.append(f"<article>\n{body}\n</article>")

    title = f"JDF/XJDF Specification ({variant})"
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{title}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        + "\n".join(articles)
        + "\n</body>\n</html>\n"
    )
    target = out_dir / "index.html"
    target.write_text(page, encoding="utf-8")
    return target
