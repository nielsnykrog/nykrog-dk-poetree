"""
dsl_parser.py -- DSL "Danske Reformationssalmer" -> PoeTree-format JSON parser.

Input : raw HTML of a poem page from salmer.dsl.dk (cached in sources/dsl-reformationssalmer/raw/)
Output: one JSON file per poem, conforming to our local convention
        (PoeTree-compatible + local extensions: source.url, source.printer,
         body[].marginal_notes[])

Design notes (locked-in field policy):
  - title           = first <div class="verse-line"> text in the first <div class="poetry">
  - author.name     = "[anonymous]"
  - author.wiki     = null
  - author.born/died/country/viaf = null
  - year_created    = book.year_published
  - source.title    = book.title (from colophon)
  - source.publisher= book.udgiver
  - source.printer  = book.trykker  (local extension)
  - source.place    = book.udgivelsessted
  - source.year_published = book.udgivelsesår
  - source.corpus   = "Danske Reformationssalmer (Dansk Sprog- og Litteraturselskab)"
  - source.url      = the page URL
  - body[]          = all <div class="verse-line"> in order, with stanza_id,
                      text (cleaned), and marginal_notes[] extracted to a side array
  - body[].words[]  = empty list (PoeTree pipeline fills)
  - body[].part     = False
  - form, body-meter-*, locations, neighbors, duplicate = null/empty/false

Usage:
    python dsl_parser.py path/to/page.html --book-slug <slug> --book-meta '<json>'
    python dsl_parser.py path/to/page.html --manifest path/to/manifest.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


CORPUS_NAME = "Danske Reformationssalmer (Dansk Sprog- og Litteraturselskab)"

# --- HTML helpers ------------------------------------------------------------

_TAG_SCRIPT = re.compile(r'<script[\s\S]*?</script>', re.IGNORECASE)
_TAG_STYLE  = re.compile(r'<style[\s\S]*?</style>',  re.IGNORECASE)
_TAG_COMM   = re.compile(r'<!--[\s\S]*?-->',         re.IGNORECASE)


def clean_html(html: str) -> str:
    """Strip scripts, styles, comments. Returns the raw HTML tree to parse."""
    html = _TAG_SCRIPT.sub('', html)
    html = _TAG_STYLE.sub('', html)
    html = _TAG_COMM.sub('', html)
    return html


def strip_inline_tags(html: str) -> str:
    """Remove ALL tags from a chunk of HTML, returning plain text."""
    text = re.sub(r'<[^>]+>', '', html)
    # Normalise whitespace
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# --- Core extraction ---------------------------------------------------------

def extract_region(html: str) -> str:
    """Pull out the <div id="region-content"> block."""
    m = re.search(r'<div[^>]+id="region-content"[^>]*>([\s\S]*?)</results>', html)
    return m.group(1) if m else ''


def extract_poems(region: str):
    """Yield each <div class="poetry"> block found in the region, in order.
    Each block is returned as raw inner HTML.
    """
    # Simple tag-by-tag iterator: find every <div ... class="poetry" ...> and
    # match its closing </div> by depth counting (the DSL HTML is regular enough
    # that verse-line divs are not nested inside poetry divs at depth > 1).
    pos = 0
    while True:
        m = re.search(r'<div\b[^>]*class="[^"]*\bpoetry\b[^"]*"[^>]*>', region[pos:])
        if not m:
            return
        start = pos + m.end()
        # Find matching </div> by depth
        depth = 1
        i = start
        while i < len(region) and depth > 0:
            next_open  = region.find('<div', i)
            next_close = region.find('</div>', i)
            if next_close == -1:
                return
            if next_open != -1 and next_open < next_close:
                depth += 1
                i = next_open + 4
            else:
                depth -= 1
                i = next_close + 6
        yield region[start:i-6]   # contents inside the <div class="poetry">
        pos = i


def extract_verse_lines(poetry_html: str):
    """Yield (raw_html, text) for each <div class="verse-line"> inside a poetry block."""
    pos = 0
    while True:
        m = re.search(r'<div\b[^>]*class="[^"]*\bverse-line\b[^"]*"[^>]*>', poetry_html[pos:])
        if not m:
            return
        start = pos + m.end()
        # Match closing </div> by depth
        depth = 1
        i = start
        while i < len(poetry_html) and depth > 0:
            next_open  = poetry_html.find('<div', i)
            next_close = poetry_html.find('</div>', i)
            if next_close == -1:
                return
            if next_open != -1 and next_open < next_close:
                depth += 1
                i = next_open + 4
            else:
                depth -= 1
                i = next_close + 6
        raw_inner = poetry_html[start:i-6]
        # Strip apparatus:
        #   - <span class="app"> ... </span> with <span class="textcriticalnote"> markers
        #   - page-break markers (they're inside legacy-page-break spans)
        cleaned = strip_apparatus(raw_inner)
        # Extract marginal notes BEFORE stripping them
        marginal = extract_marginal_notes(raw_inner)
        # Strip inline tags, normalise whitespace
        text = strip_inline_tags(cleaned)
        # Strip any residual page-break marks ("|" pipes, sigil like "3r")
        text = strip_page_break_sigil(text)
        yield raw_inner, text, marginal
        pos = i


def strip_apparatus(html: str) -> str:
    """Remove text-critical apparatus, page-break markers, and marginal-note wrappers.
    Important: page-break spans contain nested spans, so we have to repeat the
    pattern until no more matches, OR match with a balanced-spans approach.
    """
    # 1. Page-break markers: <span class="legacy-page-break"> ... </span>
    #    These can appear inline in the middle of a word (e.g. between "Je" and "sum").
    #    The inner structure has nested <span class="page-break-mark">|</span><a>3v</a>.
    #    We loop because non-greedy matching can stop at the inner </span>.
    prev = None
    while prev != html:
        prev = html
        html = re.sub(r'<span\b[^>]*class="[^"]*\blegacy-page-break\b[^"]*"[^>]*>[\s\S]*?</span>', '', html, count=1)
        html = re.sub(r'<span\b[^>]*class="[^"]*\bpage-break-mark\b[^"]*"[^>]*>[\s\S]*?</span>', '', html, count=1)
    # 1b. After legacy-page-break wrappers are gone, a <a class="facsimile-link" name="...">3v</a>
    #     link may remain. Strip ALL facsimile-link anchors (they only carry sigils).
    html = re.sub(r'<a\b[^>]*class="[^"]*\bfacsimile-link\b[^"]*"[^>]*>[\s\S]*?</a>', '', html)
    # 1c. Strip any remaining page-mark characters (just in case): pipes
    html = html.replace('|', '')
    # 2. Critical-note marker (e.g. †) -- just the dagger itself
    html = re.sub(r'<span\b[^>]*class="[^"]*\btextcriticalnote\b[^"]*"[^>]*>[\s\S]*?</span>', '', html)
    # 3. <span class="app"> -- the lemma/witness wrapper
    html = re.sub(r'<span\b[^>]*class="[^"]*\bapp\b[^"]*"[^>]*>[\s\S]*?</span>', '', html)
    # 4. <span class="appnotecontents"> -- the critical note text (often display:none)
    html = re.sub(r'<span\b[^>]*class="[^"]*\bappnotecontents\b[^"]*"[^>]*>[\s\S]*?</span>', '', html)
    # 5. Marginal-note WRAPPER spans -- only the outer <span class="marginal-note">,
    #    not its inner <span class="marginal-note-content"> (which we extract separately).
    #    The wrapper is removed BEFORE strip_inline_tags so its content doesn't leak into text.
    html = re.sub(r'<span\b[^>]*class="[^"]*\bmarginal-note\b[^"]*"[^>]*>[\s\S]*?</span>', '', html)
    # 6. Stray dagger characters left behind by apparatus stripping
    html = html.replace('†', '')
    return html


def strip_page_break_sigil(text: str) -> str:
    """Remove residual '| 3r' style page-break sigils from clean text."""
    text = re.sub(r'\s*\|\s*\d+[rv]\s*$', '', text)
    text = re.sub(r'^\s*\d+[rv]\s*\|\s*', '', text)
    return text.strip()


def extract_marginal_notes(html: str) -> list:
    """Pull out the textual content of every <span class="marginal-note-content">.
    Returns a list of strings (one per marginal note span).
    """
    notes = []
    for m in re.finditer(r'<span\b[^>]*class="[^"]*\bmarginal-note-content\b[^"]*"[^>]*>([\s\S]*?)</span>', html):
        text = strip_inline_tags(m.group(1))
        if text:
            notes.append(text)
    return notes


def is_poem_page(html: str) -> bool:
    """A page bears a poem iff it has >= 1 <div class="poetry">."""
    return bool(re.search(r'<div\b[^>]*class="[^"]*\bpoetry\b[^"]*"', html))


def find_first_poem_block(html: str) -> str:
    """Return the inner HTML of the first <div class="poetry"> block (or '')."""
    region = extract_region(html)
    for block in extract_poems(region):
        return block
    return ''


# --- Building the poem object ------------------------------------------------

def build_poem(html: str, book: dict, page_url: str) -> dict:
    """Build the PoeTree-format poem dict from a DSL page HTML and book metadata."""
    region = extract_region(html)
    if not region:
        raise ValueError(f"No region-content found in {page_url}")

    body_lines = []     # list of {id, stanza_id, text, marginal_notes}
    stanza_idx = 0
    line_id = 0
    first_verse_text = None

    for stanza_html in extract_poems(region):
        for raw, text, marginal in extract_verse_lines(stanza_html):
            if first_verse_text is None and text:
                first_verse_text = text
            body_lines.append({
                "id": line_id,
                "stanza_id": stanza_idx,
                "text": text,
                "part": False,
                "marginal_notes": marginal,
            })
            line_id += 1
        stanza_idx += 1

    if not body_lines:
        raise ValueError(f"No verse-lines found in {page_url}")

    return {
        "id": None,
        "title": first_verse_text,
        "year_created": book["year_published"],
        "neighbors": [],
        "duplicate": False,
        "locations": False,
        "author": {
            "name": "anonymous",
            "viaf": None,
            "wiki": None,
            "country": None,
            "born": None,
            "died": None,
        },
        "source": {
            "id": None,
            "title": book["title"],
            "year_published": book["year_published"],
            "publisher": book["publisher"],
            "printer": book["printer"],
            "place": book["place"],
            "corpus": CORPUS_NAME,
            "url": page_url,
        },
        "body": body_lines,
    }


# --- CLI ---------------------------------------------------------------------

def slugify(s: str) -> str:
    """Aggressive slug: lowercase, drop diacritics, whitespace->-, strip punctuation."""
    if not s:
        return ''
    # Normalise unicode (drops diacritics where possible: ÿ -> y, æ -> ae, ø -> o, etc.)
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'[^a-z0-9\-_]+', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:80]


def make_filename(source_id: str, author_slug: str, title_slug: str, book_slug: str) -> str:
    """4-part filename with double-dash separators."""
    parts = [source_id, author_slug or 'anonymous', title_slug, book_slug]
    return '--'.join(parts) + '.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html_path", help="path to the cached DSL page HTML")
    ap.add_argument("--page-url", required=True, help="the URL the page was fetched from")
    ap.add_argument("--book-slug", required=True)
    ap.add_argument("--source-id", default="dsl-reformationssalmer")
    ap.add_argument("--manifest", default=r"C:\Users\niels\Documents\nykrog-dk-poetree\sources\dsl-reformationssalmer\manifest.json")
    ap.add_argument("--out-dir", default=r"C:\Users\niels\Documents\nykrog-dk-poetree\poems")
    args = ap.parse_args()

    html = Path(args.html_path).read_text(encoding='utf-8')
    html = clean_html(html)

    if not is_poem_page(html):
        print(f"[skip] {args.page_url} is not a poem-bearing page (0 .poetry divs)", file=sys.stderr)
        sys.exit(2)

    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    book = next((b for b in manifest['books'] if b['slug'] == args.book_slug), None)
    if book is None:
        print(f"[error] book-slug '{args.book_slug}' not found in manifest", file=sys.stderr)
        sys.exit(2)

    poem = build_poem(html, book, args.page_url)

    # Filename: <source-id>--<author-slug>--<title-slug>--<book-slug>.json
    author_slug = slugify(poem['author']['name'])
    title_slug = slugify(poem['title'])
    fname = make_filename(args.source_id, author_slug, title_slug, book['slug'])
    out_path = Path(args.out_dir) / fname
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(poem, ensure_ascii=False, indent=2), encoding='utf-8')

    n_stanzas = len({ln['stanza_id'] for ln in poem['body']})
    print(f"[ok] wrote {out_path}")
    print(f"     title: {poem['title']!r}")
    print(f"     {n_stanzas} stanzas, {len(poem['body'])} verse-lines, "
          f"{sum(1 for ln in poem['body'] if ln['marginal_notes'])} with marginal notes")


if __name__ == "__main__":
    main()