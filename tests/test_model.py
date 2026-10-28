"""The model's claims, each checked against the specification's own numbers."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marscheck import model, orbit  # noqa: E402

SPEC = model.load_spec()
P = model.Params.from_spec(SPEC)


def test_parameters_come_from_the_spec():
    assert P.slot_s == 12.0
    assert P.att_due_s == 4.0          # (3333 * 12000 + 5000) // 10000 ms
    assert P.slots_per_epoch == 32
    assert P.source_window_slots == 5  # isqrt(32)
    assert P.head_window_slots == 1
    assert (P.w_source, P.w_target, P.w_head) == (14, 26, 14)
    assert P.epoch_s == 384.0


def test_rules_still_match_the_code_they_cite():
    # extract_spec.py refuses to run unless these exact lines exist in the spec
    for name in ("source_timely", "head_timely", "source_must_match", "inclusion_window",
                 "min_inclusion_delay", "leak_trigger"):
        assert SPEC["rules"][name]["code"]


def test_validator_beside_earth_gets_everything():
    for i in range(P.slots_per_epoch):
        v = model.attest(P, i, 0.5)  # half a second away
        assert v.valid and v.target and v.source and v.head
        assert v.reward_share(P) == 1.0


def test_head_vote_needs_the_message_in_the_next_slot():
    assert model.attest(P, 5, 7.9).head
    assert not model.attest(P, 5, 8.1).head


def test_source_vote_window_is_five_slots():
    assert model.attest(P, 5, 55.9).source
    assert not model.attest(P, 5, 56.1).source


def test_no_valid_attestation_once_the_delay_exceeds_the_last_slot_of_the_epoch():
    last = (P.slots_per_epoch - 1) * P.slot_s + P.att_due_s  # 376 s
    assert model.attest(P, 31, last - 0.1).valid
    assert not model.attest(P, 31, last + 0.1).valid
    for i in range(P.slots_per_epoch):
        assert not model.attest(P, i, 377).valid


def test_the_inclusion_window_closes_at_the_end_of_the_next_epoch():
    # slot 0 of an epoch has the longest window: 63 slots minus the 4 s attestation delay
    edge = 63 * P.slot_s - P.att_due_s
    assert model.attest(P, 0, edge).includable
    assert not model.attest(P, 0, edge + 0.1).includable


def test_reward_share_is_monotone_in_distance():
    shares = [model.epoch_summary(P, d)["reward_share"] for d in range(0, 500, 10)]
    assert all(a >= b for a, b in zip(shares, shares[1:]))


def test_target_alone_is_just_under_half_of_the_reward():
    assert model.Verdict(True, True, True, True, False, False).reward_share(P) == pytest.approx(26 / 54)


def test_settlement_includes_both_crossings_and_two_epochs():
    lo, hi = model.settlement_seconds(P, 100.0)
    assert lo == 100 + 65 * 12 + 100
    assert hi == 100 + 12 + 96 * 12 + 100
    assert lo < hi


def test_ephemeris_matches_known_geometry():
    days = orbit.load(next((ROOT / "data").glob("horizons_mars_*.txt")))
    assert len(days) == 1527
    assert days[0].date.isoformat() == "2026-10-27"
    # Mars is never closer than ~0.37 AU (3 min) nor farther than ~2.7 AU (22.5 min)
    assert all(150 < d.one_way_s < 1400 for d in days)
    # light takes 499.0 s per AU
    assert orbit.AU_LIGHT_SECONDS == pytest.approx(499.0048, abs=1e-4)
    # opposition elongation approaches 180 degrees, conjunction approaches 0
    assert max(d.elongation_deg for d in days) > 170
    assert min(d.elongation_deg for d in days) < 1


def test_every_day_has_no_head_or_source_vote():
    import csv
    rows = list(csv.DictReader(open(ROOT / "results" / "daily.csv")))
    assert all(float(r["head_share"]) == 0 and float(r["source_share"]) == 0 for r in rows)
    assert min(float(r["one_way_s"]) for r in rows) > 56  # nearest Mars gets is far past the cutoffs
