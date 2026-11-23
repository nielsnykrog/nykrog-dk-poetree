"""Real test for validate.py — ASSERTS outcomes, exits non-zero on any failure.

History: the original smoke test only printed validator output and never
asserted, so (a) its own 'good' fixture had been failing with 3 errors
(missing neighbors/duplicate/locations) unnoticed, and (b) the validator's
docstring promised 'no empty text lines' with no code behind it. PR #1
(stanza gaps, empty lines) then slipped through. Tests assert or they don't
count.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
TEST_DIR = SCRIPTS / "_smoke"
TEST_DIR.mkdir(exist_ok=True)

failures = []


def run_case(name, poem, expect_exit_0, expected_substrings=()):
    """Write poem JSON, run validator, assert exit code + expected messages."""
    path = TEST_DIR / f"{name}.json"
    path.write_text(json.dumps(poem, ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "validate.py"), str(path)],
                       capture_output=True, text=True)
    ok = True
    if expect_exit_0 and r.returncode != 0:
        failures.append(f"{name}: expected exit 0, got {r.returncode}\n{r.stdout}")
        ok = False
    if not expect_exit_0 and r.returncode == 0:
        failures.append(f"{name}: expected non-zero exit, got 0")
        ok = False
    for sub in expected_substrings:
        if sub not in r.stdout:
            failures.append(f"{name}: expected output to contain {sub!r}\n{r.stdout}")
            ok = False
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")


def base_poem():
    return {
        "id": "",
        "title": "Testdigtet",
        "year_created": 1620,
        "author": {
            "name": "Anders Bording", "viaf": None, "wiki": "Q1136",
            "country": None, "born": 1619, "died": 1677,
        },
        "source": {
            "id": None, "title": "Anders Bordings Samlede Skrifter",
            "year_published": 1733, "publisher": None, "place": "København",
            "corpus": "Tekstnet", "url": "https://tekstnet.dk/example",
        },
        "neighbors": None, "duplicate": False, "locations": False,
        "body": [],
    }


def line(i, stanza, text):
    return {"id": i, "stanza_id": stanza, "text": text, "part": False,
            "marginal_notes": [], "words": []}


# --- good: well-formed, multi-stanza, zero-based, contiguous ---
good = base_poem()
good["body"] = [
    line(0, 0, "Første linje af første strofe."),
    line(1, 0, "Anden linje af første strofe."),
    line(2, 1, "Første linje af anden strofe."),
    line(3, 1, "Anden linje af anden strofe."),
    line(4, 2, "Første linje af tredje strofe."),
]
run_case("good", good, expect_exit_0=True)

# --- bad_shape: broken top level + body ---
bad = {"title": "Missing many fields", "body": "should be a list, not a string"}
run_case("bad_shape", bad, expect_exit_0=False,
         expected_substrings=["Missing top-level key", "body must be a list"])

# --- empty text line (PR #1 class) ---
p = base_poem()
p["body"] = [line(0, 0, "Første linje."), line(1, 0, "")]
run_case("bad_empty_text", p, expect_exit_0=False,
         expected_substrings=["text is empty/whitespace"])

# --- stanza gap (PR #1 class): 0,1 then jumps to 3 ---
p = base_poem()
p["body"] = [line(0, 0, "a"), line(1, 0, "b"), line(2, 3, "c")]
run_case("bad_stanza_gap", p, expect_exit_0=False,
         expected_substrings=["stanza_ids must be contiguous"])

# --- first stanza not zero ---
p = base_poem()
p["body"] = [line(0, 1, "a"), line(1, 1, "b")]
run_case("bad_stanza_first", p, expect_exit_0=False,
         expected_substrings=["First stanza_id is 1, must be 0"])

# --- id gap (error now, was warning) ---
p = base_poem()
p["body"] = [line(0, 0, "a"), line(2, 0, "b")]
run_case("bad_id_gap", p, expect_exit_0=False,
         expected_substrings=["is not prev_id+1"])

# --- stanza_id decrease is also caught by contiguity ---
p = base_poem()
p["body"] = [line(0, 0, "a"), line(1, 1, "b"), line(2, 0, "c")]
run_case("bad_stanza_decrease", p, expect_exit_0=False,
         expected_substrings=["must be contiguous"])

print()
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"---\n{f}")
    sys.exit(1)
print("All smoke tests passed.")
