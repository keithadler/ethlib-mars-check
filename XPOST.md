I checked ethereum/EthLib two ways. Does it cover Ethereum? And would any of it break between Mars and Earth?

Short answer: it covers a slice, the library itself is fine on Mars, and Ethereum's consensus is not.

WHAT IT COVERS

I read the source, not the README. Against a 16-item list of Ethereum primitives, EthLib has 8: BLS12-381 FastAggregateVerify and key aggregation, KZG blob proofs, PeerDAS cells and recovery, XMSS, SHA-256, SSZ (a pinned dependency), and the libp2p varint.

It does not have BLS signing, Keccak-256, secp256k1, RLP, the trie, the EVM, the state transition or fork choice. That matches what it says it is: verified consensus-layer cryptography, not Ethereum.

No sorry, no axiom. Two native_decide known answers in the XMSS proofs, both listed in its own baseline.

THE LIBRARY ON MARS

Its source reads no clock, no network, no randomness. A signature or a KZG proof checks the same 20 light-minutes away.

THE PROTOCOL ON MARS

Real NASA/JPL ephemeris, 2026 to 2030: Mars is 5.4 to 21.2 light-minutes from Earth. Ethereum wants a vote within 4 seconds of a slot starting.

I applied the consensus spec's own rules. Every number is read out of the spec at a pinned commit, with its line.

A head vote has to reach Earth within 8 seconds, a source vote within 56. Mars never gets closer than 323.

A vote's source must match the latest justified checkpoint, which moves every 6.4 minutes. Seen from Mars it is always stale by the light delay. Once that passes 376 seconds, nothing a Mars validator signs can count. That is 92% of days.

On the other 8%, at most 16% of its votes count, for 7.5% of the full reward. No head or source vote, ever.

I also proved the core of this in Lean (core Lean, no Mathlib, re-checked with an independent kernel): no vote counts past 376 seconds, the bound is exact, a head vote needs 8 seconds, a source vote 56, and a vote can count on exactly 119 of 1,527 days. The theorems are about my reading of the spec's rules, not an executable spec.

WHAT STILL WORKS

A light client: it runs at most 0.35 hours behind, and its committee rotates every 27.3. Ordinary transactions too, seen finalized from Mars in 24 to 62 minutes. That is the speed of light, not a flaw.

WHAT ALSO DOESN'T

Data availability sampling: one sample is a 646 second round trip at best, and the vote is due in 4. And a full node at the blob cap: 1.84 Mbit/s of blobs needed, against 1.75 on NASA's best orbiter link.

WHAT I DID NOT DO

I did not run the model or the proofs against the executable spec. They are my reading of the spec text, with the generous reading chosen so a "no" is firm. The link rates are one orbiter's. It models Ethereum's consensus timing, not rollups or a design built for the distance.

I also tried to rebuild EthLib's proofs. 3,543 of 3,557 jobs finished with no error, then one file stalled on my 12 GB machine and I could not get it through. So I am not claiming I re-verified them.

Repo, data, tests and the four charts: github.com/keithadler/ethlib-mars-check

Hey diehard Ethereum people, I have a task for you.

I took EthLib and showed there's work to be done before money can move between Earth and Mars and back. Transactions can cross, slowly. Validating from Mars is the part that needs real work.

If this was useful and you feel like saying thanks, I'd happily accept a little ETH (it'd be my first).

Mars is far, but my wallet is right here:

0x88adFCaa8FFaC62618b34F87FBede6394C829B1e
