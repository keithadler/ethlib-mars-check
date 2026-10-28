import MarsCheck.Rules
import MarsCheck.Ephemeris

namespace MarsCheck

/-- Plain numbers for `omega`. -/
theorem numbers : slotDurationMs = 12000 ∧ slotsPerEpoch = 32 ∧ attDueMs = 4000 ∧
    sourceWindowSlots = 5 ∧ headWindowSlots = 1 :=
  ⟨by decide, by decide, attDueMs_eq, sourceWindowSlots_eq, headWindowSlots_eq⟩

/-- No vote counts once the one-way delay passes 376 seconds, from any slot of the epoch. -/
theorem no_valid_vote_past_376s (i D : Nat) (hi : i < slotsPerEpoch) (hD : 376000 < D) :
    ¬ valid i D := by
  obtain ⟨h1, h2, h3, -, -⟩ := numbers
  rintro ⟨-, hf⟩
  unfold fresh sendAt at hf
  rw [h1, h3] at hf
  rw [h2] at hi
  omega

/-- The threshold is exact: at 376 seconds, the last slot of the epoch still has a valid vote. -/
theorem valid_vote_at_376s : valid 31 376000 := by decide

/-- A head vote must reach Earth within 8 seconds of being sent. -/
theorem head_vote_needs_8s (i D : Nat) (h : headTimely i D) : D ≤ 8000 := by
  obtain ⟨h1, -, h3, -, h5⟩ := numbers
  unfold headTimely arriveAt sendAt at h
  rw [h1, h3, h5] at h
  omega

/-- A source vote must reach Earth within 56 seconds of being sent. -/
theorem source_vote_needs_56s (i D : Nat) (h : sourceTimely i D) : D ≤ 56000 := by
  obtain ⟨h1, -, h3, h4, -⟩ := numbers
  unfold sourceTimely arriveAt sendAt at h
  rw [h1, h3, h4] at h
  omega


/-- Some slot of the epoch has a valid vote exactly when the delay is at most 376 seconds. -/
theorem exists_valid_iff (D : Nat) : (∃ i, i < slotsPerEpoch ∧ valid i D) ↔ D ≤ 376000 := by
  constructor
  · rintro ⟨i, hi, hv⟩
    by_cases h : D ≤ 376000
    · exact h
    · exact absurd hv (no_valid_vote_past_376s i D hi (by omega))
  · intro h
    obtain ⟨h1, h2, h3, -, -⟩ := numbers
    refine ⟨31, by rw [h2]; omega, ?_, ?_⟩
    · unfold includable arriveAt sendAt lastIncludableSlotStart
      rw [h1, h2, h3]; omega
    · unfold fresh sendAt
      rw [h1, h3]; omega

/-- The ephemeris has 1,527 days. -/
theorem ephemeris_days : oneWayMs.length = 1527 := by decide +kernel

/-- Mars is never closer than 323 seconds in this window. -/
theorem every_day_at_least_323s : ∀ D ∈ oneWayMs, 323000 ≤ D := by decide +kernel

/-- So on no day does a Mars validator get a head vote or a source vote. -/
theorem never_head_or_source_vote : ∀ D ∈ oneWayMs, ∀ i, ¬ headTimely i D ∧ ¬ sourceTimely i D := by
  intro D hD i
  have h := every_day_at_least_323s D hD
  exact ⟨fun hh => by have := head_vote_needs_8s i D hh; omega,
         fun hs => by have := source_vote_needs_56s i D hs; omega⟩

/-- On 119 of the 1,527 days a Mars validator can have any vote count at all. -/
theorem days_with_a_valid_vote : oneWayMs.countP (fun D => decide (D ≤ 376000)) = 119 := by decide +kernel

/-- Number of slots of an epoch in which a vote can count, at delay `D`. -/
def validSlots (D : Nat) : Nat := (List.range slotsPerEpoch).countP (fun i => decide (valid i D))

/-- At 323 seconds or more, at most 5 of the epoch's 32 slots have a vote that can count. -/
theorem at_most_5_valid_slots (D : Nat) (hD : 323000 ≤ D) : validSlots D ≤ 5 := by
  have key : ∀ i ∈ List.range slotsPerEpoch, decide (valid i D) = true → decide (27 ≤ i) = true := by
    intro i hi hv
    have hv' : valid i D := of_decide_eq_true hv
    obtain ⟨h1, -, h3, -, -⟩ := numbers
    obtain ⟨-, hf⟩ := hv'
    unfold fresh sendAt at hf
    rw [h1, h3] at hf
    exact decide_eq_true (by omega)
  have := List.countP_mono_left key
  have h5 : (List.range slotsPerEpoch).countP (fun i => decide (27 ≤ i)) = 5 := by decide
  unfold validSlots
  omega

/-- So the share of the epoch's attestation reward a Mars validator can earn is at most
`5 * timelyTargetWeight` out of `slotsPerEpoch * (source + target + head)`: 130 / 1728, about 7.5%.
(Only the target flag is reachable, so each valid slot pays at most the target weight.) -/
theorem reward_at_most_130_of_1728 (D : Nat) (hD : 323000 ≤ D) :
    validSlots D * timelyTargetWeight ≤ 130 ∧
    slotsPerEpoch * (timelySourceWeight + timelyTargetWeight + timelyHeadWeight) = 1728 :=
  ⟨by have h := at_most_5_valid_slots D hD
      have hw : timelyTargetWeight = 26 := by decide
      rw [hw]; omega, by decide⟩

end MarsCheck
