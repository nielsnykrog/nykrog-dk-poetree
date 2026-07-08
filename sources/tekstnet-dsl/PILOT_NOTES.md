# Source #3 — tekstnet-dsl: Pilot Notes

**Date:** 2026-07-03
**Parser version:** v3 (pilot)
**Status:** awaiting user sign-off before scaling to full corpus (~670 unique slugs)

## Pilot coverage

9 poems across 4 body variants, plus 1 correctly excluded negative test (Latin):

| # | Slug | Variant | Lines | Notes |
|---|---|---|---|---|
| 1 | `andersen-hc_af-samlede-skrifter-femtende-bind/001/` | A (multi-poem, regular verse) | 20 | 1st sibling, 5 stanzas × 4 lines |
| 2 | `andersen-hc_af-samlede-skrifter-femtende-bind/002/` | A (2nd sibling) | 32 | Sibling for "≥3 verse siblings" check |
| 3 | `andersen-hc_af-samlede-skrifter-femtende-bind/003/` | A (3rd sibling) | 30 | Third sibling |
| 4 | `heiberg-jl_nye-digte/001/` | A + drama (short) | 354 | 22 speakers, mapped per-stanza |
| 5 | `heiberg-jl_nye-digte/002/` | A + drama (long) | 1649 | 262 speakers; maxes the parser |
| 6 | `munch-petersen-g_mod-jerusalem/002/` | A + prose-as-poem | 6 | Single `<p>` body × 6 paragraphs |
| 7 | `andersen-hc_1862/` | B (single-poem) | 12 | Body on book-index page; 3 stanzas × 4 lines |
| 8 | `anon_tro-haab-og-kaerlighed/` | B + partial Latin | 34 | Mixed Danish/Latin; labelled `dansk` |
| 9 | `anon_dyrerim_dipl/` | `_dipl`-only (no normalised) | 3506 | Diplomatic edition; 170 stanzas |
| - | `brahe-t_henrico-ranzovio/001/` | **EXCLUDED** | - | `Sprog=latin` → filtered out |

**Validation:** 6 per-book subdirectories, 8 files total, 0 schema errors, 1 warning (the `diplomatic_edition` field is unknown to the validator — it's Source #3 metadata, not a problem).

## Parser design (v3, frozen at end of pilot)

### URL handling

- `source.url` is the **poem-specific URL**, not the publication URL.
- For multi-poem books: `https://tekstnet.dk/books/<slug>/NNN/`
- For single-poem books (Variant B): `https://tekstnet.dk/books/<slug>/` (the book-index page IS the poem)

### `source.title`

Derived from the book slug by stripping the author prefix: `<author>_<title>` → `title`. Examples:
- `andersen-hc_af-samlede-skrifter-femtende-bind` → `Af Samlede Skrifter Femtende Bind`
- `heiberg-jl_nye-digte` → `Nye Digte`
- `anon_dyrerim_dipl` → `Dyrerim Dipl`
- `munch-petersen-g_mod-jerusalem` → `Mod Jerusalem`

### `source.publisher`

Always `null`. Tekstnet's `Udgiver` field is the digital-edition editor (often a 21st-century literary historian), not the historical publisher. Per user rule 2026-07-03, we leave this empty for now and may augment later with correct historical publisher data.

### `source.year_published`

Inherited from the book's `Udgivelsesår` field. Most books have a single year; multi-year ranges are rare in this corpus.

### Author extraction

For non-anonymous works, the slug is `lastname-initials_title` (e.g. `andersen-hc_1862` → `H.C. Andersen`; `heiberg-jl_nye-digte` → `J.L. Heiberg`). The parser extracts lastname + initials from the slug prefix.

### Title extraction

Title source priority:
1. `<title>` HTML tag — parsed as `Author: Title fra Book (year)` or `Author: »Title« fra Book (year)` or just `Title`
2. `<h1>` fallback (the last non-section-header h1 inside text-container)
3. URL slug fallback (stripping `anon_` prefix)

`Nr. N.` prefix is stripped from h1 titles. The h1 fallback also skips obvious section headers like `I.`, `II.`, `Nr. 1.`, `Bog 1.`, etc.

### Edition-suffix handling

- `<work_id>` (normalised) → include
- `<work_id>_dipl` → include only if no `<work_id>` exists; mark `Diplomatic Edition: true` in the JSON
- `<work_id>.da` (modern Danish translation) → always exclude

### Language filter

Include if the book's `Sprog` link target is one of:
- `dansk` (catch-all, also used for partial-Latin works)
- `gammeldansk` (Old Danish)
- `ældre-nydansk` (Older New Danish)
- `yngre-nydansk` (Younger New Danish)

Exclude: `latin`, `engelsk`, `fransk`, `tysk`, anything else.

### Stanza structure (key user rule, 2026-07-03)

The parser counts `<div class="mt-3 mb-4">` wrappers and assigns `stanza_id` 0, 1, 2, ... per stanza. **Verified against `andersen-hc_1862`** (3 stanzas × 4 lines each, stanza_id 0/1/2 matching the user's example).

Stanza-aware extraction also applies to drama (the same `<div class="mt-3 mb-4">` wrapper is used).

### Drama speaker labels (per-stanza mapping)

Speaker labels (`<p class=drama-speaker>`) are mapped to the **stanza in which they appear** (not just line 0 as in v2). Within each stanza, the speaker label attaches to the **first line of that stanza** in the `body[].marginal_notes` field. This is a per-stanza pattern: a speaker change in the middle of a long drama creates a new stanza_id and the new speaker attaches to that stanza's first line.

**Speaker labels are cleaned**: leading page-number prefixes like `[3] |` or `32 |` are stripped (they're apparatus, not part of the character name).

**Critical structural insight**: speakers can appear in TWO locations:
1. **Before the first stanza wrapper** — `<div class=drama><p class=drama-speaker>...</p><div class="mt-3 mb-4">...` — these are preamble speakers that should be assigned to stanza 0
2. **Between stanzas** — `</div><p class=drama-speaker>...</p><div class="mt-3 mb-4">...` — these should be assigned to the NEXT stanza

The naive approach (only look inside the stanza wrapper) misses the preamble speaker. The parser walks the HTML in document order, tracking a running stanza_id, so speakers outside stanza wrappers get correctly assigned to the appropriate stanza.

**Verification**: for `heiberg-jl_nye-digte/002/` (En Sjæl efter Døden):
- Stanza 0: `Chor af de Efterlevende` → "En værdig Mand er død! I kraftig Alder..." ✓
- Stanza 1: `Sjælen` → "Hvad plager dog mig Stakkel..." ✓

**Schema limitation**: only the FIRST speaker per stanza is stored in `marginal_notes` (since the schema has a flat list per stanza). If a stanza has multiple speakers (e.g. Chor speaks first, then Sjælen responds within the same wrapper), only the primary speaker is captured. This is rare in the corpus but does happen.

**Annotation convention** (user rule, 2026-07-03): speaker labels in `body[].marginal_notes` are prefixed with `"Speaker: "` so the role is unambiguous to downstream consumers. Future parser writers should treat `"Speaker: ..."` as a reserved prefix. A top-level `"dramatic_poem": true` field is also set on the JSON for easy filtering.

### Single-line filter

Lines (not prose) with only 1 line in the body are excluded — too likely to be apparatus misidentified as a poem. Prose-as-poem is NOT filtered by this rule (single-paragraph prose is a legitimate modernist form).

### Book-level filter for prose-as-poem

A book with < 3 sibling line/drama poems is treated as a non-poetry book (e.g. a novel) and excluded entirely. This catches cases like `anon_jon-praest-ghemen` (8 sibling poems, all prose — clearly an essay/prose-collection, not a poetry collection). The filter is applied at the full-scrape level, not the per-poem parser.

### Metadata inheritance

Per book:
- `author` → inherited from publication's `Forfatter`
- `source.title` → derived from book slug (author prefix stripped)
- `source.year_published` → inherited from publication's `Udgivelsesår`
- `title` (poem) → per-poem (from `<title>` tag or h1)
- `year_created` (poem) → per-poem (set from book's `Udgivelsesår` for now)

For single-poem books (Variant B), the book's metadata block IS the poem's metadata — no propagation needed.

### Depth-counting line extraction

Line content can contain nested `<div>`, `<button>`, etc. (e.g. footnote popover buttons with their own `<div class='arrow'>`). A naive non-greedy `.*?</div>` regex breaks on this. The parser uses a **depth-counting** `find_matching_close` function that:

1. Skips `<div` matches that are part of longer tag names like `<dialog` (char after `<` is a letter)
2. Skips `</div>` matches that are part of longer tag names like `</dialog` (char after `</` is a letter)
3. Counts opening and closing tags to find the true matching close

This handles the heiberg_002 case correctly (1649 drama lines extracted without the regex truncating on nested divs).

## Known caveats (locked in for scaling)

- **Title pollution for poems 002/003 of `andersen-hc_af-samlede-skrifter-femtende-bind`:** the `<title>` is `H.C. Andersen: Af. Samlede Skrifter. Femtende Bind, ` (trailing space, no poem title) — Tekstnet didn't fill in the per-poem title for these. The h1 returns `III.` (a Roman numeral section header). The parser falls through to the title-as-extracted, which is the book title. **Decision**: accept the imperfect title; the user can manually correct later. This is a Tekstnet data quality issue documented in `observations-on-source-quality.md`.

- **Title `1862` for `andersen-hc_1862_B`:** Tekstnet uses the year as a placeholder title for unnamed poems. Not ideal but the only option.

- **Drama-line fallback if no speaker:** heiberg_001 and heiberg_002 have speakers; the rule "attach speakers to first line of each stanza" works for these. If a drama has a speaker label that doesn't appear in front of any line, it'll be lost.

- **Munch-Petersen prose poem (6 lines):** the body has 6 `<p>` paragraphs. The user asked whether it should be a single line; my parser keeps 6 separate lines (one per `<p>`). Decision pending if you want to collapse.

## Source-quality observations

See `observations-on-source-quality.md` for a detailed list of Tekstnet's data-quality and editorial-publication-practice issues (9 specific items, with concrete examples and suggestions to share with the Tekstnet editors).

## What I want from you before scaling

1. **Approve or revise the rules** above.
2. **Decide on the Munch-Petersen prose handling**: keep 6 lines (one per `<p>`) or collapse to 1 line (whole body as one entry)?
3. **Anything I missed?**

If you sign off, Phase 3 (full scrape) will:
- Walk the 6 genre category pages (Digt, Digte, Digtsamling, Poesi, Religion, Salmebog) to get the per-genre slug lists
- For each unique base work id (~670 across genres), decide normalised / `_dipl` / `.da` according to the rules
- Apply the book-level filter: a book with < 3 sibling line/drama poems is excluded
- Fetch + cache + parse the poem pages (~1500 estimated)
- Write JSONs to `poems/` (NOT `pilot/`)
- Phase 3b: author Wiki ID augmentation pass (post-scrape)
- Phase 4: redundant-scrape check + audit
