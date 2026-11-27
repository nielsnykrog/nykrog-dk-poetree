"""
One-off migration (2026-11-27): fix mislabelled source roles in the
dsl-reformationssalmer corpus.

Background
----------
The fields `source.publisher` and `source.printer` were introduced for DSL's
"udgiver" / "trykker" metadata. On reflection the labels were wrong:

  * what we called `publisher` (DSL "udgiver") is the person who *collected /
    compiled / edited* the hymns and brought them to the press  -> `editor`
  * what we called `printer`  (DSL "trykker") is the printer-publisher who
    produced the book                                              -> `publisher`

This matches universal bibliographic categories and makes `publisher` mean the
same thing here (Lorenz Benedicht) as it will for 19th-c. sources (Gyldendal).

Scope: ONLY files whose source-id is `dsl-reformationssalmer`. Other corpora
(tekstnet, early-danish-ballads) carry `publisher: null, printer: null` and are
not remapped; use `--drop-null-printer` to remove the legacy `printer: null`
key from them (decided 2026-11-27: ballad scribes/owners are not publishers --
the manuscript name in `source.title` already carries that provenance).

Also harmonises one name: `Oluf Ulricksøn` -> `Oluf Ulriksen` (same person,
two spellings on the DSL pages; canonical form matches our book slugs).

Usage:
    python scripts/remap_dsl_publisher.py            # apply
    python scripts/remap_dsl_publisher.py --dry-run  # report only
    python scripts/remap_dsl_publisher.py --drop-null-printer [--dry-run]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POEMS = ROOT / "poems"
SOURCE_ID = "dsl-reformationssalmer"

# DSL pages spell this printer two ways; we keep the form used in our slugs.
NAME_FIXES = {"Oluf Ulricksøn": "Oluf Ulriksen"}

# PoeTree key order first, then local extensions in a stable position.
NEW_SOURCE_ORDER = [
    "id", "title", "year_published", "publisher", "place", "corpus", "url", "editor",
]


def remap_source(src: dict) -> tuple[dict, bool]:
    old_publisher = src.get("publisher")  # actually the compiler/editor
    old_printer = src.get("printer")      # actually the printer-publisher

    new_pub = NAME_FIXES.get(old_printer, old_printer)

    new = {
        "id": src.get("id"),
        "title": src.get("title"),
        "year_published": src.get("year_published"),
        "publisher": new_pub,
        "place": src.get("place"),
        "corpus": src.get("corpus"),
        "url": src.get("url"),
        "editor": old_publisher,
    }
    # Preserve any unexpected keys we don't know about (defensive).
    for k, v in src.items():
        if k not in new and k != "printer":
            new[k] = v
    return new, (new_pub != old_printer)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--drop-null-printer", action="store_true",
                    help="instead of the DSL remap, remove `printer: null` from non-DSL files")
    args = ap.parse_args()

    if args.drop_null_printer:
        return drop_null_printer(args.dry_run)

    files = sorted(POEMS.glob(f"{SOURCE_ID}--*.json"))
    if not files:
        print(f"no files found for {SOURCE_ID} in {POEMS}", file=sys.stderr)
        return 1

    changed = 0
    renamed = Counter()
    pairs = Counter()
    for path in files:
        raw = path.read_text(encoding="utf-8")
        poem = json.loads(raw)
        if poem.get("source", {}).get("corpus", "").startswith("Danske Reformationssalmer") is False:
            print(f"SKIP (unexpected corpus): {path.name}", file=sys.stderr)
            continue

        new_source, name_fixed = remap_source(poem["source"])
        pairs[(new_source["editor"], new_source["publisher"])] += 1
        if name_fixed:
            renamed[(poem["source"]["printer"], new_source["publisher"])] += 1

        poem["source"] = new_source
        out = json.dumps(poem, ensure_ascii=False, indent=2)
        if out != raw:
            changed += 1
            if not args.dry_run:
                path.write_text(out, encoding="utf-8")

    print(f"files scanned : {len(files)}")
    print(f"files changed : {changed}{' (dry-run, nothing written)' if args.dry_run else ''}")
    print("\neditor -> publisher (file count):")
    for (ed, pub), n in sorted(pairs.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {ed!s:<28} -> {pub}")
    if renamed:
        print("\nname harmonised:")
        for (a, b), n in renamed.items():
            print(f"  {n:4d}  {a!r} -> {b!r}")
    return 0


def drop_null_printer(dry_run: bool) -> int:
    """Remove the retired `printer` key from files where it is null and no remap applies."""
    changed = 0
    kept = 0
    for path in sorted(POEMS.glob("*.json")):
        if path.name.startswith(f"{SOURCE_ID}--"):
            continue
        raw = path.read_text(encoding="utf-8")
        poem = json.loads(raw)
        src = poem.get("source")
        if not isinstance(src, dict) or "printer" not in src:
            continue
        if src["printer"] is not None:
            print(f"REFUSE (non-null printer, needs a real decision): {path.name}", file=sys.stderr)
            kept += 1
            continue
        del src["printer"]
        out = json.dumps(poem, ensure_ascii=False, indent=2)
        if out != raw:
            changed += 1
            if not dry_run:
                path.write_text(out, encoding="utf-8")
    print(f"files changed : {changed}{' (dry-run, nothing written)' if dry_run else ''}")
    print(f"files refused : {kept}")
    return 1 if kept else 0


if __name__ == "__main__":
    raise SystemExit(main())
