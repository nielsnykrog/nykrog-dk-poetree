"""Apply the duplicate/containment deletion plan.

Reads review_duplicates/PLAN.md, deletes each 'Delete' file, leaves 'Keep' files alone.
Dedupes the delete list (a file flagged via multiple paths is deleted once).
Writes a deletion_log.txt appending to existing log.
"""
import re, json, shutil
from pathlib import Path
from collections import Counter
from datetime import datetime

ROOT = Path(__file__).parent.parent
PLAN = ROOT / "review_duplicates" / "PLAN.md"
POEMS = ROOT / "poems"
LOG = ROOT / "deletion_log.txt"
SCRAPE_LOG = ROOT / "scrape_log.txt"


def parse_plan():
    files = []
    reasons = {}
    with open(PLAN, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("|"):
                continue
            if "Reason" in line and "Delete" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue
            reason = parts[1].strip()
            delf = parts[2].strip().strip("`")
            keep = parts[3].strip().strip("`")
            if not (delf.endswith(".json") and keep.endswith(".json")):
                continue
            files.append((reason, delf, keep))
            reasons.setdefault(delf, []).append(reason)
    return files


def main():
    plan = parse_plan()
    file_counts = Counter(f for _, f, _ in plan)
    dups = {f for f, n in file_counts.items() if n > 1}
    if dups:
        print(f"Note: {len(dups)} files appear in multiple pairs (deleted once):")
        for f in dups:
            print(f"  - {f} ({file_counts[f]}x)")
    print()

    deleted = []
    missing = []
    for reason, delf, keep in plan:
        target = POEMS / delf
        if target.exists():
            target.unlink()
            deleted.append(delf)
        else:
            missing.append(delf)
    deleted = sorted(set(deleted))  # dedupe

    print(f"Plan pairs: {len(plan)}")
    print(f"Unique files deleted: {len(deleted)}")
    print(f"Already missing:       {len(missing)}")
    print()

    # Verify nothing we should keep was lost
    print("Remaining poems:")
    remaining = list(POEMS.glob("*.json"))
    print(f"  {len(remaining)} files in poems/")

    # Write deletion log (append mode)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as log_f:
        log_f.write(f"\n\n## Duplicate / containment cleanup — {ts}\n\n")
        log_f.write(f"Removed {len(deleted)} duplicate / contained-in-other files.\n")
        log_f.write(f"Source: review_duplicates/PLAN.md ({len(plan)} pairs, {len(dups)} files in multiple pairs).\n\n")
        log_f.write(f"Files deleted:\n\n")
        for fname in deleted:
            log_f.write(f"- `{fname}`\n")
        if missing:
            log_f.write(f"\nNoted as already-missing (no-op):\n\n")
            for m in missing:
                log_f.write(f"- `{m}`\n")

    # Append to scrape_log
    if SCRAPE_LOG.exists():
        with open(SCRAPE_LOG, "a", encoding="utf-8") as slog_f:
            slog_f.write(f"\n[{ts}] Duplicate cleanup: removed {len(deleted)} files (contained-in-other or exact duplicates); see deletion_log.txt\n")

    print(f"Log appended to: {LOG}")
    print(f"Scrape log updated.")


if __name__ == "__main__":
    main()