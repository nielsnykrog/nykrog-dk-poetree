# Source #2 — early-danish-ballads: Decisions Report

Source: UCPH, https://cst.dk/dighumlab/duds/DFK/Dorthe/html/
Author convention: anonymous (all 9 manuscripts, no exceptions)
Output: 936 PoeTree JSONs, 79,970 lines, 0 schema errors, 0 leakage of any kind

## Parser (v6.2 frozen)

1. **Stanza IDs are zero-based and contiguous 0..N-1.** The PoeTree schema is explicit (line 114); the v5b pilot used 1-indexed, which was wrong. If a stanza is purely decorative (only `*`, `* * *`, etc.) and gets dropped, the remaining stanzas compress down — no gaps.
2. **A line whose post-strip content is purely the decorative set `{*, |, :, (, ), ?, !, [, ], <, >}` is dropped.** Letters, digits, and dashes are always preserved (dashes have pre-modernist uses as emphasis). Mid-line sigils stay. Pragmatic rule: dataset serves analysis, not manuscript facsimile.
3. **Three stanza-marker HTML forms are accepted** (not just one): `<br/>[N]` (most common), `<br/>N</td>` (bare number), `<br/>N.</td>` (Dronning Sophia's form with trailing period). Tooltips allowed after each.
4. **Editorial letter/word insertions** (`<e>`, `<Biørnn>`, `<brude-bench>`, `<smaadreng>`) are stripped to their letters. Regex widened to `{1,15}` chars, internal hyphens allowed (Svaning I/II needed this; Langebek didn't). Run both before AND after `html.unescape()` because entities like `&#x3C;` only become literal `<` after unescape.
5. **Manuscript-end markers** (a small known-variants list, case-insensitive): `FINIS`, `FENIS`. Each stripped as a whole word. Add new variants to the list — the list is the audit surface.
6. **Karen Brahes has unclosed `<kommentar>` tags** that close via `</span></div>` instead of `</kommentar>`. Strip `<kommentar ...>` plus content up to the next `</span></div>`. Per-source fix; another manuscript may use a different keyword.

## Data conventions (project-wide)

- `source.publisher` = `null` for all 9 manuscripts. Manuscript-writer attribution isn't meaningful for this corpus.
- `source.url` carries the poem-page URL; for source-pid duplicates in the index (e.g. `DRSXV.htm` listed twice) the parser maps each index entry to the URL where the poem actually lives, not the URL the index claims. Where the index URL is wrong, the wrong URL is preserved in the file (audit trail) and the parser-output URL reflects the actual body source.
- Cross-manuscript duplicates (same ballad in 2+ manuscripts) are **preserved as separate witnesses** — your rule #4a, 198 titles affected.
- Filename collisions (same title appearing 2+ times in one manuscript) get `--2`, `--3` suffix. Distinct from cross-ms witnesses.
- Author is `anonymous` (no brackets) in both filename and JSON — PoeTree uses `[anonymous]` but we deviated for filename readability.

## Workflow (locked in for future sources)

- **Pilots go ONLY to `sources/<id>/pilot/<ms>/`** — never canonical `poems/`. The full scrape re-emits into canonical and the pilot copies become redundant duplicates. Phase 5 quarantines them.
- **Quarantine, don't delete**, in any cleanup pass. You always want a recoverable copy.
- **Lossy rules need explicit sign-off.** Automatic rules (strip markup, unescape entities) are fine without asking. Rules that drop lines, words, or merge/rename files need your confirmation.
- **Pre-scale pilot coverage audit** (`pre-scale-pilot-coverage` skill) runs before scaling. Lists what date/stanza/edge-case variants the pilot exercises vs. what the full corpus might contain. Surfaces known risks; doesn't block scaling.

## Known caveats (not bugs, but documented)

- **DRS index claims 118 entries but only 117 unique URLs.** `DRSXV.htm` is listed under both "Bejlekunsten" (nr XV) and "I Guds hænder" (nr XI). Only Bejlekunsten actually lives at DRSXV.htm; I Guds händer is at DRSXI.htm (Swedish-influenced Lutheran devotional, 104 lines). Upstream catalogue bug.
- **Corpus is overwhelmingly Danish** (~76 Latin tokens across 936 poems, 0.016%; mostly loanwords like `Amen`, `Christus`). No Phase 4 language-review pass needed. One Swedish-influenced poem (I Guds händer at DRSXI.htm) — keep as-is, the orthography is the scholarly point.
- **12 pilot redundant scrapes** quarantined to `sources/early-danish-ballads/pilot_redundant_quarantine/` with `QUARANTINE_LOG.md`. Not deleted.