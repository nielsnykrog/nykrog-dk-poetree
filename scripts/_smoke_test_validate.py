"""Smoke test for validate.py. Builds a synthetic good poem + a few bad ones."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
TEST_DIR = SCRIPTS / "_smoke"
TEST_DIR.mkdir(exist_ok=True)

good = {
    "id": "",
    "title": "Testdigtet",
    "year_created": 1620,
    "author": {
        "name": "Anders Bording",
        "viaf": None,
        "wiki": "Q1136",
        "country": None,
        "born": 1619,
        "died": 1677,
    },
    "source": {
        "id": None,
        "title": "Anders Bordings Samlede Skrifter",
        "year_published": 1733,
        "publisher": None,
        "place": "København",
        "corpus": "Tekstnet",
        "url": "https://tekstnet.dk/example",
    },
    "body": [
        {"id": 0, "stanza_id": 0, "text": "Første linje af første strofe.", "part": False},
        {"id": 1, "stanza_id": 0, "text": "Anden linje af første strofe.", "part": False},
        {"id": 2, "stanza_id": 1, "text": "Første linje af anden strofe.", "part": False},
    ],
}
(TEST_DIR / "good.json").write_text(json.dumps(good, ensure_ascii=False, indent=2), encoding="utf-8")

bad = {
    "title": "Missing many fields",
    "body": "should be a list, not a string",
}
(TEST_DIR / "bad.json").write_text(json.dumps(bad, ensure_ascii=False, indent=2), encoding="utf-8")

print("--- Running validator on good.json (expect exit 0) ---")
r1 = subprocess.run([sys.executable, str(SCRIPTS / "validate.py"), str(TEST_DIR / "good.json")],
                    capture_output=True, text=True)
print(r1.stdout)
print("STDERR:", r1.stderr)
print("EXIT:", r1.returncode)

print("\n--- Running validator on bad.json (expect exit 1, multiple errors) ---")
r2 = subprocess.run([sys.executable, str(SCRIPTS / "validate.py"), str(TEST_DIR / "bad.json")],
                    capture_output=True, text=True)
print(r2.stdout)
print("STDERR:", r2.stderr)
print("EXIT:", r2.returncode)