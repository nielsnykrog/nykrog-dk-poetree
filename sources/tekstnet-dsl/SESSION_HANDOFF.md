# Source #3 — tekstnet-dsl: Session Handoff (2026-07-03)

**Status:** Pilot complete (parser v4.1), pre-fix scrape trashed, fix plan locked in for re-scrape tomorrow.

## Where we are

- ✅ **Pilot v4.1** frozen: 9 poems, 0 errors, 0 leakage. All rules in `parser.py`.
- ✅ **Pre-fix full scrape** (2255 JSONs) moved to `_trash_2026-07-03/` (recoverable).
- ✅ **Discovery doc** at `references/tekstnet-dsl.md`. **Source-quality observations** at `observations-on-source-quality.md`.
- ⏳ **Re-scrape with fix plan** — pending your sign-off tomorrow.

## Key findings from this session's review

### 1. Title handling was wrong

The parser conflated poem title and publication title. There are TWO page types:

**Standalone page** (URL is `/books/<slug>/`, body lives on the publication page itself):
- `<h1>` is the **poem title** (large header)
- Breadcrumb: `<a>Author:\nPoemTitle</a>`
- `Udgivelsesår` is on the page itself (e.g. `ploug-c_balvise/` → year 1847)
- **No publication title** on the page — leave `source.title` empty

**Collection-part page** (URL is `/books/<slug>/<nnn>/`):
- `<h1>` is the **poem title** (with optional page-sigil prefix to strip)
- Two breadcrumbs:
  - First: `Author:\nBookTitle` ← **source.title**
  - Active: `Section:\nPoemTitle` ← **title** (after last `:`)
- `Udgivelsesår` is NOT on the page — must come from the publication's metadata

### 2. URL construction bug (already fixed inline)

Old code in `parse_poem_page`:
```python
poem_url = pub_meta["url"].rstrip("/").rsplit("/", 1)[0].rstrip("/") + f"/{poem_nnn}/"
```
This `rsplit("/", 1)` on `https://tekstnet.dk/books/<slug>/` returns just `https://tekstnet.dk/books` — losing the slug. Fixed to use direct string concatenation.

### 3. Music-version filter needed

Some books list different **musical settings** of the same poem (e.g. `ingemann-bs_aftensang` has 14 versions of "Aftensang"). These have:
- `<div class=metadata>` block in the body (with citation like `"Harpen", årg. 4, nr. 1 (1823), s. [1]`)
- `<title>` ending with `, Tekst 1823` or `, Musik 1830, Rudolph Bay` etc.

**Signal**: `<div class=metadata>` block + body_type NOT in (line, drama) → music-version, skip.

### 4. Books to skip entirely (100% music versions)

These 6 books have ALL /NNN/ entries as music versions:
- `ingemann-bs_aftensang` — 14 entries, all music versions
- `hauch-c_aftensang` — 13 entries
- `hauch-c_laengsel` — 10 entries
- `hauch-c_sangfuglen` — 6 entries
- `ingemann-bs_pigens-sang` — 23 entries
- `ingemann-bs_mesteren-kommer` — 15 entries

**Rule**: skip these books entirely.

### 5. Mixed book: `jacobsen-jp_gurresange`

20 entries — 9 real poems (I-IX, with line/drama markup, no metadata) + 11 music settings (with metadata, prose body).

**Rule**: keep the 9 real poems, skip the 11 music settings.

### 6. Cookbook / prose-collection false positives

Several Variant-A books have ALL `/NNN/ entries as prose-only`:
- `anon_kogebog-nks66` — 27 entries, all "Old Danish + Latin recipe"
- `anon_stenbog_nks66` — 64 entries, all prose

These get scraped as "prose-as-poem" candidates because my single-line filter excludes only non-prose with 1 line. The cookbooks have 3 `<p>` per entry (heading + Latin + recipe) and pass the filter, but they're not poems.

**Rule**: book-level filter — if ALL /NNN/ siblings have body_type=prose AND none have line/drama, exclude the whole book.

### 7. `year_published` for standalone poems

My parser currently doesn't scrape `Udgivelsesår` from the standalone page (Variant B). This came from the publication's publication-page metadata which has only editorial credits, no Udgivelsesår. The standalone poem PAGE has it.

**Fix**: for Variant B pages, read `Udgivelsesår` directly from the page's metadata block.

## Fix plan (locked in)

### A. Title rules in parser

```python
def extract_title_and_source_title(html, book_url):
    """Returns (title, source_title, year_created_from_page).

    Standalone: title=h1, source_title=None, year=from Udgivelsesår block.
    Collection-part: title=h1/active-breadcrumb, source_title=first-breadcrumb, year=None (from pub).
    """
    ...
```

### B. Per-page music filter (add to parse_poem_page)

```python
# If this page has metadata div AND body_type NOT in (line, drama),
# it's a musical setting version — skip.
if '<div class=metadata' in html and body_type not in ('line', 'drama'):
    return None
```

### C. Book-level prose-collection filter (add to full-scrape script)

```python
# For each Variant A book, sample first 3 /NNN/ pages.
# If ALL samples are body_type=prose (none line/drama), exclude the book entirely.
```

### D. Skip the 6 fully-music books (hard-coded list)

```python
MUSIC_BOOKS_TO_SKIP = {
    "ingemann-bs_aftensang",
    "hauch-c_aftensang",
    "hauch-c_laengsel",
    "hauch-c_sangfuglen",
    "ingemann-bs_pigens-sang",
    "ingemann-bs_mesteren-kommer",
}
```

### E. URL fix (already in parser.py)

The `parse_poem_page` URL construction was rewritten to:
```python
poem_url = pub_meta["url"]
if poem_nnn and not re.search(f"/{re.escape(poem_nnn)}/?$", poem_url):
    base = poem_url.rstrip("/")
    poem_url = f"{base}/{poem_nnn}/"
```

## Next steps tomorrow

1. Implement A, B, C, D in `parser.py` (parser changes) and the full-scrape script (book-level filters)
2. Re-run the full scrape: 609 works → 2514 poems, but with filters applied
3. Expected output after filters: ~2200-2300 JSONs (lose ~200 to cookbooks/prose-collections, ~80 to music-version entries, ~75 to whole-book skips)
4. Validate schema
5. Write PROGRESS.md
6. Phase 3b: author Wiki ID augmentation (post-scrape, deferred)

## Open questions / things deferred

- **`year_created`** (poem's own year) — currently inherits from book. The user said per-poem years are rare in standalone works. Mark as deferred.
- **Slug collision handling** — there's already a `--N` suffix logic, but I noticed earlier "automated filenames" hack for too-long slugs. The hash-suffix filenames are not human-readable. May need a better scheme.
- **`source.publisher`** — currently null per user rule. May augment later with historical publishers (C.A. Reitzel etc.) from a separate dataset.
