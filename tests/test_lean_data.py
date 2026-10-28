"""The Lean files must be built from the same inputs as the Python model, and say the same numbers."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "lean" / "MarsCheck"


def test_ephemeris_in_lean_is_the_csv():
    text = (LEAN / "Ephemeris.lean").read_text()
    body = text[text.index("def oneWayMs"):]
    lean = [int(x) for x in re.findall(r"\d+", body.split(":=")[1])]
    rows = list(csv.DictReader(open(ROOT / "results" / "daily.csv")))
    assert lean == [round(float(r["one_way_s"]) * 10) * 100 for r in rows]


def test_spec_constants_in_lean_are_the_json():
    spec = json.loads((ROOT / "data" / "spec_constants.json").read_text())["values"]
    text = (LEAN / "Spec.lean").read_text()
    for lean_name, key in [("slotDurationMs", "SLOT_DURATION_MS"), ("attestationDueBps", "ATTESTATION_DUE_BPS"),
                           ("slotsPerEpoch", "SLOTS_PER_EPOCH"), ("timelyTargetWeight", "TIMELY_TARGET_WEIGHT"),
                           ("minAttestationInclusionDelay", "MIN_ATTESTATION_INCLUSION_DELAY")]:
        m = re.search(rf"def {lean_name} : Nat := (\d+)", text)
        assert int(m.group(1)) == spec[key]["value"], key


def test_lean_theorems_state_the_python_results():
    thm = (LEAN / "Theorems.lean").read_text()
    mars = json.loads((ROOT / "results" / "mars_timing.json").read_text())
    th = mars["thresholds_s"]
    assert f"376000 < D" in thm and th["any_valid_vote_possible_below_s"] == 376.0
    assert "D ≤ 8000" in thm and th["head_vote_possible_below_s"] == 8.0
    assert "D ≤ 56000" in thm and th["source_vote_possible_below_s"] == 56.0
    assert "= 119" in thm and mars["days_with_any_valid_mars_attestation"] == 119
    assert "323000 ≤ D" in thm and mars["one_way_light_time_s"]["min"] == 323.0
    assert "130" in thm and abs(mars["best_reward_share_of_full"] - 130 / 1728) < 5e-4
