from pathlib import Path

from specbuild import xsd_emit, xsd_import

ROOT = Path(__file__).resolve().parents[1]
XJDF = ROOT / "import" / "xsd" / "xjdf" / "xjdf.xsd"


def _imported():
    return xsd_import.import_all(XJDF)


def test_counts():
    modelset = _imported()
    assert len(modelset["elements"]) == 370
    assert len(modelset["enums"]) == 45
    assert modelset["elements"]["Icon"]["attributes"] == [
        {"name": "BitDepth", "type": "integer", "required": True},
        {
            "name": "IconUsage",
            "type": "enumerations",
            "values": {"from": "DeviceStatus", "multiple": True},
        },
        {"name": "Size", "type": "XYPair", "required": True},
    ]
    assert {"name": "FileSpec", "cardinality": "?"} in modelset["elements"]["Icon"]["elements"]


def test_substitution_groups_and_abstract():
    modelset = _imported()
    assert modelset["elements"]["SpecificResource"]["abstract"] is True
    assert modelset["elements"]["CustomerInfo"]["substitutes"] == "SpecificResource"


def test_roundtrip_is_lossless_at_model_level(tmp_path):
    first, second, differences, generated = xsd_emit.roundtrip(XJDF, tmp_path)
    assert generated.exists()
    assert differences == []
    assert xsd_emit.canonical(first) == xsd_emit.canonical(second)
