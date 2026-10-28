"""The coverage audit decides each row from files and symbols, so test it on a tiny fake tree."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from marscheck import audit  # noqa: E402


def make_tree(tmp_path: Path) -> Path:
    lib = tmp_path / "EthLib" / "Cryptography" / "Bls"
    lib.mkdir(parents=True)
    (lib / "Exports.lean").write_text(
        "@[export eth_bls_fast_aggregate_verify]\ndef a := 1\n"
        "-- @[export eth_bls_sign]\n"
        "/- @[export eth_bls_fake] -/\n")
    (tmp_path / "lakefile.lean").write_text('require ssz from git "x"\n')
    return tmp_path


def test_exports_are_read_from_code_not_comments(tmp_path):
    ex = audit.exports(make_tree(tmp_path))
    assert ex == {"eth_bls_fast_aggregate_verify"}  # the line comment and block comment are ignored


def test_hygiene_ignores_comments_and_strings_in_docs(tmp_path):
    t = make_tree(tmp_path)
    (t / "EthLib" / "P.lean").write_text(
        "/-! this proof is kernel-checked without `native_decide` and has no sorry -/\n"
        "theorem a : True := trivial -- not a sorry\n"
        "theorem b : 1 = 1 := by native_decide\n"
        "theorem c : True := by sorry\n")
    h = audit.proof_hygiene(t)
    assert h["native_decide"] == ["EthLib/P.lean:3"]
    assert h["sorry"] == ["EthLib/P.lean:4"]
    assert h["axiom"] == []


def test_clock_and_network_reads_are_found(tmp_path):
    t = make_tree(tmp_path)
    (t / "EthLib" / "T.lean").write_text("def now : IO Nat := IO.monoMsNow\n-- IO.sleep 5\n")
    assert audit.time_and_io(t) == ["EthLib/T.lean:1: def now : IO Nat := IO.monoMsNow"]


def test_the_recorded_audit_is_what_the_readme_says():
    import json
    d = json.loads((ROOT / "results" / "coverage.json").read_text())
    covered = {r["primitive"] for r in d["rows"] if r["covered"]}
    missing = {r["primitive"] for r in d["rows"] if not r["covered"]}
    assert "KZG cells and recovery (PeerDAS, EIP-7594)" in covered
    assert "BLS12-381 FastAggregateVerify (eth_ wrapper)" in covered
    assert {"Keccak-256", "RLP", "EVM", "Beacon state transition"} <= missing
    assert d["time_and_io"] == []
    assert d["hygiene"]["sorry"] == [] and d["hygiene"]["axiom"] == []
