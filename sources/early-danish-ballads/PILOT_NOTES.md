# Langebeks Kvart — Pilot Notes

## Date
2026-07-02

## Source
- Manuscript: Langebeks Kvart (Nks. 816,4º)
- Corpus: Den ældste danske viseoverlevering (University of Copenhagen)
- Pilot scope: 106 poems, all in raw cache
- Index page: https://cst.dk/dighumlab/duds/DFK/Dorthe/html/Langebek.htm

## Dates seen
Only 4 date ranges, all list-form:
- 1560-1562 (34 poems)
- 1570-1573 (30 poems)
- 1579-1583 (39 poems)
- 1593-1596 (3 poems)

**Date rule coverage in this pilot**: only the `A-B` range rule fired. `Før N`/`Efter N`/`N'erne` rules NOT exercised; will need verification on other manuscripts.

## HTML structure
- Page wraps metadata + a single `<table>` of poem rows
- Each row is one of:
  1. Empty `<br/>` row — page-break sigil, drop silently
  2. Stanza-number row — `<br/>[N]` or `<br/>N` — increment stanza_id
  3. Line row — 2 `<td>` cols; first col `<span class="source">` keeps our text, second col `<span class="neutral">` is the editor's modernisation (drop entirely)
- Refrains marked with literal `:: ... ::` sigils in the source span; refrains stay *inline* in host stanza (no separate stanza)

## Cleaning rules (locked, in order)
1. Drop `<sup>...</sup>` (footnote markers, always inside apparatus)
2. Loop-strip `<div class="tooltip">...</div>` and orphan `<span class="tooltiptext">...</span>`/`<span class="tooltip">...</span>`
3. Strip `<em>...</em>` markup, keep inner letters (italic letter shapes, no semantic content for tokenisation)
4. Drop `<span class="layout">[sideskift]</span>` (manuscript page-end markers)
5. Drop literal word `FINIS`
6. Replace `[-]` with `-` (R4: editor's compound-hyphen marker, keep the hyphen)
7. `<[letter]{1,5}>` → `letter` (R2: editorial letter-insertion, broader than single letter)
8. `[(content)]` → `content` (R1: editorial brackets around supplied word/phrase)
9. Collapse whitespace; trim
10. Decode HTML entities

## Things the parser explicitly PRESERVES
- Original orthography (no modernisation): `wunde`, `kieriste`, `hannom`, `siide`, etc.
- Compound hyphens (e.g. `aller-kieriste`, `sønnen gud`, `ther-vdi`, `Gud-Fader`) — these are real 16th-c orthography, not editor markup
- Manuscript `|` mid-line sigils — these are the editor's preserved line-break marks
- Refrain `:: ... ::` sigils — preserved exactly
- Stanza numbers from manuscript (when in `[N]` brackets) — number used for stanza detection, not text

## Things the parser explicitly DROPS
- `<span class="neutral">` (modernised version column)
- Tooltip apparatus (footnotes, "Orddeling ved linjeskift", "Sic udg.")
- Page-break sigils (`[sideskift]`, `FINIS`)
- Title's outer parens when title is parenthesised in source

## Mojibake handling
Server declares `charset=utf-8` but rendering is double-encoded (UTF-8 bytes interpreted as Latin-1). All raw HTML is fixed on read by `.encode("latin-1").decode("utf-8")` — produces correct characters before any further processing.

## Filename handling
- Pattern: `early-danish-ballads--anonymous--<poem-title-slug>--langebeks-kvart.json`
- 4-part, double-dash separator
- Slug: NFKD-decompose, drop combining marks, lowercase, whitespace→`-`, strip punctuation, max 80 chars
- Title-slug collision handling: append `--2`, `--3`, ...
- Pilot yielded 1 collision (LNGK135 vs LNGK50, both titled "I fryden vil jeg leve en stund"), correctly disambiguated

## Known corpus edge cases (Langebek-specific)
- LNGK62A line 0 is a single `*` (manuscript decorative asterisk before stanza 1) — kept as s0
- Refrains appear with high frequency: 237 refrain lines across 25 poems (24% of corpus)
- Longest poem: 88 stanzas (very long ballad)
- Shortest: 1 stanza

## Open questions for scaling
1. Manuscript writer / source.publisher — Langebek Kvart's writer unknown; awaiting user's input
2. Date-rule verification on other manuscripts (need `Før N`, `Efter N`, `N'erne` exercise)
3. Variant identifier in filename? E.g. `LNGK62A` vs `LNGK62B` — same title, different witness — currently distinguished by full filename collision suffix only. Question: do we want to include the manuscript's own `nr_in_hs` in filenames?

## Audit samples
7 pilot JSONs are in `sources/early-danish-ballads/pilot/langebeks-kvart/`. Cover:
- LNGK1 — long ballad with 5 refrains
- LNGK14 — many compound-hyphen examples
- LNGK15 — many `[word]` editorial bracket examples (now stripped)
- LNGK43 — many `<letter>` editorial letter-insertion examples (now stripped)
- LNGK50 — collision case (becomes `--2`)
- LNGK62A — many `<letter>` examples + decorative asterisk
- LNGK93 — no refrains, single sigil vocabulary

All 7 are written and readable end-to-end.
