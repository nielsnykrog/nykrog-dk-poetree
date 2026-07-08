# Source #2 early-danish-ballads — Session Handoff

**Date:** 2026-07-02 (session ended before scaling)
**Resume tomorrow by:** open a chat and say "Pick up Source #2 early-danish-ballads" — the assistant will read this file.

---

## Where we are

Source #1 (DSL Reformationssalmer) was completed in a prior session (782 final poems).
Source #2 (early-danish-ballads) — 2 of 9 manuscripts piloted, awaiting user review.

Phase 1 done:
- All 9 manuscript index pages fetched and parsed (118 DRS + 106 LNGK + 7 others)
- Langebeks Kvart: 106 poems parsed with v6, 7 audit JSONs written
- Dronning Sophias visebog: 5 poems parsed with v6, covering every date form (`Før N`, `Efter N`, `N'erne`, bare year)
- Parser v6 frozen 2026-07-03 (zero-based stanza_id, lone-sigil line drop broadened to punctuation set)

Phase 2 awaiting user:
- DRS pilot JSONs (5) — sign-off or revisions
- Confirmation to scale v6 to the remaining 7 manuscripts

## Phase 5 — done 2026-07-03

Redundant-scrap pass found 12 pilot files that leaked into `poems/` from
the v6 pilot re-emit (mtime 10:51–10:52). The full scrape (mtime 11:05)
re-emitted identical copies with different filenames, leaving the older
files as redundant duplicates. All 12 quarantined (not deleted) to
`sources/early-danish-ballads/pilot_redundant_quarantine/` with
`QUARANTINE_LOG.md`. The canonical `poems/` directory now has **936 files** —
exactly one per unique source URL, with no in-corpus duplicates.

**DRSXV/DRSXI clarification**: the DRS index lists 118 entries but only
117 unique URLs (DRSXV.htm is listed under both "Bejlekunsten" nr XV and
"I Guds händer" nr XI). I Guds händer actually lives at DRSXI.htm — the
index metadata for nr XI is wrong. The parser correctly mapped each entry
to its actual URL, producing 117 distinct DRS files. Flagged as an
upstream catalogue bug.

**General redundant-scrape check** across all 936 files confirms no other
intra-ms pairs with ≥90% line-set containment. Cross-ms duplicates (198
titles) are expected per rule #4a (each witness distinct).

---

## What's on disk

```
C:\Users\niels\Documents\nykrog-dk-poetry\sources\early-danish-ballads\
├── PILOT_NOTES.md                  ← parser rules, edge cases, manifest
├── PROGRESS.md                      ← running progress
├── SESSION_HANDOFF.md              ← THIS FILE (read first on resume)
├── parser.py                        ← v5b, FROZEN
├── index\
│   ├── hjertebogen.html + _parsed.json (not yet used)
│   ├── jens-billes-haandskrift.html + _parsed.json
│   ├── langebeks-kvart.html + _parsed.json  ← USED IN PILOT
│   ├── karen-brahes-folio-aeldre-del.html
│   ├── dronning-sophias-visebog.html
│   ├── anna-munks-haandskrift.html
│   ├── rentzells-haandskrift.html
│   ├── svanings-haandskrift-i.html
│   └── svanings-haandskrift-ii.html
├── raw\
│   └── langebeks-kvart\         ← 106 raw HTML files
└── pilot\
    └── langebeks-kvart\         ← 7 audit JSONs (READ THESE)
        ├── early-danish-ballads--anonymous--elsker-dræbt-af-broder--langebeks-kvart.json
        ├── early-danish-ballads--anonymous--linden-paa-lindebjærg--langebeks-kvart.json
        ├── early-danish-ballads--anonymous--den-listige-kæreste--langebeks-kvart.json
        ├── early-danish-ballads--anonymous--kærestens-død--langebeks-kvart.json
        ├── early-danish-ballads--anonymous--i-fryden-vil-jeg-leve-en-stund--langebeks-kvart--2.json
        ├── early-danish-ballads--anonymous--tro-som-guld--langebeks-kvart--3.json
        └── early-danish-ballads--anonymous--mit-barn-frygt-den-sande-gud--langebeks-kvart.json
```

Also at `_parse_tmp_langebek.json` (in source root) — full 106-poem parse output, all fields.

---

## Locked schema/filenaming (DO NOT change without user)

- **Filename**: `early-danish-ballads--anonymous--<poem-title-slug>--<manuscript-slug>.json` (4-part double-dash)
- **Slugs**: NFKD, drop combining marks, lowercase, whitespace→`-`, strip punctuation, max 80 chars
- **Manuscript slugs used so far**: `langebeks-kvart`. The 8 others need slugs as we go.
- **Author**: `"anonymous"` (no brackets) in both filename and JSON
- **Unknown**: `source.publisher` currently `null` for all 7 (waiting on user info)
- **`source.corpus`**: `"Den ældste danske viseoverlevering (University of Copenhagen)"` (single value)

---

## Cleaning rules — locked at v6

1. Strip `<sup>...</sup>`
2. Loop-strip `<div class="tooltip">...</div>` + orphan `<span class="tooltiptext|tooltip">...</span>`
3. Strip `<em>...</em>`, keep inner letters
4. Strip `<span class="layout">...</span>` (manuscript page-end markers)
5. Drop word `FINIS` (manuscript-end marker)
6. `[-]` → `-` (R4: keep editorial compound-hyphen)
7. `<[letter]{1,5}>` → `letter` (R2: editorial letter-insertion)
8. `[(content)]` → `content` (R1: editorial bracket around supplied word)
9. Whitespace collapse + trim
10. **unescape entities, then re-run R2 + R1** (bug fixed: entities like `&#x3C;` were escaping earlier)
11. **Drop a line whose post-strip content is only the decorative set `{*, |, :, (, ), ?, !, [, ], <, >}`** (v6, 2026-07-03). Letters, digits, dashes always preserved.
12. **Renumber stanza_ids contiguously 0..N-1** after all parsing (v6).

**Preserved**: original orthography, manuscript `|` line-break sigils, `::` refrain sigils, compound hyphens (e.g. `aller-kieriste`, `Gud-Fader`).

**Stanza-id semantics (v6)**: zero-based, contiguous 0..N-1. If the source had a decorative stanza at the start that got dropped (e.g. LNGK62A's `[*]` row), remaining stanzas compress down — no gaps.

---

## Title handling — locked

- Real titles without parens: kept as-is
- Parenthesised titles like `(Flere venner end en at have)`: drop outer parens, keep inner text
- These dropped-paren titles are used as-is for filename slugs

---

## Refrains — locked

No `is_refrain` field. Refrain lines stay *inline* in their host stanza. `::` sigils preserved.

---

## Date rules — locked

| Source string | year_created | source.year_published |
|---|---|---|
| `1589` (bare int) | `1589` (int) | `1589` |
| `Før 1555`, `Efter 1598` | `1555`/`1598` (int) | same |
| `1575-1590`, `1634-1638` | `[1575,1590]` (list) | `1590` (last) |
| `1630'erne` | `[1630,1639]` (list) | `1639` |
| empty / malformed | `null` | `null` |

Langebek pilot only exercised the `A-B` range form. **The `Før N`, `Efter N`, `N'erne` rules are coded but not yet tested with real data** — will need verification on a sample from at least one other manuscript before scaling.

---

## 7 Audit POEM samples (READ THESE on resume)

These show every cleaning rule in action:

1. **LNGK1** `elsker-dræbt-af-broder` — long ballad, 5 refrains spread inline, `::` preserved
2. **LNGK14** `linden-paa-lindebjærg` — longest in pilot (82 lines), many compound-hyphens
3. **LNGK15** `den-listige-kæreste` — many `[word]` editorial brackets now stripped
4. **LNGK43** `kærestens-død` — many `<letter>` editorial insertions now stripped to `welde were`, `efftter meg` etc.
5. **LNGK50** `i-fryden-vil-jeg-leve-en-stund--2` — collision with LNGK135, demonstrates `--2` suffix
6. **LNGK62A** `tro-som-guld--3` — more `<letter>` inserts + a decorative `*` at s0
7. **LNGK93** `mit-barn-frygt-den-sande-gud` — Lutheran catechism, no refrains, `|` sigils preserved

**Audit pass post-v5b-fix**: 0 tag-leakage, 0 bracket-leakage, 0 `[-]`-leakage, 0 entity-leakage across all 106.

---

## Open questions for the user on resume

1. **Approve cleaning rules?** Read the 7 pilot JSONs. Are there cases where rules didn't do what you expected? Want anything changed/stripped/preserved differently?
2. **Manuscript writers?** Per-poem `source.publisher` (or per-manuscript, applied to all poems in that manuscript). You mentioned you'd give me this info — ready to share now or after you've reviewed the pilot?
3. **Confirm scale to 8 remaining manuscripts?** Once approved, will run on hjertebogen, jens-billes-haandskrift, karen-brahes-folio-aeldre-del, dronning-sophias-visebog, anna-munks-haandskrift, rentzells-haandskrift, svanings-haandskrift-i, svanings-haandskrift-ii — and pick manuscript-slugs for each (suggested: lowercase, hyphenated, e.g. `hjertebogen`, `jens-billes-haandskrift`, `karen-brahes-folio-aeldre-del`).

---

## Known caveats for scaling

- Date-rule forms `Før N`, `Efter N`, `N'erne` haven't been seen in raw data yet — code is written but unverified. **Run on a sample of one other manuscript first** to verify all forms.
- Different manuscripts may have different HTML structure quirks. Pilot may need minor parser tweaks.
- Cross-manuscript duplicates of the same ballad title exist (e.g., "Tro som Guld" appears in Langebek 3 times, and likely appears in other manuscripts too). Per user rule #4a, keep each witness distinct (collision-suffix logic).
- `source.publisher` is `null` until manuscript writers provided.

---

## Files to read on resume (in order)

1. `SESSION_HANDOFF.md` (this file)
2. `PILOT_NOTES.md` — detailed parser/cleaning rationale
3. Open all 7 pilot JSONs end-to-end, read each body in full
4. If approved, ask user for manuscript writers + scale confirmation
