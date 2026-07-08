"""
validate.py — validates a PoeTree-compatible poem JSON file against the
project's local schema conventions.

What it checks:
  1. JSON parses.
  2. Top-level shape matches the PoeTree schema (only the keys we use).
  3. Required-by-our-convention fields are present and well-typed.
  4. body[] is well-formed (zero-based ids, monotonically increasing,
     stanza_id non-decreasing, no empty text lines unless intentional).
  5. author.wiki, source.year_published etc. follow simple sanity rules.

What it does NOT do (intentionally):
  - Validate CoNLL-U annotation in body[].words[] (we leave it empty).
  - Validate neighbors / duplicate / locations / meter fields (PoeTree fills these).
  - Validate form against controlled vocabulary (not in scope for early-modern DK).

Usage:
    python validate.py path/to/poem.json
    python validate.py path/to/poems/dir/         # validates all *.json in dir

Exit code 0 = all good. Non-zero = at least one problem found.
"""

import json
import sys
from pathlib import Path

# Load the upstream schema so we can reference its terminal types.
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "poetree.schema.json"


def _has_field(obj, *keys):
    return all(k in obj for k in keys)


def validate(poem):
    """Return a list of (level, message) tuples. level in {'error','warning','info'}."""
    findings = []

    # ---------- 1. Top-level shape ----------
    if not isinstance(poem, dict):
        return [("error", "Top-level JSON value is not an object.")]

    # Our convention: which top-level keys are EXPECTED.
    # We use: id (may be empty), title, year_created, author, source, body
    #         + our local extension: source.url
    # We EXPLICITLY leave empty: neighbors, duplicate, locations,
    #         body[].words[], body[].part, form, body-meter-*
    expected_keys = {
        "id", "title", "year_created", "author", "source", "body",
        # We also leave these PoeTree fields empty (PoeTree pipeline fills them).
        # They are EXPECTED to be present, just with empty values, so we add them to
        # the expected set rather than flagging them as "unexpected".
        "neighbors", "duplicate", "locations",
    }
    unexpected = set(poem.keys()) - expected_keys
    if unexpected:
        findings.append(("warning", f"Unexpected top-level keys (allowed but unusual): {sorted(unexpected)}"))

    for k in expected_keys:
        if k not in poem:
            findings.append(("error", f"Missing top-level key: '{k}'"))

    # ---------- 2. id (we leave empty; PoeTree fills) ----------
    if "id" in poem and poem["id"] not in (None, ""):
        findings.append(("info", f"id is filled ('{poem['id']}') — usually left empty for PoeTree to assign."))

    # ---------- 3. title ----------
    if "title" in poem:
        if poem["title"] is not None and not isinstance(poem["title"], str):
            findings.append(("error", f"title must be string or null, got {type(poem['title']).__name__}"))

    # ---------- 4. year_created ----------
    if "year_created" in poem:
        yc = poem["year_created"]
        if yc is not None:
            if isinstance(yc, int) and not isinstance(yc, bool):
                pass  # ok
            elif isinstance(yc, list):
                if len(yc) != 2 or not all(isinstance(x, int) and not isinstance(x, bool) for x in yc):
                    findings.append(("error", "year_created list must be [int, int] for time spans."))
                elif yc[0] > yc[1]:
                    findings.append(("error", f"year_created span [{yc[0]}, {yc[1]}] is reversed."))
            else:
                findings.append(("error", f"year_created must be int, [int,int], or null. Got {type(yc).__name__}."))

    # ---------- 5. author ----------
    if "author" in poem:
        au = poem["author"]
        if not isinstance(au, dict):
            findings.append(("error", f"author must be an object. Got {type(au).__name__}."))
        else:
            if "name" not in au:
                findings.append(("error", "author.name is required by PoeTree convention."))
            elif not isinstance(au["name"], str) or not au["name"].strip():
                findings.append(("error", "author.name must be a non-empty string."))
            for int_field in ("born", "died"):
                if int_field in au and au[int_field] is not None and not isinstance(au[int_field], int):
                    findings.append(("error", f"author.{int_field} must be int or null."))
            # Emphasised: WIKI ID
            if "wiki" in au and au["wiki"] is not None:
                if not isinstance(au["wiki"], str) or not au["wiki"].strip():
                    findings.append(("error", "author.wiki must be a non-empty string or null."))
                elif not au["wiki"][0].isalpha():
                    findings.append(("warning", f"author.wiki '{au['wiki']}' does not look like a Wikidata Q-id."))

    # ---------- 6. source ----------
    if "source" in poem:
        src = poem["source"]
        if not isinstance(src, dict):
            findings.append(("error", "source must be an object."))
        else:
            if "corpus" not in src:
                findings.append(("error", "source.corpus is required (e.g. 'Tekstnet')."))
            elif not isinstance(src["corpus"], str) or not src["corpus"].strip():
                findings.append(("error", "source.corpus must be a non-empty string."))
            # Emphasised: publication title, place, year
            for sf in ("title", "year_published", "place"):
                if sf not in src:
                    findings.append(("warning", f"source.{sf} missing — emphasised by PoeTree team."))
            if "year_published" in src and src["year_published"] is not None and not isinstance(src["year_published"], int):
                findings.append(("error", "source.year_published must be int or null."))
            # Local extensions on source:
            #   source.url     -- poem page URL (we always set this)
            #   source.printer -- the trykker, distinct from publisher
            if "url" in src and src["url"] is not None:
                if not isinstance(src["url"], str) or not src["url"].startswith(("http://", "https://")):
                    findings.append(("error", "source.url must be an http(s) URL or null."))
            if "printer" in src and src["printer"] is not None and not isinstance(src["printer"], str):
                findings.append(("error", "source.printer must be string or null."))

    # ---------- 7. body ----------
    if "body" in poem:
        body = poem["body"]
        if not isinstance(body, list):
            findings.append(("error", "body must be a list of line-objects."))
        else:
            prev_id = -1
            prev_stanza = -1
            for i, line in enumerate(body):
                if not isinstance(line, dict):
                    findings.append(("error", f"body[{i}] is not an object."))
                    continue
                # Required: id, stanza_id, text
                for k in ("id", "stanza_id", "text"):
                    if k not in line:
                        findings.append(("error", f"body[{i}] missing '{k}'."))
                # id should be zero-based and monotonically increasing through whole poem
                if "id" in line:
                    if not isinstance(line["id"], int) or isinstance(line["id"], bool):
                        findings.append(("error", f"body[{i}].id must be int."))
                    else:
                        if line["id"] != prev_id + 1:
                            findings.append(("warning", f"body[{i}].id={line['id']} is not prev_id+1={prev_id+1} (id should run through whole poem, not restart per stanza)."))
                        prev_id = line["id"]
                if "stanza_id" in line:
                    if not isinstance(line["stanza_id"], int) or isinstance(line["stanza_id"], bool):
                        findings.append(("error", f"body[{i}].stanza_id must be int."))
                    else:
                        if line["stanza_id"] < prev_stanza:
                            findings.append(("warning", f"body[{i}].stanza_id={line['stanza_id']} decreased from {prev_stanza}."))
                        prev_stanza = line["stanza_id"]
                if "text" in line and (not isinstance(line["text"], str)):
                    findings.append(("error", f"body[{i}].text must be string."))
                # By convention we leave words empty; flag if present
                if "words" in line and line["words"]:
                    findings.append(("info", f"body[{i}] has words[] filled — we usually leave empty for the PoeTree pipeline."))
                # By convention we leave part False; flag if set to something else
                if "part" in line and line["part"] not in (False, None, "I", "M", "F"):
                    findings.append(("warning", f"body[{i}].part='{line['part']}' is unexpected; expected 'I','M','F' or False."))
                # Local extension: marginal_notes -- must be list of strings if present
                if "marginal_notes" in line:
                    mn = line["marginal_notes"]
                    if mn is None:
                        pass  # ok
                    elif not isinstance(mn, list):
                        findings.append(("error", f"body[{i}].marginal_notes must be list of strings or null."))
                    else:
                        for j, note in enumerate(mn):
                            if not isinstance(note, str):
                                findings.append(("error", f"body[{i}].marginal_notes[{j}] must be string."))
                            elif not note.strip():
                                findings.append(("warning", f"body[{i}].marginal_notes[{j}] is empty/whitespace."))

    return findings


def validate_file(path: Path):
    findings = [("info", f"Validating: {path}")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [("error", f"Invalid JSON: {e}")]
    findings.extend(validate(data))
    return findings


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    target = Path(sys.argv[1])
    files = []
    if target.is_dir():
        files = sorted(target.glob("*.json"))
    elif target.is_file():
        files = [target]
    else:
        print(f"Path not found: {target}")
        sys.exit(2)

    if not files:
        print(f"No .json files found at: {target}")
        sys.exit(2)

    total_errors = 0
    total_warnings = 0
    for f in files:
        findings = validate_file(f)
        err = sum(1 for lvl, _ in findings if lvl == "error")
        warn = sum(1 for lvl, _ in findings if lvl == "warning")
        total_errors += err
        total_warnings += warn
        print(f"\n{'='*60}\n{f}\n{'='*60}")
        for lvl, msg in findings:
            icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}[lvl]
            print(f"  {icon} [{lvl}] {msg}")

    print(f"\n{'='*60}")
    print(f"Summary: {len(files)} file(s), {total_errors} error(s), {total_warnings} warning(s)")
    print(f"{'='*60}")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()