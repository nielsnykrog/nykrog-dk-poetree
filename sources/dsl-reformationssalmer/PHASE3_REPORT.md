# Phase 3 Report — DSL full scrape

**Status:** complete
**Date:** 2026-07-01
**Source:** `sources/dsl-reformationssalmer/`

## Result

**1,096 poem JSON files** written to `poems/`, all passing `scripts/validate.py` with 0 errors, 0 warnings.

| Book | Poems | Stanzas | Verse-lines | With marginal notes |
|---|---:|---:|---:|---:|
| Dietz 1529 | 87 | 973 | 5,257 | 583 |
| Malmoe 1533 | 138 | 1,707 | 8,810 | 607 |
| Dietz 1536 | 36 | 209 | 1,232 | 0 |
| Vingaard 1553 | 212 | 2,599 | 13,870 | 0 |
| Thomissøn 1569 | 298 | 4,188 | 27,086 | 6 |
| Claus Mortensen 1529 (messe) | 13 | 60 | 319 | 32 |
| Oluf Ulriksen 1535 (messe) | 9 | 26 | 256 | 0 |
| Oluf Ulriksen 1539 (messe-haandbog) | 29 | 156 | 878 | 0 |
| Jespersen 1573 | 274 | 1,294 | 7,652 | 0 |
| **Total** | **1,096** | **11,212** | **65,360** | **1,228** |

## Sanity checks (passed)

- ✅ `python scripts/validate.py poems/` → 1096 files, 0 errors, 0 warnings
- ✅ Per-book counts match discovery data
- ✅ 0 file parse failures
- ✅ No suspicious patterns (page-break sigils, daggers) found in any body text
- ✅ Title == first verse line for every poem (manual check on a sample; all 1,096 verified by automated check)
- ✅ Line ids 0..N-1, stanza ids non-decreasing

## Filename collisions

**207 filenames collided** (two pages in the same book produce the same slug from the same first-verse-line) and were disambiguated with a `--N` suffix:
- Largest collision group: 50+ pages all titled "HAleluia." across Jespersen 1573 (each is a separate antiphon at a different position in the liturgical year — distinct poems, just same opening word)
- Other notable collisions: "Kyrie eleison" appears across many books (same Latin formula), "O Gud aff hiemmelen see her til" (Psalm 12) appears in multiple books

Total files: 1,096 (889 unique-slug + 207 collision-suffixed = 1,096 ✓)

## Field policy applied (per our agreement)

- ✅ `author.name = "anonymous"` (no brackets)
- ✅ `year_created = source.year_published` for all 1,096 poems
- ✅ `source.corpus = "Danske Reformationssalmer (Dansk Sprog- og Litteraturselskab)"`
- ✅ `source.title`, `source.publisher`, `source.printer`, `source.place` from colophon for each book
- ✅ `source.url` per poem (the page URL)
- ✅ `body[].marginal_notes[]` extracted (only Dietz 1529, Malmoe 1533, Thomissøn 1569, Claus Mortensen 1529 had marginal notes — DSL convention)
- ✅ Page-break sigils, †-apparatus stripped
- ✅ Original 16th-c. orthography preserved
- ✅ Filenames: `<source-id>--<author-slug>--<poem-title-slug>--<book-slug>.json` (with `--N` suffix on collisions)

## What I did NOT do (and why)

- **No re-validation of marginal-note extraction at scale.** Pilot-only check. The 1,228 lines with marginal notes were extracted by the same logic that passed for the pilot's 17 lines, but I didn't read every one.
- **No language detection on the 9 books.** All books have some Latin material (antiphons, kyries). Latin poems will have the same orthography-preservation treatment as Danish ones. If you want Latin to be handled differently (e.g. different `author.country`, or skip Latin entirely), say so and I'll re-process.
- **No deduplication across books.** A poem like "I JHesu naffn begynde wÿ" appears in Dietz 1529, Malmoe 1533, Vingaard 1553, and possibly others. They are correctly written as separate files because they ARE separate editions of the same text. PoeTree's `duplicate` field is left `false` for the pipeline to handle.

## Open questions for PoeTree (still pending)

- Whether to keep `source.printer` (our local extension)
- Whether to keep `body[].marginal_notes[]` per verse-line (our local extension)
- Whether to use `id` field for cross-source identification (PoeTree may assign)

## Next step

When you're ready, the dataset is complete for DSL. You can:

1. **Hand it off to PoeTree** as-is, with a note about the local extensions
2. **Spot-check more poems** — read a few random files in `poems/`
3. **Move to the next source** (Tekstnet, Kalliope, or whatever's next on your list)
4. **Add data augmentation** (e.g. modernise orthography, lemmatise, etc.) — but you said this was less important