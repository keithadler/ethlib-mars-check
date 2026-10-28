#!/usr/bin/env python3
"""Read the numbers and rules this project depends on out of ethereum/consensus-specs.

Nothing is typed in by hand. Each value is found in a named file of a clone of the
specification, with its line number, and the rules are checked against the exact
lines of code they come from. If the specification changes under us, this fails
instead of quietly using an old number.

    python tools/extract_spec.py /path/to/consensus-specs > data/spec_constants.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def find(root: Path, rel: str, pattern: str):
    """First line of `rel` matching `pattern`; returns (line number, match)."""
    text = (root / rel).read_text().splitlines()
    rx = re.compile(pattern)
    for i, line in enumerate(text, 1):
        m = rx.search(line)
        if m:
            return i, m
    raise SystemExit(f"not found in {rel}: {pattern}")


def main(root: Path) -> dict:
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    out = {"consensus_specs_commit": sha, "values": {}, "rules": {}}

    def val(name, rel, pattern, cast=int):
        line, m = find(root, rel, pattern)
        out["values"][name] = {"value": cast(m.group(1)), "source": f"{rel}:{line}"}

    cfg = "configs/mainnet.yaml"
    val("SLOT_DURATION_MS", cfg, r"^SLOT_DURATION_MS:\s*(\d+)")
    val("ATTESTATION_DUE_BPS", cfg, r"^ATTESTATION_DUE_BPS:\s*(\d+)")
    val("AGGREGATE_DUE_BPS", cfg, r"^AGGREGATE_DUE_BPS:\s*(\d+)")
    val("INACTIVITY_SCORE_BIAS", cfg, r"^INACTIVITY_SCORE_BIAS:\s*(\d+)")
    val("EJECTION_BALANCE", cfg, r"^EJECTION_BALANCE:\s*(\d+)")
    val("SAMPLES_PER_SLOT", cfg, r"^SAMPLES_PER_SLOT:\s*(\d+)")
    val("CUSTODY_REQUIREMENT", cfg, r"^CUSTODY_REQUIREMENT:\s*(\d+)")
    val("NUMBER_OF_CUSTODY_GROUPS", cfg, r"^NUMBER_OF_CUSTODY_GROUPS:\s*(\d+)")
    val("MAXIMUM_GOSSIP_CLOCK_DISPARITY", cfg, r"^MAXIMUM_GOSSIP_CLOCK_DISPARITY:\s*(\d+)")

    # The newest entry of BLOB_SCHEDULE is the blob limit in force.
    text = (root / cfg).read_text().splitlines()
    start = next(i for i, l in enumerate(text) if l.startswith("BLOB_SCHEDULE:"))
    last = None
    for i in range(start + 1, len(text)):
        m = re.match(r"\s+MAX_BLOBS_PER_BLOCK:\s*(\d+)", text[i])
        if m:
            last = (i + 1, int(m.group(1)))
        elif text[i] and not text[i].startswith((" ", "-", "#")):
            break
    out["values"]["MAX_BLOBS_PER_BLOCK_LATEST"] = {"value": last[1], "source": f"{cfg}:{last[0]}"}

    val("SLOTS_PER_EPOCH", "presets/mainnet/phase0.yaml", r"^SLOTS_PER_EPOCH:\s*(\d+)")
    val("MIN_ATTESTATION_INCLUSION_DELAY", "presets/mainnet/phase0.yaml",
        r"^MIN_ATTESTATION_INCLUSION_DELAY:\s*(\d+)")
    val("EPOCHS_PER_SYNC_COMMITTEE_PERIOD", "presets/mainnet/altair.yaml",
        r"^EPOCHS_PER_SYNC_COMMITTEE_PERIOD:\s*(\d+)")
    val("INACTIVITY_PENALTY_QUOTIENT_BELLATRIX", "presets/mainnet/bellatrix.yaml",
        r"^INACTIVITY_PENALTY_QUOTIENT_BELLATRIX:\s*(\d+)")
    val("FIELD_ELEMENTS_PER_BLOB", "presets/mainnet/deneb.yaml", r"^FIELD_ELEMENTS_PER_BLOB:\s*(\d+)")
    val("NUMBER_OF_COLUMNS", "presets/mainnet/fulu.yaml", r"^NUMBER_OF_COLUMNS:\s*(\d+)")
    val("MAX_EFFECTIVE_BALANCE", "presets/mainnet/phase0.yaml", r"^MAX_EFFECTIVE_BALANCE:\s*(\d+)")

    alt = "specs/altair/beacon-chain.md"
    val("TIMELY_SOURCE_WEIGHT", alt, r"`TIMELY_SOURCE_WEIGHT`\s*\|\s*`Uint64\((\d+)\)`")
    val("TIMELY_TARGET_WEIGHT", alt, r"`TIMELY_TARGET_WEIGHT`\s*\|\s*`Uint64\((\d+)\)`")
    val("TIMELY_HEAD_WEIGHT", alt, r"`TIMELY_HEAD_WEIGHT`\s*\|\s*`Uint64\((\d+)\)`")
    val("WEIGHT_DENOMINATOR", alt, r"`WEIGHT_DENOMINATOR`\s*\|\s*`Uint64\((\d+)\)`")
    val("MIN_EPOCHS_TO_INACTIVITY_PENALTY", "specs/phase0/beacon-chain.md",
        r"`MIN_EPOCHS_TO_INACTIVITY_PENALTY`\s*\|\s*`Epoch\(2\*\*(\d+)\)`",
        cast=lambda s: 2 ** int(s))

    # The rules, each checked against the code it is read from.
    def rule(name, rel, snippet):
        line, _ = find(root, rel, re.escape(snippet))
        out["rules"][name] = {"source": f"{rel}:{line}", "code": snippet}

    den = "specs/deneb/beacon-chain.md"
    rule("source_timely", den, "inclusion_delay <= integer_squareroot(SLOTS_PER_EPOCH)")
    rule("head_timely", den, "inclusion_delay == MIN_ATTESTATION_INCLUSION_DELAY")
    rule("source_must_match", den, "assert is_matching_source")
    rule("source_is_current_or_previous_justified", den, "justified_checkpoint = state.previous_justified_checkpoint")
    ele = "specs/electra/beacon-chain.md"
    rule("inclusion_window", ele, "assert data.target.epoch in (get_previous_epoch(state), get_current_epoch(state))")
    rule("min_inclusion_delay", ele, "assert data.slot + MIN_ATTESTATION_INCLUSION_DELAY <= state.slot")
    rule("leak_trigger", "specs/phase0/beacon-chain.md",
         "return get_finality_delay(state) > MIN_EPOCHS_TO_INACTIVITY_PENALTY")
    rule("inactivity_score_bias", "specs/altair/beacon-chain.md", "state.inactivity_scores[index] += INACTIVITY_SCORE_BIAS")
    rule("attestation_due", "specs/phase0/fork-choice.md", "return get_slot_component_duration_ms(ATTESTATION_DUE_BPS)")
    return out


if __name__ == "__main__":
    json.dump(main(Path(sys.argv[1])), sys.stdout, indent=2)
    print()
