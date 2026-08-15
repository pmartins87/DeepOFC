import json
from pathlib import Path

from tools.export_fantasy_recognizer_cpp import export_header


ROOT = Path(__file__).resolve().parents[1]
FAN = ROOT / "tablemaps" / "joker_ultimate_hu_fantasy15_rank_medoid_bank_v1.json"
UPRIGHT = ROOT / "tablemaps" / "joker_ultimate_hu_upright_rank_bank_v1.json"


def test_cpp_export_contains_exact_three_rank_alphabets_and_runtime_authority_off():
    fan = json.loads(FAN.read_text(encoding="utf-8"))
    upright = json.loads(UPRIGHT.read_text(encoding="utf-8"))
    header = export_header(fan, upright)

    assert "kDeepOFCRecognizerBanksRuntimeAuthorized = false" in header
    assert "kDeepOFCFantasy15FanRankTemplates[13]" in header
    assert "kDeepOFCUprightLargeRankTemplates[13]" in header
    assert "kDeepOFCUprightSmallRankTemplates[13]" in header
    assert "kDeepOFCSuitPrototypes[4]" in header
    assert "#include \"COFCFantasyRecognitionCore.h\"" in header

    # Each array has one entry per ordinary rank; data is generated from the
    # versioned JSON masks rather than copied by hand into OpenHoldem.
    for symbol in (
        "kDeepOFCFantasy15FanRankTemplates",
        "kDeepOFCUprightLargeRankTemplates",
        "kDeepOFCUprightSmallRankTemplates",
    ):
        start = header.index(f"{symbol}[13]")
        end = header.index("};", start)
        block = header[start:end]
        for rank in "23456789TJQKA":
            assert f"{{'{rank}', {{" in block


def test_cpp_export_is_deterministic():
    fan = json.loads(FAN.read_text(encoding="utf-8"))
    upright = json.loads(UPRIGHT.read_text(encoding="utf-8"))
    assert export_header(fan, upright) == export_header(fan, upright)
