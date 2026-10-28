"""Which Ethereum duties can a validator on Mars still perform?

Every number comes from `data/spec_constants.json`, which `tools/extract_spec.py` reads out
of ethereum/consensus-specs. The rules below are the ones that code states, with the
generous reading wherever the specification leaves room, so a "no" here is a firm no.

One-way light time is D seconds. A validator on Mars learns of anything that happens on
Earth D seconds late, and anything it sends needs D seconds to arrive.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from math import isqrt
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"


def load_spec(path: Path | None = None) -> dict:
    return json.loads((path or DATA / "spec_constants.json").read_text())


@dataclass(frozen=True)
class Params:
    slot_s: float
    att_due_s: float
    slots_per_epoch: int
    source_window_slots: int
    head_window_slots: int
    w_source: int
    w_target: int
    w_head: int

    @property
    def epoch_s(self) -> float:
        return self.slot_s * self.slots_per_epoch

    @classmethod
    def from_spec(cls, spec: dict) -> "Params":
        v = {k: x["value"] for k, x in spec["values"].items()}
        slot_ms = v["SLOT_DURATION_MS"]
        # get_slot_component_duration_ms: rounded to the nearest millisecond
        due_ms = (v["ATTESTATION_DUE_BPS"] * slot_ms + 10_000 // 2) // 10_000
        return cls(
            slot_s=slot_ms / 1000,
            att_due_s=due_ms / 1000,
            slots_per_epoch=v["SLOTS_PER_EPOCH"],
            source_window_slots=isqrt(v["SLOTS_PER_EPOCH"]),
            head_window_slots=v["MIN_ATTESTATION_INCLUSION_DELAY"],
            w_source=v["TIMELY_SOURCE_WEIGHT"],
            w_target=v["TIMELY_TARGET_WEIGHT"],
            w_head=v["TIMELY_HEAD_WEIGHT"],
        )


@dataclass(frozen=True)
class Verdict:
    includable: bool   # can the attestation still be put in a block on Earth at all
    fresh_view: bool   # does the Mars validator know the current epoch's checkpoints
    valid: bool
    target: bool
    source: bool
    head: bool

    def reward_share(self, p: Params) -> float:
        got = (p.w_source if self.source else 0) + (p.w_target if self.target else 0) + (
            p.w_head if self.head else 0)
        return got / (p.w_source + p.w_target + p.w_head)


def attest(p: Params, i: int, D: float) -> Verdict:
    """A Mars validator attesting at slot index `i` (0..slots_per_epoch-1) of an epoch.

    It attests `att_due_s` into its slot. The message reaches Earth `D` later.

    includable  -- an attestation is valid in a block only while its target epoch is the
                   current or the previous epoch (electra process_attestation). The last
                   slot that can still carry it is the last slot of the next epoch, and
                   the block proposer must have it by the start of that slot.
    fresh_view  -- `is_matching_source` must hold. The source is the justified checkpoint,
                   which moves at every epoch boundary while the chain finalizes. A Mars
                   validator sees the chain as it was D seconds ago, so it has the new
                   epoch's checkpoints only if D has passed since the epoch began. This
                   is read generously: Earth's epoch-start block is assumed available the
                   instant the epoch begins.
    Flags       -- target needs a valid attestation. Source additionally needs inclusion
                   within isqrt(SLOTS_PER_EPOCH) slots; head within one slot.
    """
    send_at = i * p.slot_s + p.att_due_s
    arrive_at = send_at + D
    last_slot_start = (2 * p.slots_per_epoch - 1) * p.slot_s
    includable = arrive_at <= last_slot_start
    fresh = send_at >= D
    valid = includable and fresh
    in_window = lambda slots: arrive_at <= (i + slots) * p.slot_s  # noqa: E731
    return Verdict(
        includable, fresh, valid,
        target=valid,
        source=valid and in_window(p.source_window_slots),
        head=valid and in_window(p.head_window_slots),
    )


def epoch_summary(p: Params, D: float) -> dict:
    """Over one epoch of slots: share of attestations that count, and of the full reward."""
    vs = [attest(p, i, D) for i in range(p.slots_per_epoch)]
    n = len(vs)
    return {
        "valid_share": sum(v.valid for v in vs) / n,
        "reward_share": sum(v.reward_share(p) for v in vs) / n,
        "head_share": sum(v.head for v in vs) / n,
        "source_share": sum(v.source for v in vs) / n,
    }


def settlement_seconds(p: Params, D: float) -> tuple[float, float]:
    """Seconds from a transaction leaving Mars until Mars can see it finalized.

    It crosses to Earth (D), waits for a block (up to one slot), and finalizes when the next
    epoch's checkpoint does: at the start of the epoch after next, 65 to 96 slots after
    inclusion depending on where in its epoch it landed. Then the news crosses back (D).
    """
    spe = p.slots_per_epoch
    lo = D + (2 * spe + 1) * p.slot_s + D
    hi = D + p.slot_s + 3 * spe * p.slot_s + D
    return lo, hi
