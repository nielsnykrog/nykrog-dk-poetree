"""
tekstnet-dsl parser — v2 (pilot, with depth-counting line extraction)
Built 2026-07-03 against the 10-poem pilot.

Handles four body variants:
  A: multi-poem book, body in /books/<slug>/NNN/  — regular verse or drama
  B: single-poem book, body in /books/<slug>/       — verse (regular or mixed Latin)
  C: drama in multi-poem book                        — drama-line + drama-speaker
  D: prose-as-poem in multi-poem book                — single <p> body

Edition-suffix handling:
  <work_id>            → include, normalised
  <work_id>_dipl       → include only if no <work_id> exists
  <work_id>.da         → always exclude (modern Danish translation)

Language filter: include only if book Sprog ∈ {dansk, gammeldansk, ældre-nydansk, yngre-nydansk}
"""
import re, unicodedata
from html import unescape
from urllib.parse import unquote


# --- Edition-suffix pattern ---

def base_work_id(slug):
    """Strip _dipl and .da suffixes to get the base work id."""
    if slug.endswith("_dipl"):
        return slug[:-5]
    if slug.endswith(".da"):
        return slug[:-3]
    return slug


# --- Slug helper ---

def extract_source_title(book_slug):
    """Derive a clean publication title from the book slug, stripping the
    author-prefix (e.g. 'andersen-hc_1862' → '1862', 'heiberg-jl_nye-digte' →
    'Nye Digte', 'anon_dyrerim_dipl' → 'Dyrerim').

    The convention: <author-lastname>-<initials-or-anon>_<title>. The
    author prefix is the part before the first underscore (or the first
    hyphen-prefixed token if no underscore).
    """
    s = book_slug
    # Find the underscore separating author from title
    if "_" in s:
        # <author>_<title> — strip author, keep title
        s = s.split("_", 1)[1]
    # Replace underscores with spaces, then title-case
    return s.replace("-", " ").replace("_", " ").strip()


def slugify(s, maxlen=80):
    """General-purpose slugify: NFKD+drop combining, lowercase, punct→-, ascii only.

    NOTE: this does NOT handle the Danish æ character (which is precomposed and
    is NOT decomposed by NFKD). For Danish text, use `slugify_title` (which
    explicitly maps æ→ae) or `book_slug` (which builds the segment-4 slug).
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w\-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:maxlen]


def slugify_title(s, maxlen=80):
    """Danish-title slugify: matches the existing dataset convention used for
    poem-title and book-title slugs in filenames (e.g. 'Mit Livs Eventyr' →
    'mit-livs-eventyr', 'Samlede Skrifter' → 'samlede-skrifter', 'Tillaeg' →
    'tillaeg').

    Mapping: NFKD+drop combining for ø/å/é/etc.; æ is precomposed (not
    decomposed) so it is explicitly mapped to 'ae'. Lowercase, all
    non-alphanumeric runs collapse to '-', trim, max 80 chars.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("æ", "ae")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:maxlen].rstrip("-")


def book_slug(source_title, year_published):
    """Build the segment-4 (book) slug for a Tekstnet filename. This is the
    canonical rule (locked in 2026-07-07, revised 2026-07-07):

      1. If source.title is set, use slugify_title(source.title).
      2. Otherwise use the year_published (as string) — this keeps the
         filename human-readable without repeating the poem title or
         carrying a legacy URL fragment.
      3. If neither is available, use 'unknown'.
      4. If the result exceeds 80 chars, truncate to 80 and append
         '-<7-hex-md5-of-full-slug>' for collision-handling.

    Collisions (same author + title + year) are resolved by the caller
    appending --2, --3, ... to the filename — not inside this function.

    Examples (from the live dataset after 2026-07-07 rename):
      source.title='Digte'                              -> 'digte'
      source.title=None, year=1830                      -> '1830'
      source.title=None, year=None                      -> 'unknown'
      source.title='Mit Livs Eventyr (...). 1855-1877'  -> 'mit-livs-eventyr-inklusive-fortsaettelse-og-tillaeg-1855-1877'

    The rule is symmetric: the same input always produces the same output,
    so re-runs are idempotent.
    """
    import hashlib
    if source_title:
        base = slugify_title(source_title)
    elif year_published:
        base = str(year_published)
    else:
        base = "unknown"
    if len(base) <= 80:
        return base
    h = hashlib.md5(base.encode("utf-8")).hexdigest()[:7]
    truncated = base[:80].rstrip("-")
    return f"{truncated}-{h}"


# --- Language filter ---

def is_danish(slug):
    if not slug:
        return False
    slug_lower = unquote(slug).lower()
    danish_values = {"dansk", "gammeldansk", "ældre-nydansk", "yngre-nydansk"}
    if slug_lower in danish_values:
        return True
    return False


def extract_sprog_slug(html):
    """Extract the Sprog value from a publication page. Returns the slug string
    (matching the /languages/<slug> scheme) or the raw text if no link.

    Tekstnet has TWO patterns:
      - Variant A (multi-poem book) with editorial metadata:
          <dt class="col-sm-4 article-info__item-name">Sprog</dt>
          <dd class="col-sm-8 article-info__item-value">
            <a href=/languages/yngre-nydansk>yngre nydansk</a>
          </dd>
        In this case, extract the slug from the href.
      - Variant B (single-poem book) with only editorial metadata:
          <dt class="col-sm-4 article-info__item-name">Sprog</dt>
          <dd class="col-sm-8 article-info__item-value">yngre nydansk</dd>
        In this case, the dd has plain text (no link); use the text as the
        slug (after url-decoding, lowercasing, replacing spaces with -).
    """
    m = re.search(
        r'Sprog\s*</dt>\s*<dd[^>]*>(.*?)</dd>',
        html, re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    inner = m.group(1)
    # Try the link pattern first
    link_m = re.search(r'href=[\'"]?/?[a-zA-Z]*/?languages/([^\'"/\s>]+)', inner)
    if link_m:
        return unquote(link_m.group(1))
    # No link — extract text. Strip HTML tags, normalise whitespace.
    text = re.sub(r'<[^>]+>', '', inner)
    text = re.sub(r'\s+', ' ', text).strip()
    # Slugify: lowercase, replace spaces with -
    text = text.lower()
    text = text.replace(' ', '-')
    # The text in Variant B is already a slug-like form (e.g. "yngre nydansk")
    # but with a space; we convert to "yngre-nydansk" which matches the Danish
    # values set.
    return text


# --- Metadata block extraction ---

def extract_metadata(html):
    """Extract publication-page metadata blocks. Returns list of dicts."""
    blocks = re.findall(r'<div class="p-4 bg-light"><dl class=row>(.*?)</div>', html, re.DOTALL)
    result = []
    for block in blocks:
        pairs = re.findall(r'<dt[^>]*>([^<]+)</dt>\s*<dd[^>]*>(.*?)</dd>', block, re.DOTALL)
        meta = {}
        for name, val in pairs:
            val_clean = re.sub(r"<[^>]+>", " ", val).strip()
            val_clean = re.sub(r"\s+", " ", val_clean)
            meta[name.strip()] = val_clean
        result.append(meta)
    return result


def extract_text_links(html, book_slug):
    """Return list of /NNN/ text IDs from the publication page, sorted."""
    pattern = r'href=(?:https?://tekstnet\.dk)?/books/' + re.escape(book_slug) + r'/(\d+)/?'
    links = re.findall(pattern, html)
    return sorted(set(links), key=lambda x: int(x))


# --- Title extraction ---

def extract_title_from_title_tag(html):
    """Parse 'Author: Title fra Book (year)' or 'Title' from <title>."""
    m = re.search(r'<title>(.*?)</title>', html)
    if not m:
        return None, None
    raw = m.group(1).strip()
    # Try »...« form first
    m2 = re.search(r'^(?P<author>[^:]+):\s*»(?P<title>[^«]+)«', raw)
    if m2:
        return m2.group("title").strip(), m2.group("author").strip()
    # Split on first ": "
    if ": " in raw:
        author_part, rest = raw.split(": ", 1)
        author = author_part.strip()
        if ", " in rest:
            *book_parts, title_part = rest.rsplit(", ", 1)
            title = title_part.strip()
        else:
            title = rest.strip()
        return title, author
    return raw, None


def extract_title_from_h1(html):
    """Fallback: extract title from <h1> in the text-container region.

    The text-container region may have multiple h1s (e.g. one for a section
    header, one for the actual poem). We look for the LAST non-empty h1
    in the region, which is typically the most specific (closest to the
    body content).

    Strips <small>...</small> subtitles: <h1>Gudstjeneste<br><small>En
    Foraars-Phantasie</small></h1> → 'Gudstjeneste'."""
    m = re.search(r'<div class=text-container>(.*?)(?:<div class=footer|$)', html, re.DOTALL)
    if not m:
        return None
    body = m.group(1)
    candidates = []
    for h_m in re.finditer(r'<h1[^>]*>(.*?)</h1>', body, re.DOTALL):
        inner = h_m.group(1)
        # Remove <small>...</small> subtitles first (Tekstnet uses these for
        # poem subtitles that are part of the heading but not the title)
        inner_no_small = re.sub(r'<small\b[^>]*>.*?</small>', ' ', inner, flags=re.DOTALL)
        # Replace <br> with space before stripping other tags
        inner_no_small = re.sub(r'<br\s*/?>', ' ', inner_no_small)
        text = re.sub(r'<[^>]+>', ' ', inner_no_small)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            candidates.append(text)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Multiple h1s: prefer the last one (most specific), but skip obvious
    # section headers like "Nr. N" or roman numerals
    for text in reversed(candidates):
        if re.match(r'^(Nr\.\s*\d+|I+\.|V+\.|X+\.)$', text):
            continue
        if re.match(r'^(Bog|[Dd]el)\s', text):
            continue
        return text
    return candidates[-1]  # fallback


def extract_title_from_slug(book_slug):
    """Last-resort: extract title from URL slug, stripping the `anon_` prefix."""
    s = book_slug
    if s.startswith("anon_"):
        s = s[5:]
    return s.replace("-", " ").strip()


# --- Apparatus strip ---

APPARATUS_PATTERNS = [
    # Page sigils: <span class=pageBegin>...</span> (handles BOTH quoted and unquoted)
    (r'<span[^>]*class=(?:["\']?)pageBegin[^>]*>.*?</span>', ""),
    # Legacy page-break: <span class=legacy-page-break>...</span>
    (r'<span[^>]*class=(?:["\']?)legacy-page-break[^>]*>.*?</span>', ""),
    # Popover buttons (footnote / critical-note markers)
    (r'<button\b[^>]*\bid=(["\']?)(?:App\d+|n\d+)\1[^>]*>.*?</button>', ""),
    # <sup>, <em>, <strong> tags (editorial emphasis) — keep inner text
    (r'<sup[^>]*>(.*?)</sup>', r"\1"),
    (r'<em[^>]*>(.*?)</em>', r"\1"),
    (r'<strong[^>]*>(.*?)</strong>', r"\1"),
    # <br> tags: in diplomatic editions, the source uses <br> to mark
    # line breaks within a verse line. Since our parser treats each
    # <div class=line> as one body entry, the <br> is just noise. Strip.
    (r'<br[^>]*>', ""),
    # Page-break breadcrumb: <a class=page-break-mark href=...>TEXT</a>
    # (handles both quoted and unquoted)
    (r'<a[^>]*class=(?:["\']?)page-break-mark[^>]*>(.*?)</a>', r"\1"),
]


def strip_apparatus(s):
    """Remove apparatus markup from a body line."""
    for pat, repl in APPARATUS_PATTERNS:
        if callable(repl):
            s = re.sub(pat, repl, s, flags=re.DOTALL)
        else:
            s = re.sub(pat, repl, s, flags=re.DOTALL)
    return s


def clean_text(s):
    """Final text cleaning: unescape entities, normalize whitespace, trim."""
    s = unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# --- Depth-counting element finder ---

def find_matching_close(html, start, open_tag, close_tag):
    """Find the index just past the closing tag that matches the opening at start.
    Counts nested open/close pairs.

    The tricky case: <div and </div can appear as substrings of other tags
    (e.g. <dialog, </dialog). To skip such false matches:
    - For opening tag: skip if the char AFTER < is a letter (so <div doesn't
      match <dialog's <div part — wait no, <div IS the start of <dialog).
      Actually: skip if <div is followed by a letter (e.g. <dialog), because
      the real <div> tag ends with `>`, ` `, `\t`, `\n`, or `/`.
    - For closing tag: skip if the char AFTER </ is a letter (so </div doesn't
      match </dialog's </div part, where `</div` is followed by `alog>`).

    Returns -1 if not found.
    """
    pos = start + len(open_tag)
    depth = 1
    open_pat = re.compile(re.escape(open_tag))
    close_pat = re.compile(re.escape(close_tag))
    while depth > 0 and pos < len(html):
        # Find next opening: <div must NOT be followed by a letter
        # (so <div doesn't match the <div in <dialog, which is a different tag)
        next_open = -1
        for m in open_pat.finditer(html, pos):
            after = m.end()
            if after < len(html) and html[after].isalpha():
                continue  # <div is part of <dialog, <divide, etc.
            next_open = m.start()
            break
        # Find next closing: </div must NOT be followed by a letter
        # (so </div doesn't match the </div in </dialog, </divide, etc.)
        next_close = -1
        for m in close_pat.finditer(html, pos):
            after = m.end()
            if after < len(html) and html[after].isalpha():
                continue  # </div is part of </dialog, </divide, etc.
            next_close = m.start()
            break
        if next_close == -1:
            return -1
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len(open_tag)
        else:
            depth -= 1
            if depth == 0:
                return next_close + len(close_tag)
            pos = next_close + len(close_tag)
    return -1


# --- Body extraction ---

def extract_lines_from_div(html):
    """Extract <div class=line>...</div> contents as a list of (line, stanza_id) tuples.

    Tekstnet wraps each stanza in <div class="mt-3 mb-4">...</div>. We split
    on the stanza wrapper first, then extract lines from each stanza, and
    assign stanza_id starting at 0 for the first wrapper, incrementing for
    each subsequent wrapper. (Dramas use the same wrapper but no stanza-number
    divs — they get the same stanza_id treatment.)

    Lines can contain nested <div>, <button>, etc. (e.g. footnote popover
    buttons with their own <div class='arrow'>). Uses depth-counting to find
    the matching </div> for each <div class=line>.
    """
    lines = []
    # Find all <div class="mt-3 mb-4"> wrapper positions to count stanzas
    stanza_positions = [m.start() for m in re.finditer(r'<div\s+class="mt-3\s+mb-4">', html)]
    if not stanza_positions:
        # No stanza wrappers — treat as one stanza
        stanza_positions = [0]
    # Process each stanza wrapper
    for stanza_idx, stanza_start in enumerate(stanza_positions):
        # Find the end of this stanza (next wrapper, or end of text-container)
        next_idx = stanza_idx + 1
        if next_idx < len(stanza_positions):
            stanza_end = stanza_positions[next_idx]
        else:
            # Find the end of the last stanza (find the closing of the wrapper)
            stanza_end = find_matching_close(html, stanza_start, "<div", "</div>")
            if stanza_end == -1:
                stanza_end = len(html)
        # Extract lines within this stanza
        stanza_html = html[stanza_start:stanza_end]
        for m in re.finditer(r'<div\s+class=line>', stanza_html):
            start = stanza_start + m.start()
            end = find_matching_close(html, start, "<div", "</div>")
            if end == -1:
                content = html[start + len('<div class=line>'):stanza_end]
            else:
                content = html[start + len('<div class=line>'):end - len("</div>")]
            s = strip_apparatus(content)
            s = clean_text(s)
            if s:
                lines.append((s, stanza_idx))
    return lines, bool(lines)


def extract_drama_lines_and_speakers(html):
    """Extract drama body. Returns (lines, marginal_notes_per_stanza, found_any).

    lines: list of (text, stanza_id) tuples.
    marginal_notes_per_stanza: dict mapping stanza_id → list of speaker names
    (only the FIRST speaker per stanza, since the schema's marginal_notes field
    is a flat list per stanza and per-line speaker tracking would require a
    schema change).

    Drama structure (Tekstnet):
        <div class=drama>
          <p class=drama-speaker>SPEAKER1</p>          ← preamble speaker (before any stanza)
          <div class="mt-3 mb-4">                       ← stanza 0 starts
            <div class=drama-line>...</div>
            ...
          </div>
          <p class=drama-speaker>SPEAKER2</p>          ← speaker between stanzas (assigns to next stanza)
          <div class="mt-3 mb-4">                       ← stanza 1 starts
            <div class=drama-line>...</div>
            ...
          </div>
        </div>

    The naive approach (look only inside stanza wrappers) misses the
    preamble speaker. We process the HTML in document order, alternating
    speakers and lines, and track a running stanza_id that increments when
    we encounter a stanza wrapper. A speaker that appears BEFORE the first
    stanza wrapper is assigned to stanza 0 (the first stanza). A speaker
    that appears between two stanzas is assigned to the NEXT stanza.

    Speaker labels may have a leading page-number like "[3] |" or "32 |" —
    we strip these (they're apparatus, not part of the character name).
    """
    lines = []  # (text, stanza_id)
    # Walk the document in order, alternating speakers and lines.
    # Track current stanza_id (starts at 0, increments per <div class="mt-3 mb-4">)
    # Pattern: speaker | drama-line | stanza-wrapper-mark
    # We use a single combined regex with named groups.
    pattern = (
        r'<div\s+class="mt-3\s+mb-4">'
        r'|<p[^>]*class=(?:["\']?)drama-speaker[^>]*>(.*?)</p>'
        r'|<div[^>]*class=(?:["\']?)drama-line[^>]*>'
    )
    current_stanza_id = -1  # increments before each stanza; -1 means "before first stanza"
    notes_per_stanza = {}  # stanza_id → [first_speaker]
    speakers_for_next_stanza = []  # speakers seen between stanzas (assign to next stanza)
    speakers_before_first_stanza = []  # speakers before any stanza (assign to stanza 0)
    saw_first_stanza = False
    for m in re.finditer(pattern, html, re.DOTALL):
        matched_text = m.group(0)
        if matched_text.startswith('<div class="mt-3 mb-4">'):
            # Stanza wrapper — increment and assign any pending speakers
            current_stanza_id += 1
            saw_first_stanza = True
            pending = speakers_for_next_stanza
            speakers_for_next_stanza = []
            if pending:
                # Take only the first speaker for the stanza's notes
                notes_per_stanza.setdefault(current_stanza_id, []).append(pending[0])
        elif matched_text.startswith('<p'):
            # Speaker — strip page-number prefix
            speaker = re.sub(r'<[^>]+>', '', m.group(1))
            speaker = re.sub(r'\s+', ' ', speaker).strip()
            speaker = re.sub(r'^\[\d+\]\s*\|?\s*', '', speaker)
            speaker = re.sub(r'^\d+\s*\|\s*', '', speaker)
            if speaker:
                if not saw_first_stanza:
                    # Before first stanza: assign to stanza 0
                    speakers_before_first_stanza.append(speaker)
                else:
                    # After first stanza: assign to next stanza
                    speakers_for_next_stanza.append(speaker)
        else:
            # Drama line — find content with depth-counting
            start = m.end()
            end = find_matching_close(html, start, "<div", "</div>")
            if end == -1:
                content = html[start:]
            else:
                content = html[start:end - len("</div>")]
            s = strip_apparatus(content)
            s = clean_text(s)
            if s:
                # Use current stanza_id (which is 0 if no stanza wrapper seen yet)
                stanza_id = max(current_stanza_id, 0)
                lines.append((s, stanza_id))
    # If there were speakers before the first stanza, assign them to stanza 0
    if speakers_before_first_stanza:
        notes_per_stanza.setdefault(0, []).insert(0, speakers_before_first_stanza[0])
    return lines, notes_per_stanza, bool(lines or notes_per_stanza)


def extract_prose_as_poem(html):
    """Extract prose-as-poem body. Lines come from <p> tags inside text-container."""
    m = re.search(r'<div class=text-container>(.*?)(?:<div class=footer|$)', html, re.DOTALL)
    if not m:
        return [], False
    body = m.group(1)
    lines = []
    for m in re.finditer(r'<p(?:\s[^>]*)?>', body):
        start = m.end()
        end = find_matching_close(body, start, "<p", "</p>")
        if end == -1:
            content = body[start:]
        else:
            content = body[start:end - len("</p>")]
        s = strip_apparatus(content)
        s = clean_text(s)
        if s:
            lines.append(s)
    return lines, bool(lines)


# --- Body-type detection ---

def detect_body_type(html):
    """Return one of: 'drama', 'line', 'prose', 'unknown'. Drama > line > prose.

    Tekstnet uses unquoted attributes, so we need to handle both
    `class="drama-line"` and `class=drama-line`."""
    has_drama_line = bool(re.search(r'<div[^>]*class=(?:["\']?)drama-line', html))
    has_drama_speaker = bool(re.search(r'<p[^>]*class=(?:["\']?)drama-speaker', html))
    has_line = bool(re.search(r'<div[^>]*class=(?:["\']?)line(?:["\']?)[>\s]', html))
    if has_drama_line or has_drama_speaker:
        return 'drama'
    if has_line:
        return 'line'
    m = re.search(r'<div class=text-container>(.*?)(?:<div class=footer|$)', html, re.DOTALL)
    if m and re.search(r'<p(?:\s[^>]*)?>', m.group(1)):
        return 'prose'
    return 'unknown'


# --- Main parser ---

CORPUS_NAME = "Tekstnet — Det Danske Sprog- og Litteraturselskab"

# Dramatic poems are written to a separate danish-dramas dataset, not poems/.
# The full-scrape script checks for this flag and redirects the output path.
DRAMA_DATASET_DIR = "danish-dramas"
# --- Music-version filter ---

MUSIC_BOOKS_TO_SKIP = {
    # 100% music versions: every /NNN/ entry is a different musical setting
    # of the same poem (per user review 2026-07-03). The "book" itself is not
    # a poem collection — it's a music collection. Skip the entire book.
    "ingemann-bs_aftensang",
    "hauch-c_aftensang",
    "hauch-c_laengsel",
    "hauch-c_sangfuglen",
    "ingemann-bs_pigens-sang",
    "ingemann-bs_mesteren-kommer",
}


def is_music_version_page(html):
    """A /NNN/ page is a music-version entry (per user rule 2026-07-03) if:
    - body contains <div class=metadata> (citation / edition apparatus), AND
    - after stripping that metadata div, the body has NO <div class=line> AND
      NO <div class=drama-line> markup (i.e. the metadata IS the body — no
      actual verse).

    Used at /NNN/ granularity: skip such pages in mixed books like
    jacobsen-jp_gurresange (real poems + 11 music settings).

    The trick: a page like ingemann-bs_aftensang/002/ has BOTH metadata
    (the editorial citation for the 1845 reissue) AND the actual verse
    underneath. We keep that. A page like /007/ has metadata describing the
    music edition but NO verse — we skip it.
    """
    if "<div class=metadata" not in html:
        return False
    # Strip metadata divs and see if any line/drama markup remains in body
    stripped = re.sub(
        r'<div[^>]*class=(?:["\']?)metadata[^>]*>.*?</div>\s*',
        '',
        html, flags=re.DOTALL,
    )
    # Check the text-container specifically
    m = re.search(r'<div class=text-container>(.*?)(?:<div class=footer|$)', stripped, re.DOTALL)
    body = m.group(1) if m else stripped
    has_line = bool(re.search(r'<div[^>]*class=(?:["\']?)line(?:["\']?)[>\s]', body))
    has_drama = bool(re.search(r'<div[^>]*class=(?:["\']?)drama-line', body))
    return not has_line and not has_drama


def page_has_udgivelsesaar(html):
    """Return the Udgivelsesår value if this page has a publication-year field."""
    m = re.search(r'Udgivelsesår\s*</dt>\s*<dd[^>]*>(.*?)</dd>', html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    val = re.sub(r"<[^>]+>", " ", m.group(1))
    val = re.sub(r"\s+", " ", val).strip()
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# --- Breadcrumb extraction ---

def extract_breadcrumbs(html):
    """Return list of (text, href) for breadcrumb nav items.

    Tekstnet uses Bootstrap breadcrumbs:
        <ol class=breadcrumb>
          <li class=breadcrumb-item><a href=/books/<slug>/>Author:\nBookTitle</a></li>
          <li class="breadcrumb-item active"><a href=...>Section:\nPoemTitle</a></li>
        </ol>
    """
    items = []
    m = re.search(r'<ol[^>]*class=[^>]*breadcrumb[^>]*>(.*?)</ol>', html, re.DOTALL | re.IGNORECASE)
    if not m:
        return items
    inner = m.group(1)
    for lm in re.finditer(
        r'<li[^>]*class=[^>]*breadcrumb-item[^>]*>(.*?)</li>',
        inner, re.DOTALL,
    ):
        item_inner = lm.group(1)
        # Extract text + href of the <a>
        am = re.search(r'<a[^>]+href=["\']?([^"\'\s>]+)["\']?[^>]*>(.*?)</a>', item_inner, re.DOTALL)
        if am:
            href = am.group(1)
            text = re.sub(r"<[^>]+>", " ", am.group(2))
            text = re.sub(r"\s+", " ", text).strip()
            items.append((text, href))
        else:
            # Active link without <a> tag (current page)
            text = re.sub(r"<[^>]+>", " ", item_inner)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                items.append((text, ""))
    return items


def split_breadcrumb_for_title(source_text):
    """Split a breadcrumb's text into (author, title).

    Forms observed:
      - 'Author:\\nTitle'       → ('Author', 'Title')
      - 'Author: Title'        → ('Author', 'Title')
      - 'JustTitle' (no sep)   → (None, 'JustTitle')   ← entire thing is the title

    Returns (None, None) for empty/whitespace-only input.
    """
    if not source_text or not source_text.strip():
        return None, None
    if "\n" in source_text:
        a, _, t = source_text.partition("\n")
        a, t = a.strip(), t.strip()
        return (a if a else None), (t if t else None)
    if ":" in source_text:
        a, _, t = source_text.partition(":")
        a, t = a.strip(), t.strip()
        return (a if a else None), (t if t else None)
    # No separator: whole text is the title (e.g. "Gudstjeneste")
    return None, source_text.strip()


SOURCE_ID = "dsl-tekstnet"


def parse_publication_page(html, book_url, book_slug, poem_nnn=None):
    """Parse a publication-index page. Returns metadata dict or None if excluded.

    poem_nnn: if set, this is the specific poem being scraped (for URL
    construction). For Variant B (single-poem books), no /NNN/ suffix is
    added.

    The returned dict has a `forfatter_present` flag (True/False) indicating
    whether the literary "Forfatter" field was actually populated in the
    publication metadata. False means we need to fall back to the page's
    own breadcrumbs / <title> tag to recover the author (Variant B case).
    """
    sprog = extract_sprog_slug(html)
    if not is_danish(sprog):
        return None
    blocks = extract_metadata(html)
    if not blocks:
        return None
    literary = blocks[0]
    editorial = blocks[1] if len(blocks) > 1 else {}
    raw_forfatter = literary.get("Forfatter", "").strip()
    forfatter_present = bool(raw_forfatter) and raw_forfatter.lower() != "anonym"
    if forfatter_present:
        author = raw_forfatter
    else:
        author = "anonymous"
    year_str = literary.get("Udgivelsesår", "").strip()
    try:
        year_pub = int(year_str)
    except (ValueError, TypeError):
        year_pub = None
    # publisher: Tekstnet's "Udgiver" is the digital-edition editor (often a
    # 21st-century literary historian), NOT the historical publisher. Per
    # user rule 2026-07-03, leave this empty for now — we may augment later.
    publisher = None
    source_title = extract_source_title(book_slug)
    text_links = extract_text_links(html, book_slug)
    # Construct the poem-specific URL
    if poem_nnn:
        poem_url = book_url.rstrip("/") + f"/{poem_nnn}/"
    else:
        poem_url = book_url
    return {
        "author": author,
        "forfatter_present": forfatter_present,
        "year_published": year_pub,
        "publisher": publisher,
        "sprog_slug": sprog,
        "source_title": source_title,
        "text_links": text_links,
        "url": poem_url,
    }


def literary_author_from_publication(pub_meta, html):
    """For publication pages where the Forfatter was missing (Variant B
    single-poem books: the metadata block only has editorial credits),
    recover the literary author from the page itself.

    Tries, in order:
      1. Active breadcrumb in form 'Author: Title' (e.g. 'H.C. Andersen: Balvise')
      2. <title> HTML tag in form 'Author: Title' (e.g. 'Carl Ploug: Til de Gamle')
      3. URL slug prefix (e.g. 'andersen-hc' → 'H. C. Andersen' — *approximate*)

    Returns a non-empty author string or None if no signal is found.
    """
    if pub_meta.get("forfatter_present"):
        # The publication page had a real literary Forfatter field; use it.
        return pub_meta.get("author") if pub_meta.get("author") != "anonymous" else None

    # Try the breadcrumbs we already parsed
    breadcrumbs = extract_breadcrumbs(html)
    if breadcrumbs:
        for txt, _ in reversed(breadcrumbs):
            if not txt or txt.lower() in ("bibliotek", "library"):
                continue
            author, _ = split_breadcrumb_for_title(txt)
            if author and author.strip() and author.strip().lower() != "empty":
                return author.strip()

    # Try the <title> tag
    mt = re.search(r"<title>(.*?)</title>", html)
    if mt:
        title_text = mt.group(1).strip()
        author, _ = split_breadcrumb_for_title(title_text)
        if author and author.strip() and author.strip().lower() != "empty":
            return author.strip()

    # Last fallback: URL slug prefix → approximate name
    # NOTE: this is a *guess* and may need manual correction. The slug
    # encodes only the lastname + initials (e.g. 'andersen-hc' → 'H.C. Andersen'
    # is reasonable; 'hr-michael' → 'Hr. Michael' is also reasonable).
    # We return None here rather than guess, so the caller can mark these
    # as needing manual review.
    return None


def parse_poem_page(html, book_slug, pub_meta, is_diplomatic=False, poem_nnn=None):
    """Parse a poem page. Returns a schema-compliant dict or None.

    Title resolution (per user rule, 2026-07-03 review):
      1. Active breadcrumb (last item of breadcrumb list) — section:poem title
         text after the last ":" / newline is the poem title.
      2. <h1> in text-container — strip page-sigil prefix like "33| ".
      3. <title> HTML tag — parse "Author: ... Title ..., Book (year)" form.
    Source.title (the publication collection title):
      - For collection-part pages: first breadcrumb item ("Author: BookTitle"
        → strip the "Author: " prefix to get the book title).
      - For standalone pages: no publication context, leave empty.
    Year_published for the SOURCE object (the book publication year):
      - Collection-part: from pub_meta (year_published set by publication page).
      - Standalone: from the page's own Udgivelsesår block.

    Other filters:
      - Music-version skip: if has_metadata AND no line/drama markup after
        stripping metadata, return None.
      - Single-line skip (non-prose only).
    """
    # === Music-version skip (must come first) ===
    if is_music_version_page(html):
        return None

    # === Title and source.title from breadcrumbs ===
    breadcrumbs = extract_breadcrumbs(html)
    title = None
    source_title = None

    if len(breadcrumbs) >= 2:
        # Last item is the active crumb: typically "Section: PoemTitle" or "Author: PoemTitle"
        active_text = breadcrumbs[-1][0]
        # Pick the first *meaningful* (non-library) breadcrumb as the source.
        # Library crumb is the canonical "bibliotek" / "library" home link.
        # We skip it when present.
        first_text = breadcrumbs[0][0]
        skip_indices = set()
        for i, (txt, _) in enumerate(breadcrumbs):
            if txt.lower() in ("bibliotek", "library"):
                skip_indices.add(i)
        # First meaningful breadcrumb (could be index 0 if no library crumb)
        meaningful = [(i, t, h) for i, (t, h) in enumerate(breadcrumbs) if i not in skip_indices]
        if len(meaningful) >= 2:
            # Collection-part: ≥ 2 meaningful breadcrumbs. First is publication.
            first_text = meaningful[0][1]
        elif len(meaningful) == 1:
            # Standalone: only the active breadcrumb is meaningful.
            first_text = None  # No publication title

        # Active breadcrumb: extract poem title (after the ":" or newline).
        # If the active breadcrumb is empty or just ":", skip (Tekstnet data hole).
        if active_text and active_text.strip() and active_text.strip() != ":":
            _, t = split_breadcrumb_for_title(active_text)
            title = t

        # First breadcrumb: extract book title (after the ":" or newline),
        # then strip any author prefix added by Tekstnet's "Author: BookTitle" form.
        if first_text:
            _, book_title = split_breadcrumb_for_title(first_text)
            if book_title:
                source_title = book_title

    # === Title fallback: <h1> in text-container (strip page-sigil prefix) ===
    if not title:
        h1_title = extract_title_from_h1(html)
        if h1_title:
            # Strip page-sigil prefixes like "33 | ", "32 | ", "[7]|", "[33] | ".
            # Handles: leading digits, optional "[", optional whitespace, "|", optional "]".
            h1_clean = re.sub(r"^[\[]?\d+[\]]?\s*\|?\s*", "", h1_title).strip()
            title = h1_clean

    # === Title fallback: <title> HTML tag ===
    # Skip the <title> fallback if it ends with empty title (trailing ", "),
    # because that's a Tekstnet data hole — the whole rest is the book title.
    if not title or title.lower().startswith("empty:"):
        t, _ = extract_title_from_title_tag(html)
        if t and not t.lower().startswith("empty:"):
            raw_title = re.search(r"<title>(.*?)</title>", html)
            if raw_title and not raw_title.group(1).rstrip().endswith(","):
                title = t

    # === Title fallback: URL slug ===
    # If all sources gave a Roman-numeral-only / section-number-only result
    # (e.g. "III.", "IV.", "Nr. 1"), Tekstnet didn't fill in the title —
    # leave the section number as-is rather than propagating the slug.
    if not title or re.match(r'^(Nr\.\s*\d+|I+\.|IV\.|V[I]*\.|VI+\.|IX\.|X\.|XL?\.|L\.|C\.|D\.|M\.?)$', title or '', re.IGNORECASE):
        # Roman numeral only — keep the section number as the title; the user
        # can manually correct later. Don't fall through to the URL slug
        # (which would just be the publication slug).
        pass

    # Strip "Nr. N." prefix and "empty:" placeholders
    if title:
        title = re.sub(r"^Nr\.\s*\d+\.?\s*", "", title).strip()
        if title.lower().startswith("empty:") or title.lower() == "empty":
            title = extract_title_from_slug(book_slug)

    if not title:
        return None

    # === Body extraction ===
    body_type = detect_body_type(html)
    if body_type == "drama":
        body_lines_stanzas, notes_per_stanza, _ = extract_drama_lines_and_speakers(html)
        body_lines = [(t, s) for t, s in body_lines_stanzas]
    elif body_type == "line":
        body_lines, _ = extract_lines_from_div(html)
        notes_per_stanza = {}
    elif body_type == "prose":
        prose_lines, _ = extract_prose_as_poem(html)
        body_lines = [(t, 0) for t in prose_lines]
        notes_per_stanza = {}
    else:
        return None
    if not body_lines:
        return None
    if body_type != "prose" and len(body_lines) == 1:
        return None

    body = []
    for i, (line, stanza_id) in enumerate(body_lines):
        # Drama: speaker notes attach to the FIRST line of each stanza only
        if body_type == "drama":
            if i == 0 or body_lines[i-1][1] != stanza_id:
                all_speakers = notes_per_stanza.get(stanza_id, [])
                marginal_notes = (
                    [f"Speaker: {s}" for s in all_speakers[:1]] if all_speakers else []
                )
            else:
                marginal_notes = []
        else:
            marginal_notes = []

        body.append({
            "id": i,
            "stanza_id": stanza_id,
            "text": line,
            "part": False,
            "marginal_notes": marginal_notes,
        })

    # === Year source: standalone page reads Udgivelsesår from THIS page ===
    page_year = page_has_udgivelsesaar(html)
    if page_year is not None:
        source_year = page_year
        year_created = page_year
    else:
        source_year = pub_meta.get("year_published")
        year_created = pub_meta.get("year_published")

    # === Standalone detection (page-type discrimination) ===
    # A page is standalone (Variant B: single-poem book) if it has only 1
    # user-facing breadcrumb (active) after skipping the library/home link.
    # A page is collection-part (Variant A: poem within a multi-poem book)
    # if it has 2+ breadcrumb items beyond the library link.
    meaningful_breadcrumbs = len(breadcrumbs)
    if len(breadcrumbs) >= 1 and breadcrumbs[0][0].lower() in ("bibliotek", "library"):
        meaningful_breadcrumbs -= 1
    is_standalone = meaningful_breadcrumbs <= 1

    # === Resolve author for standalone (Variant B) pages ===
    # For standalone pages, the pub_meta author comes from the publication
    # metadata block which only has editorial credits (Hovedredaktør etc.),
    # not the literary author. The literary author IS encoded in either
    # the <title> tag (e.g. "H.C. Andersen: ...") or in the active
    # breadcrumb ("H.C. Andersen: Title"). Try both before falling back
    # to the pub_meta value.
    resolved_author = pub_meta.get("author", "anonymous")
    pub_author_from_meta = literary_author_from_publication(pub_meta, html)
    if pub_author_from_meta:
        resolved_author = pub_author_from_meta
    # Final normalization: convert Danish "Anonym"/"anonym" to English
    # "anonymous" for consistency across the dataset (user rule 2026-07-06).
    if resolved_author and resolved_author.lower() in ("anonym", "anonymous"):
        resolved_author = "anonymous"

    # === URL construction ===
    poem_url = pub_meta["url"]
    if poem_nnn and not re.search(f"/{re.escape(poem_nnn)}/?$", poem_url):
        base = poem_url.rstrip("/")
        poem_url = f"{base}/{poem_nnn}/"

    # === Output JSON ===
    json_obj = {
        "id": None,
        "title": title,
        "year_created": year_created,
        "neighbors": None,
        "duplicate": False,
        "locations": False,
        "author": {"name": resolved_author, "country": None},
        "source": {
            "corpus": CORPUS_NAME,
            "title": source_title.title() if source_title else None,
            "publisher": pub_meta.get("publisher"),
            "printer": None,
            "place": None,
            "year_published": source_year,
            "url": poem_url,
        },
        "body": body,
    }
    if is_diplomatic:
        json_obj["diplomatic_edition"] = True
    if body_type == "drama":
        json_obj["dramatic_poem"] = True
    return json_obj
