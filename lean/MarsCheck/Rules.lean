import MarsCheck.Spec

/-!
# The rules a validator on Mars is held to

A validator `D` milliseconds from Earth signs an attestation `attDueMs` into slot `i` of an epoch.
The message needs `D` more to reach Earth. These definitions restate the Ethereum consensus
specification's rules with the numbers in `MarsCheck.Spec`; the sources are named on each.

They are the same rules as `src/marscheck/model.py`, written again here so they can be proved about.
They are the author's reading of the specification text, not an extraction from an executable spec.
-/

namespace MarsCheck

/-- `get_slot_component_duration_ms`, `specs/phase0/fork-choice.md`: rounded to the nearest millisecond. -/
def componentMs (bps : Nat) : Nat := (bps * slotDurationMs + 10000 / 2) / 10000

/-- When an attestation is due, after the slot starts (`get_attestation_due_ms`). -/
def attDueMs : Nat := componentMs attestationDueBps

theorem attDueMs_eq : attDueMs = 4000 := by decide

/-- Integer square root, as `integer_squareroot` in the specification. -/
def isqrt (n : Nat) : Nat := (List.range (n + 1)).foldl (fun r k => if k * k ≤ n then k else r) 0

/-- The source vote is timely within `isqrt(SLOTS_PER_EPOCH)` slots (`deneb/beacon-chain.md`). -/
def sourceWindowSlots : Nat := isqrt slotsPerEpoch

/-- The head vote is timely only when included `MIN_ATTESTATION_INCLUSION_DELAY` slots later. -/
def headWindowSlots : Nat := minAttestationInclusionDelay

theorem sourceWindowSlots_eq : sourceWindowSlots = 5 := by decide
theorem headWindowSlots_eq : headWindowSlots = 1 := by decide

/-- Milliseconds after its epoch began at which a validator in slot `i` signs. -/
def sendAt (i : Nat) : Nat := i * slotDurationMs + attDueMs

/-- Milliseconds after that epoch began at which the attestation reaches Earth. -/
def arriveAt (i D : Nat) : Nat := sendAt i + D

/-- An attestation is valid in a block only while its target epoch is the current or the previous one
(`electra/beacon-chain.md`, `process_attestation`). The last slot that can carry it is the last slot of
the next epoch, and the proposer needs the vote by the start of that slot. -/
def lastIncludableSlotStart : Nat := (2 * slotsPerEpoch - 1) * slotDurationMs

def includable (i D : Nat) : Prop := arriveAt i D ≤ lastIncludableSlotStart

/-- `is_matching_source` must hold. The source is the justified checkpoint, which moves at every epoch
boundary while the chain finalizes, so a validator that sees the chain `D` late knows the new epoch's
checkpoints only once `D` has passed since the epoch began. Read generously: Earth's epoch-start block
is taken to be available the instant the epoch begins. -/
def fresh (i D : Nat) : Prop := D ≤ sendAt i

/-- The attestation can count at all. -/
def valid (i D : Nat) : Prop := includable i D ∧ fresh i D

/-- Included in the block of the very next slot or earlier: the head vote's condition. -/
def headTimely (i D : Nat) : Prop := arriveAt i D ≤ (i + headWindowSlots) * slotDurationMs

/-- Included within `isqrt(SLOTS_PER_EPOCH)` slots: the source vote's condition. -/
def sourceTimely (i D : Nat) : Prop := arriveAt i D ≤ (i + sourceWindowSlots) * slotDurationMs

instance (i D : Nat) : Decidable (includable i D) := by unfold includable; infer_instance
instance (i D : Nat) : Decidable (fresh i D) := by unfold fresh; infer_instance
instance (i D : Nat) : Decidable (valid i D) := by unfold valid; infer_instance

end MarsCheck
