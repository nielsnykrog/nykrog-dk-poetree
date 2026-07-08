"""Detect poems where one is contained inside another (same title + same source).

Two metrics:
  - containment A->B:  how much of A's text is also in B (in either order)
  - containment B->A:  vice versa
  - if either is >=90% AND the candidate titles + source match, flag.

Output: review_duplicates/DUPLICATES.md + folder with each pair copied.
"""
import json, re, shutil
from pathlib import Path
from collections import defaultdict

POEMS = Path(__file__).parent.parent / "poems"
OUT = Path(__file__).parent.parent / "review_duplicates"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()


def normalize(text: str) -> str:
    """Normalise: strip whitespace, lowercase, drop punctuation/diacritics for matching."""
    if not text:
        return ""
    # Drop dagger / pilcrows / page numbers
    text = re.sub(r"[†‡¶⁕*✝]", "", text)
    text = text.replace("\u017f", "s")  # long s
    text = text.lower()
    # remove diacritics: æ->ae, ø->oe, å->aa
    text = text.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    text = text.replace("ÿ", "y").replace("ö", "o")
    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()
    # remove leading/trailing punctuation
    text = re.sub(r"^[\W_]+|[\W_]+$", "", text)
    return text


def lines_of(data):
    """Return normalised non-empty lines of the body."""
    out = []
    for line in data.get("body", []):
        if isinstance(line, dict) and "text" in line:
            t = normalize(line["text"])
            if t and len(t) >= 3:
                out.append(t)
    return out


def containment(short_lines, long_lines):
    """How many of short_lines appear (as whole strings) in long_lines? Return 0..1."""
    if not short_lines:
        return 0.0
    s = set(short_lines)
    l = set(long_lines)
    if not s:
        return 0.0
    return len(s & l) / len(s)


def source_of(data):
    s = data.get("source", {})
    return (s.get("title", ""), s.get("year_published", ""), s.get("corpus", ""))


def main():
    files = sorted(POEMS.glob("*.json"))
    # Group by (title_norm, source_title_norm)
    buckets = defaultdict(list)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = normalize(data.get("title", ""))
        if not title or title == ".":
            continue
        src_title, _, _ = source_of(data)
        src_title = normalize(src_title)
        key = (title, src_title)
        buckets[key].append((f, data))

    pairs = []  # list of (file_a, file_b, %a_in_b, %b_in_a, reason)
    for key, items in buckets.items():
        if len(items) < 2:
            continue
        # For efficiency, only compare within bucket
        # Compute line-sets
        enriched = []
        for f, data in items:
            ln = lines_of(data)
            enriched.append((f, data, ln, len(ln)))
        for i in range(len(enriched)):
            for j in range(i+1, len(enriched)):
                fa, da, la, la_count = enriched[i]
                fb, db, lb, lb_count = enriched[j]
                if la_count == 0 or lb_count == 0:
                    continue
                # containment in each direction
                ci = containment(la, lb)
                cj = containment(lb, la)
                if max(ci, cj) >= 0.90:
                    pairs.append((fa, fb, ci, cj, la_count, lb_count))

    # Write manifest
    md = OUT / "DUPLICATES.md"
    with open(md, "w", encoding="utf-8") as out:
        out.write(f"# Duplicate / containment candidates — {len(pairs)} pairs\n\n")
        out.write("Same title + same source. Pairs sorted by containment severity.\n\n")
        out.write("| A→B | B→A | A lines | B lines | Title | File A | File B |\n")
        out.write("|---:|---:|---:|---:|---|---|---|\n")
        # Sort: containment pairs where one direction is full (1.0) first
        pairs_sorted = sorted(pairs, key=lambda x: -max(x[2], x[3]))
        for fa, fb, ci, cj, la, lb in pairs_sorted:
            with open(fa, encoding="utf-8") as fh:
                title = json.load(fh).get("title", "")
            out.write(f"| {ci*100:.0f}% | {cj*100:.0f}% | {la} | {lb} | {title} | `{fa.name}` | `{fb.name}` |\n")

    # Copy each pair into a subfolder for inspection
    pairs_dir = OUT / "pairs"
    pairs_dir.mkdir()
    for i, (fa, fb, ci, cj, la, lb) in enumerate(pairs_sorted):
        d = pairs_dir / f"{i+1:03d}_pair"
        d.mkdir()
        shutil.copy2(fa, d / f"A__{fa.name}")
        shutil.copy2(fb, d / f"B__{fb.name}")
        with open(d / "OVERLAP.txt", "w", encoding="utf-8") as o:
            o.write(f"A: {fa.name}  ({la} lines)\n")
            o.write(f"B: {fb.name}  ({lb} lines)\n")
            o.write(f"A contained in B: {ci*100:.1f}%\n")
            o.write(f"B contained in A: {cj*100:.1f}%\n\n")
            # Print first 10 lines of A and which are present in B
            o.write("A lines (with 'Y' if found in B)\n")
            data_a = json.loads(fa.read_text(encoding="utf-8"))
            data_b = json.loads(fb.read_text(encoding="utf-8"))
            lb_lines = set(lines_of(data_b))
            for line in data_a.get("body", []):
                t = normalize(line.get("text", ""))
                if not t or len(t) < 3:
                    continue
                marker = "Y" if t in lb_lines else "."
                o.write(f"  [{marker}] {line.get('text','')}\n")

    print(f"Pairs flagged: {len(pairs)}")
    print(f"Manifest: {md}")
    print(f"Folders:  {pairs_dir}")
    print()
    print("Top 20 pairs (sorted by max-containment):")
    for fa, fb, ci, cj, la, lb in pairs_sorted[:20]:
        data_a = json.loads(fa.read_text(encoding="utf-8"))
        title = data_a.get("title", "")
        print(f"  A→B={ci*100:3.0f}%  B→A={cj*100:3.0f}%  ({la}/{lb} lines)  {title}  | {fa.name}  vs  {fb.name}")


if __name__ == "__main__":
    main()