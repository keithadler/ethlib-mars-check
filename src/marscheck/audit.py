"""What does EthLib cover? Read from its source, not from its README.

Run against a checkout of ethereum/EthLib. Every row is decided by a file or an
exported symbol found there (or its absence), never by a claim.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# (area, name, where the Ethereum specification defines it, evidence that EthLib has it)
# `export` evidence is a C entry point found in an @[export ...] attribute;
# `file` evidence is a Lean source file.
CHECKLIST = [
    ("consensus", "BLS12-381 FastAggregateVerify (eth_ wrapper)", "consensus-specs bls.md",
     ("export", "eth_bls_fast_aggregate_verify")),
    ("consensus", "BLS12-381 aggregate public keys", "consensus-specs bls.md",
     ("export", "eth_bls_aggregate_pubkeys")),
    ("consensus", "BLS12-381 signing and key generation", "consensus-specs bls.md",
     ("export", "eth_bls_sign")),
    ("consensus", "KZG commitments, blob proofs (EIP-4844)", "consensus-specs deneb polynomial-commitments.md",
     ("export", "eth_kzg_verify_blob_kzg_proof")),
    ("consensus", "KZG cells and recovery (PeerDAS, EIP-7594)", "consensus-specs fulu polynomial-commitments-sampling.md",
     ("export", "eth_kzg_recover_cells_and_kzg_proofs")),
    ("consensus", "XMSS hash-based signatures (post-quantum)", "leanSig / leanSpec",
     ("export", "eth_xmss_verify")),
    ("consensus", "SHA-256", "FIPS 180-4", ("file", "EthLib/Cryptography/Hash/Sha256.lean")),
    ("consensus", "SSZ encoding (pinned dependency)", "consensus-specs ssz/simple-serialize.md",
     ("dependency", "ssz")),
    ("consensus", "Beacon state transition", "consensus-specs beacon-chain.md",
     ("file", "EthLib/Consensus")),
    ("consensus", "Fork choice", "consensus-specs fork-choice.md", ("file", "EthLib/ForkChoice")),
    ("networking", "libp2p unsigned varint", "multiformats unsigned-varint",
     ("file", "EthLib/Networking/Encoding/Varint.lean")),
    ("execution", "Keccak-256", "FIPS 202 / Yellow Paper", ("file", "EthLib/Cryptography/Hash/Keccak.lean")),
    ("execution", "secp256k1 ECDSA / ecrecover", "Yellow Paper, SEC 2", ("file", "EthLib/Cryptography/Secp256k1")),
    ("execution", "RLP", "Yellow Paper appendix B", ("file", "EthLib/Encoding/Rlp.lean")),
    ("execution", "Merkle-Patricia trie", "Yellow Paper appendix D", ("file", "EthLib/Trie")),
    ("execution", "EVM", "Yellow Paper", ("file", "EthLib/Evm")),
]


def exports(root: Path) -> set[str]:
    names: set[str] = set()
    for f in (root / "EthLib").rglob("*.lean"):
        if f.name == "TrustedSetupData.lean":
            continue
        for _, code in code_lines(f.read_text()):
            names.update(re.findall(r"@\[export (\w+)\]", code))
    return names


def code_lines(text: str):
    """(line number, code) with line comments and /- block comments removed."""
    depth = 0
    for i, line in enumerate(text.splitlines(), 1):
        out, j = [], 0
        while j < len(line):
            two = line[j:j + 2]
            if two == "/-":
                depth += 1
                j += 2
            elif two == "-/" and depth:
                depth -= 1
                j += 2
            elif depth == 0 and two == "--":
                break
            else:
                if depth == 0:
                    out.append(line[j])
                j += 1
        yield i, "".join(out)


def proof_hygiene(root: Path) -> dict:
    """Words in the Lean source that weaken a proof, outside comments and the data file."""
    hits: dict[str, list[str]] = {"sorry": [], "native_decide": [], "axiom": []}
    for f in (root / "EthLib").rglob("*.lean"):
        if f.name == "TrustedSetupData.lean":
            continue
        for i, code in code_lines(f.read_text()):
            rel = f"{f.relative_to(root)}:{i}"
            if re.search(r"\bsorry\b", code):
                hits["sorry"].append(rel)
            if re.search(r"\bnative_decide\b", code):
                hits["native_decide"].append(rel)
            if re.match(r"\s*axiom\b", code):
                hits["axiom"].append(rel)
    return hits


def time_and_io(root: Path) -> list[str]:
    """Reads of the clock, the network or randomness anywhere in the library."""
    rx = re.compile(r"\b(IO\.monoMsNow|IO\.monoNanosNow|IO\.sleep|IO\.getRandomBytes|IO\.rand|"
                    r"IO\.Process|IO\.FS\.|Std\.Internal\.UV|Std\.Http|Std\.Net)")
    out = []
    for f in (root / "EthLib").rglob("*.lean"):
        if f.name == "TrustedSetupData.lean":
            continue
        for i, code in code_lines(f.read_text()):
            if rx.search(code):
                out.append(f"{f.relative_to(root)}:{i}: {code.strip()[:100]}")
    return out


def run(root: Path) -> dict:
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    ex = exports(root)
    manifest = (root / "lakefile.lean").read_text()
    rows = []
    for area, name, spec, (kind, ev) in CHECKLIST:
        if kind == "export":
            have = ev in ex
        elif kind == "file":
            have = (root / ev).exists()
        else:
            have = f"require {ev} " in manifest or f"require {ev}\n" in manifest
        rows.append({"area": area, "primitive": name, "spec": spec, "evidence": f"{kind}:{ev}",
                     "covered": have})
    return {
        "ethlib_commit": sha,
        "exports": sorted(ex),
        "rows": rows,
        "hygiene": proof_hygiene(root),
        "time_and_io": time_and_io(root),
    }


if __name__ == "__main__":
    import sys
    json.dump(run(Path(sys.argv[1])), sys.stdout, indent=2)
    print()
