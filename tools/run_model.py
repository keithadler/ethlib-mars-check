#!/usr/bin/env python3
"""Run the Mars timing model over every day of the ephemeris and write results/."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marscheck import model, orbit  # noqa: E402

SPEC = model.load_spec()
P = model.Params.from_spec(SPEC)
V = {k: x["value"] for k, x in SPEC["values"].items()}
DAYS = orbit.load(next((ROOT / "data").glob("horizons_mars_*.txt")))

# Link capacity assumption. NASA's description of the Mars Reconnaissance Orbiter's
# direct-to-Earth link: 0.5 to 4 megabits per second depending on distance, with data
# sent 10 to 11 of every 24 hours (https://webarchive.library.unt.edu/web/20130308105753/
# http://mars.jpl.nasa.gov/mro/mission/communications). One orbiter, not a network.
LINK_MIN_MBPS, LINK_MAX_MBPS = 0.5, 4.0
LINK_HOURS_PER_DAY = 10.5

rows = []
for d in DAYS:
    D = d.one_way_s
    e = model.epoch_summary(P, D)
    lo, hi = model.settlement_seconds(P, D)
    rows.append({
        "date": d.date.isoformat(), "one_way_s": round(D, 1), "elongation_deg": round(d.elongation_deg, 2),
        "blackout": d.blackout, "valid_share": round(e["valid_share"], 4),
        "reward_share": round(e["reward_share"], 4), "head_share": e["head_share"],
        "source_share": e["source_share"], "settle_min_s": round(lo), "settle_max_s": round(hi),
    })

with open(ROOT / "results" / "daily.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

Ds = [r["one_way_s"] for r in rows]
dmin, dmax = min(Ds), max(Ds)
imin, imax = Ds.index(dmin), Ds.index(dmax)

# Thresholds, read straight off the rules.
slot, due, epoch = P.slot_s, P.att_due_s, P.epoch_s
last_i = P.slots_per_epoch - 1
thresholds = {
    "head_vote_possible_below_s": slot - due,                            # next slot's proposer
    "source_vote_possible_below_s": P.source_window_slots * slot - due,  # isqrt(32) slots
    "any_valid_vote_possible_below_s": last_i * slot + due,             # fresh view at the last slot
    "epoch_s": epoch,
}
valid_days = sum(r["valid_share"] > 0 for r in rows)
reward_peak = max(r["reward_share"] for r in rows)

# Inactivity leak: how long until a validator that never counts is ejected.
bal, score, epochs = float(V["MAX_EFFECTIVE_BALANCE"]), 0, 0
while bal > V["EJECTION_BALANCE"]:
    score += V["INACTIVITY_SCORE_BIAS"]
    bal -= bal * score / (V["INACTIVITY_SCORE_BIAS"] * V["INACTIVITY_PENALTY_QUOTIENT_BELLATRIX"])
    epochs += 1
leak_epochs = epochs
leak_days = epochs * epoch / 86400

# Blob data a node must receive once per slot (any 64 of 128 columns rebuild the rest).
blob_bytes = V["FIELD_ELEMENTS_PER_BLOB"] * 32
per_slot_bits = V["MAX_BLOBS_PER_BLOCK_LATEST"] * blob_bytes * 8
need_mbps = per_slot_bits / slot / 1e6
duty = LINK_HOURS_PER_DAY / 24
avg_best, avg_worst = LINK_MAX_MBPS * duty, LINK_MIN_MBPS * duty
blobs_best = avg_best * 1e6 * slot / (blob_bytes * 8)
blobs_worst = avg_worst * 1e6 * slot / (blob_bytes * 8)

best, worst = rows[imin], rows[imax]
summary = {
    "inputs": {"consensus_specs_commit": SPEC["consensus_specs_commit"], "days": len(rows),
               "first_day": rows[0]["date"], "last_day": rows[-1]["date"]},
    "one_way_light_time_s": {"min": dmin, "max": dmax, "min_date": best["date"], "max_date": worst["date"]},
    "blackout_days": sum(r["blackout"] for r in rows),
    "thresholds_s": thresholds,
    "days_with_any_valid_mars_attestation": valid_days,
    "share_of_days_with_any_valid_mars_attestation": valid_days / len(rows),
    "best_valid_share": max(r["valid_share"] for r in rows),
    "best_reward_share_of_full": reward_peak,
    "head_or_source_votes_ever": any(r["head_share"] or r["source_share"] for r in rows),
    "settlement_see_finality_s": {
        "fastest": min(r["settle_min_s"] for r in rows), "slowest": max(r["settle_max_s"] for r in rows)},
    "leak": {"epochs_to_ejection": leak_epochs, "days_to_ejection": round(leak_days, 1),
             "applies_only_if": "validators that do not count hold more than 1/3 of the stake, so the chain stops finalizing"},
    "das": {"samples_per_slot": V["SAMPLES_PER_SLOT"], "sample_round_trip_s_best": 2 * dmin,
            "attestation_due_s": due},
    "bandwidth": {"blob_data_needed_mbps_at_max_blobs": round(need_mbps, 3),
                  "max_blobs_per_block": V["MAX_BLOBS_PER_BLOCK_LATEST"],
                  "link_average_mbps_best": round(avg_best, 3), "link_average_mbps_worst": round(avg_worst, 3),
                  "blobs_per_block_link_carries_best": round(blobs_best, 1),
                  "blobs_per_block_link_carries_worst": round(blobs_worst, 1)},
    "light_client": {"sync_committee_period_hours": V["EPOCHS_PER_SYNC_COMMITTEE_PERIOD"] * epoch / 3600,
                     "max_one_way_delay_hours": dmax / 3600},
}
(ROOT / "results" / "mars_timing.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
