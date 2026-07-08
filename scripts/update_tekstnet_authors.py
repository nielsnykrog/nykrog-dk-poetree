"""Update Tekstnet poem JSONs and rename files.

For each dsl-tekstnet poem file (in poems/ and danish-dramas/):
  1. Read JSON.
  2. Look up author by filename's current author-slug (via SLUG_TO_KEY map).
  3. Update author.name to name_full from authors.json.
  4. Add author.wiki = wiki_id.
  5. Compute new filename with new author-slug (transliterated full name).
  6. Rename file.

Idempotent: if filename is already correct, skip rename (still updates JSON).
If a target filename already exists, abort and report (shouldn't happen, we
verified no collisions).
"""
import json, re, shutil, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"C:\Users\niels\Documents\nykrog-dk-poetry")
POEMS = ROOT / "poems"
DRAMAS = ROOT / "danish-dramas"

with open(ROOT / "sources" / "authors.json", encoding="utf-8") as f:
    authors = json.load(f)
authors_by_key = {a["key"]: a for a in authors}

SLUG_TO_KEY = {
    "adam-oehlenschlager": "oehlenschlaeger-a",
    "anders-arrebo": "arrebo-a",
    "carl-ploug": "carl-ploug",
    "carsten-hauch": "hauch-c",
    "fr-paludan-muller": "paludan-mueller-fr",
    "gustaf-munch-petersen": "munch-petersen-g",
    "hans-adolph-brorson": "brorson-ha",
    "hc-andersen": "andersen-hc",
    "hc-ørsted": "oersted-hc",
    "hr-michael": "hr-michael",
    "hv-kaalund": "kaalund-hv",
    "jl-heiberg": "heiberg-jl",
    "johan-skjoldborg": "skjoldborg-j",
    "jp-jacobsen": "jacobsen-jp",
    "peder-ræv-lille": "peder-raev-lille",
    "thomas-kingo": "thomas-kingo",
    "thøger-larsen": "larsen-t",
}


def to_author_slug(name_full, drop_honorific=True):
    if not name_full:
        return None
    s = name_full
    if drop_honorific:
        s = re.sub(r'^(Hr\.|Dr\.|Fr\.|Prof\.|H\.)\s+', '', s, flags=re.IGNORECASE)
    replacements = {
        'æ': 'ae', 'ø': 'o', 'å': 'aa',
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ÿ': 'y',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'á': 'a', 'à': 'a', 'â': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ñ': 'n', 'ç': 'c', 'ß': 'ss',
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
        s = s.replace(src.upper(), dst)
    s = s.lower()
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-+', '-', s)
    return s


def main(dry_run=False):
    targets = []
    for d in (POEMS, DRAMAS):
        if d.exists():
            targets.extend(d.glob("dsl-tekstnet--*.json"))

    n_renamed = 0
    n_updated = 0
    n_anonymous = 0
    n_already_done = 0
    n_unknown = 0
    n_errors = 0
    collisions = []
    new_names = set()

    # First pass: check for collisions in the planned new names
    plan = []
    for f in sorted(targets):
        parts = f.name.split("--")
        if len(parts) < 4:
            print(f"  WARN: unexpected filename format: {f.name}")
            continue
        old_author_slug = parts[1]
        poem_title = parts[2]
        book_slug = parts[3]

        # Map old slug -> new slug
        if old_author_slug == "anonymous":
            new_author_slug = "anonymous"
            n_anonymous += 1
            update_json = False
        elif old_author_slug in SLUG_TO_KEY:
            key = SLUG_TO_KEY[old_author_slug]
            if key not in authors_by_key:
                print(f"  ERROR: {old_author_slug} -> {key} not in authors.json ({f.name})")
                n_errors += 1
                continue
            a = authors_by_key[key]
            new_author_slug = to_author_slug(a["name_full"])
            update_json = True
        else:
            print(f"  WARN: unknown author-slug '{old_author_slug}' in {f.name}")
            n_unknown += 1
            continue

        new_name = f"dsl-tekstnet--{new_author_slug}--{poem_title}--{book_slug}"
        if new_name in new_names:
            collisions.append((f.name, new_name))
            continue
        new_names.add(new_name)

        plan.append((f, new_name, update_json, key if update_json else None))

    if collisions:
        print(f"\n!!! COLLISIONS DETECTED: {len(collisions)}")
        for old, new in collisions:
            print(f"  {old} -> {new}")
        if not dry_run:
            sys.exit(1)

    print(f"\nPlan: {len(plan)} files to process")
    print(f"  - Renames needed: {sum(1 for f, n, _, _ in plan if f.name != n)}")
    print(f"  - Anonymous (skip JSON update): {n_anonymous}")
    print(f"  - Unknown author-slugs: {n_unknown}")

    if dry_run:
        print("\n[DRY RUN] First 20 changes:")
        for f, new_name, upd, key in plan[:20]:
            marker = "RENAME" if f.name != new_name else "(no rename)"
            upd_marker = "JSON-UPDATE" if upd else ""
            print(f"  [{marker:7}] [{upd_marker:12}] {f.name} -> {new_name}")
        return

    # Apply
    for f, new_name, upd, key in plan:
        # 1. Update JSON if needed
        if upd and key:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  ERROR reading {f}: {e}")
                n_errors += 1
                continue
            author = data.get("author", {})
            if not isinstance(author, dict):
                author = {}
            a = authors_by_key[key]
            old_name = author.get("name")
            new_name_full = a["name_full"]
            if old_name != new_name_full or "wiki" not in author:
                author["name"] = new_name_full
                author["wiki"] = a["wiki_id"]
                # Preserve other author fields (viaf, country, born, died, ...)
                data["author"] = author
                # Write back
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                n_updated += 1
        elif not upd:
            n_anonymous += 0

        # 2. Rename file
        if f.name != new_name:
            new_path = f.parent / new_name
            try:
                f.rename(new_path)
                n_renamed += 1
            except Exception as e:
                print(f"  ERROR renaming {f.name}: {e}")
                n_errors += 1

    print(f"\nDone. Renamed {n_renamed}, JSON-updated {n_updated}, anonymous skipped {n_anonymous}, unknown {n_unknown}, errors {n_errors}")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)