from pathlib import Path

from specbuild import build

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = (
    "A"
    "<!-- jdf -->KEEPJDF<!-- /jdf -->"
    "<!-- xjdf -->KEEPXJDF<!-- /xjdf -->"
    "<!-- both-only -->KEEPBOTH<!-- /both-only -->"
    "<!-- draft -->KEEPDRAFT<!-- /draft -->"
    "Z"
)


def test_jdf_variant_keeps_only_jdf_and_draft():
    result = build.filter_variants(SAMPLE, "jdf", release=False)
    assert "KEEPJDF" in result
    assert "KEEPXJDF" not in result
    assert "KEEPBOTH" not in result
    assert "KEEPDRAFT" in result
    assert "<!--" not in result


def test_xjdf_release_drops_draft():
    result = build.filter_variants(SAMPLE, "xjdf", release=True)
    assert "KEEPXJDF" in result
    assert "KEEPJDF" not in result
    assert "KEEPBOTH" not in result
    assert "KEEPDRAFT" not in result


def test_both_variant_contains_everything_except_draft_when_released():
    draft = build.filter_variants(SAMPLE, "both", release=False)
    assert all(token in draft for token in ("KEEPJDF", "KEEPXJDF", "KEEPBOTH", "KEEPDRAFT"))
    release = build.filter_variants(SAMPLE, "both", release=True)
    assert "KEEPDRAFT" not in release


def test_build_writes_html_for_each_variant(tmp_path):
    for variant in ("both", "jdf", "xjdf"):
        target = build.build(ROOT, variant, release=False, out=str(tmp_path / variant))
        assert target.exists()
        assert "Icon" in target.read_text(encoding="utf-8")
