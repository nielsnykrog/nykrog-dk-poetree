# Tekstnet DSL — source-specific notes

Source: https://tekstnet.dk/
Hosting: `https://cst.dk/` is **not** used here — Tekstnet has its own hosting
Corpus name (for `source.corpus`): `Tekstnet — Det Danske Sprog- og Litteraturselskab`
Source id (for filenames): `tekstnet-dsl`

General archive of Danish literature from the Middle Ages to today — medieval
ballads, Reformation hymns, 19th-c verse, modernist prose-poems, and much
non-poetry besides. Significantly different from Sources #1 and #2 in that
it is a **general literary archive** rather than a verse-specific corpus.

The 9 earliest Danish ballad manuscripts (Source #2) are **not** in Tekstnet
(those came from the DSL/UCPH `cst.dk` mirror). Tekstnet covers different
texts, often with more recent editorial apparatus (modern Danish
translations, critical notes, parallel editions).

## Corpus shape (from general index)

- **~1149 index entries** in the general index (`/books/`). All have a
  year; 919 have an explicit author field. Range: 1100–2024 (plus one
  sentinel entry at year 9999).
- **Suffix distribution** (from the index):
  - `normalised` (no suffix): 1023
  - `.da` (modern Danish translation): 83 — **exclude**
  - `_dipl` (diplomatic edition): 43 — include if and only if no
    normalised version exists for the same work

## URL pattern

- General index: `https://tekstnet.dk/books/`
- Per-book index: `https://tekstnet.dk/books/<book-slug>/`
- Per-poem (multi-poem book): `https://tekstnet.dk/books/<book-slug>/<NNN>/`
- Per-poem (single-poem book): `https://tekstnet.dk/books/<book-slug>/` — same URL as the book index; body lives on the index page itself
- Per-edition-suffix: `_dipl` or `.da` appended to the book slug

Book slugs follow the convention `<author>-<title>` (e.g. `arrebo-a_hexaemeron`,
`brorson-ha_troens-rare-klenodie`) or `anon_<title>` for anonymous works. The
`anon_` prefix is **part of the slug, not a separate field**.

## Edition-suffix pattern (user rule, 2026-07-03)

| Slug | Edition | Action | Filename slug segment |
|---|---|---|---|
| `work_id` | normalised (default) | **include** | `work_id` (normalised) |
| `work_id_dipl` | diplomatic, normalised exists | exclude (normalised wins) | — |
| `work_id_dipl` (no normalised) | diplomatic, only Danish | **include**, mark `Diplomatic Edition: true` | `work_id--diplomatic-version` |
| `work_id.da` | modern Danish translation | **always exclude** | — |

The "same work, different edition" detection: strip `_dipl` or `.da` suffix
from the book slug to get the base work id. If `work_id`, `work_id_dipl`,
and `work_id.da` all exist, the normalised wins. If only `_dipl` and `.da`
exist, the `_dipl` wins. If only `.da` exists, the entire work is excluded
(no Danish source).

**Filename slug**: use the **normalised** base work id (no `_dipl` suffix,
no `.da` suffix). For diplomatic-only works, append `--diplomatic-version`
to the filename slug so it's recoverable which edition it is.

## Language filter (user rule, 2026-07-03)

The full `/languages/` list (fetched 2026-07-03) contains exactly 9 values:
- **Include** (Danish variants): `gammeldansk`, `ældre-nydansk`, `yngre-nydansk`, `dansk` (catch-all — also used for partial-Latin works labelled as Danish)
- **Exclude**: `latin`, `engelsk`, `fransk`, `tysk`
- The 9th value is `sprog` (the breadcrumb link, not a real language)

The `Sprog` field on each publication-index page is the source of truth:

```html
<dt class="col-sm-4 article-info__item-name">Sprog</dt>
<dd class="col-sm-8 article-info__item-value"><a href=/languages/X>label</a></dd>
```

**Filter rule**: include the work if the `Sprog` link target is one of
`gammeldansk`, `ældre-nydansk`, `yngre-nydansk`, or `dansk` (case-insensitive
match on the slug after `/languages/`). Exclude otherwise.

**Why book-level filter, not per-poem**: the book's `Sprog` propagates to
every poem in the book — no per-poem language check needed. The only edge
case is Variant B (single-poem book) where the book's `Sprog` IS the
poem's `Sprog`.

**Confirmed Danish-via-partial-Latin example**: `anon_tro-haab-og-kaerlighed`
(Danish + Latin mix) is labelled `dansk` in Tekstnet's index, and the
introduction page confirms: *"Tro, Håb og Kærlighed er skrevet på en
blanding af dansk og latin"*. We include these.

## Metadata block structure

Publication-index pages (`/books/<book-slug>/`) have an `article-info` block:

```html
<div class="p-4 bg-light"><dl class=row>
  <dt>FieldName</dt>  <dd>FieldValue</dd>
  ...
</dl></div>
```

Field names observed so far (in **Danish**):
- `Forfatter` — author (string; if "Anonym" or absent, treat as anonymous)
- `Udgivelsesår` — publication year (4-digit string, sometimes 9999 for "unknown")
- `Sprog` — language (see filter above)
- `Udgiver` / `Udgivere` — editor(s) of the modern edition
- `Redaktion` — editorial team
- `Tilsynsførende` — supervising editor
- `Studentermedhj.` — student assistants
- `Kommentarforf.` — commentary author(s)
- `Finansiering` — funding bodies
- `Hovedredaktør` — editor-in-chief (only on standalone single-poem works)

Some books have **2 metadata blocks**: block 0 = the literary metadata
(Forfatter, Udgivelsesår, Sprog); block 1 = the editorial credits
(Udgiver, Redaktion, etc.). Some books have **1 block** (standalone
single-poem works show only editorial credits — no Forfatter/Udgivelsesår/Sprog).

**Inheritance rule** (user 2026-07-03):
- `author`, `source.title`, `source.publisher` (from `Udgiver` block 1),
  `source.place` (when present), and `source.year_published` (from book's
  `Udgivelsesår`): **always inherited from the book** when present.
- `title` and `year_created`: **poem-specific** (per-page when present).
- For standalone single-poem works, the `Forfatter` / `Udgivelsesår` /
  `Sprog` are **not on the book page** — they need to be extracted from
  the poem page itself (or the URL slug).

## Poem page structure

Three observed variants, distinguished by URL pattern and body markup:

### Variant A — Multi-poem book, normalised edition (most common)

URL: `https://tekstnet.dk/books/<book-slug>/<NNN>/`
Title source: usually inferred from `<h1>` text (after stripping the `|`
separator, the `Nr. N` prefix, and any `<button>` apparatus element).
Body markup: regular stanzas.

```html
<div class=text-container>
  <h1><span class=pageBegin>...</span> PART_OR_SECTION_TITLE</h1>
  <p>Mel. ...</p>                                    ← apparatus
  <div class="mt-3 mb-4">
    <div class=stanza-number>N.</div>                 ← stanza marker
    <div class=line>Verse line 1</div>
    <div class=line>Verse line 2</div>
    ...
  </div>
  <div class="mt-3 mb-4">
    <div class=stanza-number>N+1.</div>
    <div class=line>...</div>
    ...
  </div>
</div>
```

Stanza IDs: zero-based (the v6 rule from Source #2 applies here too).
Sole-sigil lines: drop (the v6 rule applies here too — never seen yet
in this corpus but the rule generalises).

### Variant B — Single-poem book, normalised edition (e.g. `anon_tro-haab-og-kaerlighed/`)

URL: same as the book index (no `/NNN/` subdirectory).
Title source: URL slug (with `anon_` prefix stripped) or `<title>` HTML
element, parsed as `Author: Title`.
Body markup: same as Variant A, but the body lives on the book-index
page itself rather than a subdirectory.

```html
<div class=text-container>
  <h1></h1>                                           ← often empty
  <div class="mt-3 mb-4">
    <div class=line><span class=pageBegin>...</span>LINE 1</div>
    <div class=line>LINE 2</div>
    ...
  </div>
  ...
</div>
```

### Variant C — Drama (e.g. `heiberg-jl_nye-digte/003/`)

Body markup uses `<div class=drama-line>` for verse and
`<p class=drama-speaker>` for speaker labels (marginal notes, not body lines):

```html
<h2>I. Ankomsten</h2>                                  ← act/scene
<div class=drama>
  <p class=drama-speaker>Vilhelm</p>                 ← SPEAKER (marginal note)
  <div class="mt-3 mb-4">
    <div class=drama-line>Verse line 1</div>
    <div class=drama-line>Verse line 2</div>
    ...
  </div>
  ...
</div>
```

Stanzas: **no `<div class=stanza-number>`** in drama — stanzas are inferred
from the `<div class="mt-3 mb-4">` wrapper (one stanza per wrapper).
Speaker labels go into `body[].marginal_notes[]`, NOT into `body[].text`.

### Variant D — Modernist prose-as-poem (e.g. `munch-petersen-g_mod-jerusalem/002/`)

Body has **no line markup** — the entire text is one `<p>` block:

```html
<div class=text-container>
  <h1>[7] | I. fra i dag</h1>                          ← title in h1
  <p>fra i dag er hele verden anderledes...</p>      ← single <p> with prose
</div>
```

Detection rule: if a poem page has `<div class=text-container>` and
`<p>` body but no `<div class=line>` and no `<div class=drama-line>`,
flag as a **prose-as-poem candidate**. The trigger for extraction is:
**at least 3 sibling poems in the same book are recognised as verse.**
If yes, treat the unrecognised one as a candidate and flag for review.
If no, skip the whole book (likely a novel or essay collection).

**Do not attempt to parse the prose into verse lines.** Just extract the
title from the h1 and surface the body for human review. Works written
after 1900 only (per user rule).

## Title extraction (the tricky part)

There is no `<b>Titel:</b>` field. The title must be derived from one of:

| Variant | Title source | Example |
|---|---|---|
| Multi-poem book, Variant A | `<h1>` text after `\|` separator, after stripping `Nr. N` and `<button>` apparatus | `1. Advents-Psalmer.` + `Nr. 1.` + `<button>A</button>` → derive from body's first line `Fryd dig! du JEsu bruud,` |
| Single-poem book, Variant B | URL slug with `anon_` prefix stripped, OR `<title>` tag parsed as `Author: Title` | URL `anon_ave-maria-fuld-af-naade` → `Ave Maria fuld af nåde` |
| Drama, Variant C | Often the section h2 or h1; sometimes blank | `De Nygifte En Romance-Cyclus` (a section title) |
| Prose-as-poem, Variant D | h1 text after `\|` | `I. fra i dag` |

**Pragmatic rule for Variant A**: when the `<h1>` looks like a section/part
header (e.g. `DEN FØRSTE DEEL, TROENS FRYDE-FEST.` or `1. Advents-Psalmer.`),
use the **first line of the body** as the title. The Tekstnet `<title>` tag
is reliable: it follows the pattern `Author: »Title« fra Book (year)` and
the inner quoted title is the canonical title.

**Filename slug construction**: take the title, slugify, append
`--tekstnet-dsl` as the book-slug segment. For multi-poem books where the
title comes from the body's first line, slugify the first line directly
(removing trailing punctuation). For single-poem works, slugify the URL
slug minus `anon_` prefix.

## Edition-suffix discovery (for the full scrape)

Before scaling, the full-scrape Phase 1 should:
1. Walk the general index (or the per-genre index pages).
2. Group by base work id (strip `_dipl` and `.da`).
3. For each group, decide: include normalised (default), include `_dipl`
   (if no normalised), exclude `.da` (always).
4. Build the canonical work list with one row per work.

## To be done before scaling

- **Sampling notes (2026-07-03)**:
  - `brahe-t_henrico-ranzovio` is a `digte`-genre book with `Sprog=latin` — correctly excluded by book-level filter.
  - `heiberg-jl_nye-digte` has multiple drama poems using `<div class=drama-line>` + `<p class=drama-speaker>` consistently. Heiberg's "En Sjæl efter Døden" alone has 1649 drama-lines and 262 speakers.
  - `munch-petersen-g_mod-jerusalem` is mixed: some poems are regular verse (`<div class=line>`), some are prose-as-poem (single `<p>`). The parser dispatches per-poem based on markup, not per-book.
  - `anon_jon-praest-thott` is `gammeldansk` year 1500 with no explicit `Forfatter` field — author is anonymous by absence, not by name.
  - Salmebog genre has only 1 entry (Brorson); it's already in `religion` and `poesi`. No separate Salmebog fetch needed.

## Pre-scaling checks done (2026-07-03)

- Full `/languages/` list fetched and enumerated.
- 6 genre categories confirmed reachable: `digt` (534 slugs), `digte` (8), `digtsamling` (1), `poesi` (90), `religion` (37), `salmebog` (1). Total unique slugs: 670.

## Per-source reference

For Source #1 (DSL Reformationssalmer), see `references/dsl-reformationssalmer.md`.
For Source #2 (early-danish-ballads, UCPH), see `references/early-danish-ballads.md`.
For Source #3 (tekstnet-dsl, this file), you are reading it.

For new sources, write a similar `references/<source-id>.md` capturing the
URL pattern, HTML structure, and quirks — anything you'd want to hand to
a fresh agent.