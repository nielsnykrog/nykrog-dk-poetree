# Source #3 — Tekstnet: Observations on source quality

**Date:** 2026-07-03
**Status:** user's instruction — these are observations to share with the Tekstnet editors.

## Summary

Tekstnet (https://tekstnet.dk) is a **general archive of Danish literature** maintained by the Society for Danish Language and Literature (DSL). It is comprehensive in scope (medieval to present) but has several data-quality and editorial-publication-practice issues that make it less reliable than the two previous sources (DSL Reformationssalmer, early-danish-ballads/UCPH). Below are the specific issues I observed while building a parser for the corpus.

## Issues observed

### 1. The `Udgiver` field in publication metadata is misleading

Tekstnet's publication metadata block has a field called `Udgiver` (literally "publisher" in Danish) which lists the **editor of the modern digital edition**, not the historical publisher of the original work.

**Concrete example**:
- The book `heiberg-jl_nye-digte` (J.L. Heiberg, *Nye Digte*, 1841) lists `Udgiver: Klaus P. Mortensen` — a 21st-century literary historian.
- The actual historical publisher of *Nye Digte* in 1841 was **C.A. Reitzel** (a major Danish publisher of the 19th century).
- The Tekstnet `Udgiver` field is **not** the publisher in the bibliographic sense. Using it as `source.publisher` in our dataset would propagate false provenance.

**Suggestion to Tekstnet**: rename the field to `Digital udgiver` or `Redaktør af digital udgave` to disambiguate from historical publisher. Or add a separate `Originalforlag` field that captures the historical publisher.

### 2. Author prefix in URL slugs and book titles

Tekstnet URL slugs follow the pattern `<author-lastname>-<initials>_<title>`, e.g. `heiberg-jl_nye-digte`. When a user-facing publication title is derived from the slug (e.g. by replacing hyphens with spaces), the result includes the author prefix: `Heiberg Jl Nye Digte`.

**Concrete example**:
- `<title>` HTML element: `Johan Ludvig Heiberg: Nye Digte 1841, Gudstjeneste` — author and book are clearly separated by `: `, and the poem title `Gudstjeneste` is at the end.
- But derived book title (from slug `heiberg-jl_nye-digte`): `Heiberg Jl Nye Digte` — has the author prefix baked in.

**Suggestion to Tekstnet**: provide a separate metadata field for the human-readable book title that excludes the author prefix.

### 3. The `<title>` HTML element is unreliable for parsing

The `<title>` element follows different patterns across pages:
- Multi-poem book: `H.C. Andersen: Af. Samlede Skrifter. Femtende Bind, Af Nogle Viser` (author: book, poem)
- Single-poem book: `H.C. Andersen: 1862` (author: year) — the year is used as a placeholder title for unnamed poems
- Edition-variant: `Dyrerim (diplomatarisk udgave)` — title with edition marker in parens
- Standalone: `Tro, håb og kærlighed` — no author prefix
- Edge case: `empty: Jon Præst (Ghemen, 1510), ` — `empty:` prefix is an HTML artefact when the title field is empty

The patterns are inconsistent and require multiple regex strategies. For example, `H.C. Andersen: 1862` parses as "title = 1862" but the user probably wants "title = (whatever the 1862 poem is actually about)". The use of the **year as a placeholder** for unnamed poems is a poor convention that loses information.

**Suggestion to Tekstnet**: always provide a structured title field (e.g. `<meta property="og:title">` or a `<b>Titel:</b>` block on the poem page) that has a single canonical form. Avoid putting the year in the title field as a placeholder.

### 4. Source-pid duplicates: same URL, different metadata

Some works are referenced by two different index entries that point to the same URL. **This is a catalogue bug** — it indicates that the index was generated from a list of works that had catalogue errors, with no deduplication step.

**Concrete example**:
- `DRSXV.htm` (Dronning Sophias visebog) is referenced by TWO different index entries:
  - Entry 1: `nr XV`, title `Bejlekunsten`, `Efter 1598`, `Riddervise`
  - Entry 2: `nr XI`, title `I Guds händer`, `1630'erne`, `Svensk vise`
- The HTML page at `DRSXV.htm` contains only one poem. The index claims two different poems live there. The second entry's `Datering` (`1630'erne`) and genre (`Svensk vise`) are wrong for the actual content.

**Suggestion to Tekstnet**: deduplicate the index by `href` and add a note when two entries point to the same page. Better: link each entry to a unique poem when possible.

### 5. Stanza structure is implicit

Tekstnet does not number stanzas explicitly. The stanza boundary is marked by the HTML wrapper `<div class="mt-3 mb-4">`, but no stanza number, letter, or other explicit marker is given. This means a downstream analysis tool cannot tell which stanza is which without parsing the wrapper.

**Concrete example**:
- A poem like H.C. Andersen's `1862` has 3 stanzas of 4 lines each, with the only stanza separator being `<div class="mt-3 mb-4">` wrapping.
- There's no `<span class="stanza-number">1.</span>` or similar markup.

**Suggestion to Tekstnet**: add explicit stanza numbers (`<span class="stanza-number">1.</span>`, `2.`, ...) for accessibility and for downstream analysis. Many other digital edition sites do this.

### 6. Modernist prose-as-poem is structurally identical to prose

Modernist poems (e.g. Gustaf Munch-Petersen's *Mod Jerusalem*, 1934) appear as **single `<p>` blocks with no line breaks** — structurally identical to regular prose. There's no `class="poem"` or `class="verse"` distinguishing them. The only signal is that the page is filed under a poetry genre (e.g. `Digte`).

**Concrete example**:
- Munch-Petersen's poem `1. fra i dag` is one `<p>` block. The body is 6 prose paragraphs in 6 `<p>` elements. There's no markup difference from a page in a novel or essay collection.
- This means a downstream tool that wants to find "all the poems on Tekstnet" can't easily distinguish a poem from a prose paragraph. It has to rely on the book-level genre metadata, which is also sometimes unreliable.

**Suggestion to Tekstnet**: add a structural marker (e.g. `<div class="poem">` or `<article typeof="schema:CreativeWork schema:Poem">`) to distinguish poems from prose passages, even modernist ones. This is critical for accessibility and for machine-readable analysis.

### 7. Footnote / critical-note apparatus is inline in body text

The footnote apparatus (`<button id="AppN">`, `<button id="nN">`) is inline in the body markup. The note's text appears inside `data-content` attributes in the same `<div class=line>` block as the verse line. Extracting just the verse line without the apparatus requires stripping the button. The apparatus is also heavily nested (the button's `data-template` attribute contains its own `<div>` tags), making naive regex extraction break.

**Concrete example**:
- A verse line in H.C. Andersen's poem 1 has structure: `<div class=line>verse text <button id=n1 ... data-content="critical note text" data-template="<div class='popover'...><div class='arrow'></div>...">A</button> rest of verse</div>`
- A naive `<div class=line>(.*?)</div>` regex truncates at the first `</div>` inside the button's data-template.

**Suggestion to Tekstnet**: extract the apparatus into a separate element (e.g. `<aside class="apparatus">` or `<sup class="footnote">`) outside the verse line, so that the verse body can be extracted with a simple regex. This is also better for accessibility.

### 8. The `Forfatter` (author) field is often missing

For anonymous works or works of disputed/uncertain authorship, the `Forfatter` field is absent from the metadata block. The parser falls back to URL-slug parsing (`anon_` prefix → "anonymous"), but this is **lossy**: a work where the author is genuinely unknown cannot be distinguished from a work where Tekstnet forgot to fill in the field.

**Concrete example**:
- `anon_jon-praest-ghemen` has no `Forfatter` field in the publication metadata. It could be:
  - (a) Anonymously authored (the `anon_` prefix is correct)
  - (b) By a known author that Tekstnet hasn't attributed yet

**Suggestion to Tekstnet**: always include a `Forfatter` field, even if the value is "Ukendt" (Unknown) or "Anonym". Distinguishing "unknown" from "absent" matters for bibliometric analysis.

### 9. The general index mixes books with single-poem works

Tekstnet's general `/books/` index lists works of widely different scales:
- Full collections (e.g. `heiberg-jl_nye-digte` has 5 poems)
- Single-poem works (e.g. `andersen-hc_1862` has 1 poem)
- Diplomatic editions (e.g. `anon_dyrerim_dipl` is one 3506-line poem)
- Modern Danish translations (e.g. `anon_dyrerim.da` — always exclude)
- Standalone single-poem works (e.g. `anon_ave-maria-fuld-af-naade`)

All of these are indexed at the same level. A downstream tool can't easily filter "I want only the multi-poem collections" without per-book inspection. The same goes for filtering out translation editions (`.da` suffix) vs diplomatic editions (`_dipl` suffix) — they share the index.

**Suggestion to Tekstnet**: provide a structured API or category breakdown in the index (e.g. `/books/?type=multi-poem&type=single-poem&type=collection&translation=excluded`) so downstream tools can filter at the index level rather than inspecting every book.

## Comparison with other sources

Compared to the two previous sources in this project (DSL Reformationssalmer, UCPH early-danish-ballads), Tekstnet has:

| Aspect | DSL | UCPH | Tekstnet |
|---|---|---|---|
| Edition markers explicit | Yes (Jespersen 1573 etc.) | Yes (9 distinct manuscripts) | Yes (`_dipl`, `.da` suffix) |
| Poem numbering in URL | Yes (`/<book>/<page>`) | Yes (`/<book>/<NNN>`) | Yes (`/<book>/<NNN>`) |
| Stanza structure explicit | Sometimes (`<br/>[N]`) | Implicit (no markers) | Implicit (only `<div class="mt-3 mb-4">` wrapper) |
| Source-pid duplicates | Few | Many (DRSXV) | Many (DRSXV, DRSXI) |
| Author field always present | No (often "Anonym") | No (often anonymous) | No (often absent) |
| Language label | `Sprog` field | `Sprog` field (only on pubs) | `Sprog` field with 9 values |
| Title in `<title>` HTML | Reliable | Reliable | Inconsistent (multiple patterns) |
| Footnote apparatus in body | Inline (with `data-template` popovers) | Mostly inline (`<sup>`, `data-num`) | Inline (popover buttons) |

Tekstnet's coverage is wider (all Danish literature) but the structural markup is less consistent. For medieval/early-modern material, the UCPH manuscripts are better curated. For modern Danish literature (1800-present), Tekstnet is the only option but requires more careful parsing.

## Acknowledgements

To be clear: I appreciate that Tekstnet is doing the hard work of curating a free, public archive of Danish literature, and these criticisms are aimed at making the resource more useful for downstream analysis, not at diminishing the value of the work. The editorial team is responsive and these observations should be read as collaboration, not as complaints.
