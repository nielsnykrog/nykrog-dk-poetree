# nykrog-dk-poetree

A structured poetry dataset of 3,424 Danish-language poems drawn from three scholarly
sources. Each poem is one JSON file conforming to the [PoeTree](https://versologie.cz/poetree/)
schema (with project-local extensions for marginal notes, `dramatic_poem`, and `diplomatic_edition`).

This is a contribution by Niels Nykrog toward the Danish PoeTree corpus.
Curated for sharing with the PoeTree working group; intended to merge into a larger
pooled dataset.

## What's in this repo

```
nykrog-dk-poetree/
├── poems/                   ← the dataset: 3,424 JSON files, one per poem
├── schema/                  ← PoeTree JSON Schema + controlled vocabularies
├── sources/                 ← per-source raw snapshots, parsers, manifests
│   ├── dsl-reformationssalmer/
│   ├── early-danish-ballads/
│   └── tekstnet-dsl/
├── scripts/                 ← validator, dedup tools, parsers (generic, reusable)
├── deletion_log.txt         ← audit trail of all deletions made during curation
├── discovery_log.txt        ← per-source discovery statistics
├── scrape_log.txt           ← per-source full-scrape run logs
└── .gitignore
```

The dataset itself (`poems/`) is **37.4 MB** across all 3,424 files.

## Sources

| Source ID | Corpus | Poems | Period |
|---|---|---:|---|
| `dsl-reformationssalmer` | DSL — Danish Reformation hymnals (Dietz 1529, Malmø 1533, Vingaard 1553, Thomissøn 1569, Jespersen 1573, etc.) | 782 | 16th c. |
| `early-danish-ballads` | Danish medieval/early-modern ballads from the major manuscript sources (Karen Brahe's folio, Anna Munks håndskrift, Dronning Sophias visebog, Langebeks kvart, etc.) | 936 | 16th–17th c. |
| `dsl-tekstnet` | Tekstnet — Danish Society for Language and Literature's general literature corpus | 1,706 | Various periods |

Total: **3,424 poems** across the three sources. Each poem in `poems/` is named
`<source-id>--<author-slug>--<poem-title-slug>--<book-slug>.json`.

## Filename convention

```
<source-id>--<author-slug>--<poem-title-slug>--<book-slug>.json
```

- **4 fields, double-dash `--` separator**, single-dash `-` within fields.
- **Source-id prefix** prevents collisions when corpora are merged.
- **Author-slug** is `lastname-<first-initial(s)>` with Danish diacritics transliterated
  to ASCII: `æ→ae`, `ø→o`, `å→aa`. Examples: `andersen-hc`, `brorson-ha`,
  `oehlenschlaeger-a`, `ploug-c`, `kingo-t`. Honorifics (`Hr.`, `Dr.`, `Fr.`, `Prof.`)
  are stripped before slugging.
- **Title-slug** is lowercase, diacritics-transliterated, whitespace → `-`, non-`[a-z0-9\-_]`
  stripped, max 80 chars.
- **Book-slug** is derived per-source:
  - `dsl-tekstnet` — `slugify(source.title)` if set, else `unknown`
    (with `-<7-hex-md5>` truncation-handling when >80 chars)
  - `dsl-reformationssalmer`, `early-danish-ballads` — URL book-slug verbatim
    (e.g. `dietz-salmebog-1529`, `karen-brahes-folio-aeldre-del`)
- The slug is a working handle. The original orthography lives inside the JSON.

The original orthography is preserved in the JSON fields (`title`, `body[].text`,
`author.name`, `source.title`, `source.printer`, etc.) — including early-modern
spellings like `wÿ`, `Jhesu`, `Christe`, `ÿ`.

## Schema

The dataset follows the [PoeTree](https://versologie.cz/poetree/) JSON Schema. The
authoritative copy is in `schema/poetree.schema.json`; controlled vocabularies are in
`schema/poetree.values.json`.

### Top-level fields

| Field | Type | Notes |
|---|---|---|
| `id` | `null` (project convention) | PoeTree allows strings; we leave it null |
| `title` | `string` | Original orthography |
| `year_created` | `int \| list[int] \| null` | `int` for a known year, `list[A, B]` for a span (e.g. `[1630, 1639]` for "1630'erne") |
| `neighbors`, `duplicate`, `locations` | `null` / `false` | Computed fields, intentionally left empty |
| `author.name` | `string` | `"anonymous"` (no brackets) when unknown |
| `author.country` | `null` | Left empty (PoeTree's `iso 639-1` label is misleading) |
| `author.wiki` | `string \| null` | **Wikidata Q-id only** (e.g. `"Q5673"`), never a Wikipedia URL |
| `source.corpus` | `string` | Human-readable source name |
| `source.title` | `string \| null` | Source book title (DSL only) |
| `source.publisher` | `string \| null` | Filled only when known |
| `source.printer` | `string \| null` | Filled only for DSL — empty for the other sources |
| `source.place`, `source.year_published` | `string \| null`, `int \| null` | |
| `source.url` | `string` | Reader convenience — the live URL of the source page |
| `body[]` | `array` | Ordered list of verse lines, each with `id`, `stanza_id`, `text`, `part`, `marginal_notes` |
| `form`, `body[]words`, `body[]meter_*` | empty | Optional/computed, intentionally left empty |

### Project-local extensions (not in PoeTree core schema)

- `dramatic_poem: true` — flag on a poem that is structurally a drama/scene
  (e.g. a scene from a play scraped from Tekstnet). 65 such files.
- `diplomatic_edition: true` — flag on a poem whose source text is a diplomatic
  transcription preserving manuscript features. 1 such file.
- Marginal notes in each line of body. Used for such purposes as noting speaking characters in dramatic poems and for bible references in hymns.

The validator accepts these as warnings (not errors).

## Sources in detail

### `sources/<id>/manifest.json`
Provenance for each source: original URL, fetch timestamp, sha256 of raw bytes,
parser used, access mode, mutability flag.

### `sources/<id>/raw/`
Immutable HTML snapshots of every page in scope. **Large (DSL Reformation: 293 MB;
ballads: 13 MB; Tekstnet: not snapshotted — the source is small and re-fetchable).**
These are excluded from git via `.gitignore`.

### `sources/<id>/_discovery/` and `_publications/`
Per-source discovery and publication-mapping reports used during the scrape.

### Re-runnable pipeline
For each source, the parser (in `scripts/dsl_parser.py`, `sources/*/parser.py`) reads
the raw snapshot (not the live URL) and emits one JSON per poem. The validator
(`scripts/validate.py`) is run on every batch.

## Validation

```bash
cd nykrog-dk-poetree
python scripts/validate.py poems/
```

Should report: **3,424 files, 0 errors**. Warnings are benign
(`dramatic_poem` / `diplomatic_edition` keys beyond PoeTree core).

A smoke test fixture lives in `scripts/_smoke/`.

## Curation history

The dataset went through two post-scrape curation passes that are documented in
`deletion_log.txt`:

1. **Language filter** — removed pure-Latin items from the Danish Reformation hymnal
   corpus (DSL mixed Latin liturgical fillers in with the Danish hymns). Result:
   `dsl-reformationssalmer` reduced by ~170 items. See `sources/dsl-reformationssalmer/PHASE3_REPORT.md`
   for the heuristic discussion.
2. **Deduplication** — removed items where one poem was a truncated subset of another
   (same title + same source, line-set containment ≥90%). Result: ~88 pairs removed.

The Latin detection toolkit used in pass 1 — classifiers, bucket generators,
the 38 MB Whitaker's-WORDS inflected-form set — was relocated to
`../latin-detection-toolkit/` after cleanup completed.

## What is NOT in this repo

- **`raw/` HTML snapshots** are gitignored (too large; poems/ + manifest.json are
  the source of truth for already-parsed content).
- **`__pycache__/`** directories are gitignored.
- **`danish-dramas/`** (44 files of dramatic poetry scraped alongside the Tekstnet
  corpus) is **not** part of the poetry dataset — it lives separately in
  `../danish-dramas/` and may follow a different schema.
- **Latin detection toolkit** (scripts + 38 MB data) lives in
  `../latin-detection-toolkit/`.
- **Process notes** (`SESSION_HANDOFF.md`, `PROGRESS.md`, `PILOT_NOTES.md`,
  `DECISIONS.md`, `PHASE3_REPORT.md`, `observations-on-source-quality.md`) are kept
  in `sources/<id>/` as a historical record of decisions.

## License

The repository is split-licensed by content type:

| What | License | See |
|---|---|---|
| `poems/`, `schema/`, `sources/<id>/raw/`, `sources/<id>/discovery/`, `*.log.txt` (the data) | **CC0 1.0** — public domain dedication, no attribution required | `LICENSE-DATA` |
| `scripts/`, `sources/<id>/parser.py` (the code) | **0BSD** — permissive, no attribution required, SPDX-recognized for code reuse | `LICENSE-CODE` |

The underlying poems themselves are in the public domain;
the curation, schema design, and JSON structuring are released under CC0. The
code is 0BSD so it can be upstreamed into MIT- or Apache-licensed projects in
the PoeTree toolchain without license-compatibility friction (CC0 is rejected
by Apache-2.0 §3 for code contributions — 0BSD is the practical equivalent
that works).
