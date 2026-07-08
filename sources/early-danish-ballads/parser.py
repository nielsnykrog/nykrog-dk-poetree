"""
early-danish-ballads parser — v6.2
v6 changes (2026-07-03, after Langebeks Kvart pilot review):
  - stanza_id is ZERO-based: the first stanza's lines have stanza_id=0.
    Initial state is -1 ("no stanza started yet"). First stanza-number
    row seen: bumps to 0. Subsequent rows: += 1. After all parsing,
    stanza_ids are renumbered to be contiguous 0..N-1 (so a purely
    decorative dropped stanza doesn't leave a gap). Schema line 114 is
    explicit: zero-based indexing.
  - Drop a line whose post-strip content is just decorative sigils or
    punctuation. Specifically: if the line's only non-whitespace
    characters are drawn from {*, |, :, (, ), ?, !, [, ], <, >}, drop
    it. Letters, digits, and dashes are ALWAYS preserved (dashes have
    long pre-modernist uses as emphasis markers, so we accept some
    noise rather than strip). Dataset serves analysis, not manuscript
    facsimile. Mid-line sigils stay. Re-confirmed 2026-07-03: pragmatic
    data-cleanliness rule, suitable for early-modern corpora.
  - Stanza-number detection now matches three HTML forms:
    `<br/>[N]` (most common; sometimes followed by a tooltip),
    `<br/>N</td>` (bare number, e.g. LNGK10), and
    `<br/>N.</td>` (number with trailing period, e.g. DRS86 —
    Dronning Sophia's standard stanza marker). All N-forms can
    have an optional tooltip div between the number and </td>.

v6.1 changes (2026-07-03):
  - FINIS strip is now case-insensitive (catches `finis`, `Finis` etc.).
    Found 3 such lines in Langebek that v6 missed.
  - Manuscript-end marker strip now also catches `Fenis` (Swedish-influenced
    scribal variant of `Finis`, found in DRS86). Other future variants can
    be added to the same list.

v6.2 changes (2026-07-03, after full corpus scrape):
  - Editorial letter-insertion regex widened from {1,5} to {1,12} chars.
    New manuscripts (especially Svaning I/II) have multi-letter
    insertions up to 9 chars (e.g. `<smaadreng>`, `<Biørnn>`). The
    previous limit was set on the Langebek pilot and missed these.
  - Added `<kommentar ...>` strip rule. Karen Brahes (KBRA) has
    unclosed `<kommentar type="projekt">` tags that close via
    `</span></div>` in the source HTML — strip the opening tag plus
    everything up to the next `</span></div>` boundary.

v5b cleaning rules otherwise unchanged.
"""
import re, unicodedata
from html import unescape


def slugify(s, maxlen=80):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^\w\-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:maxlen]


def parse_date(s):
    """Returns (kind, value) for a date string from the manuscript index.
    kind: 'empty' | 'int' | 'list' | 'malformed'.
    Locks per user instructions (2026-07-02)."""
    if s is None:
        return ("empty", None)
    s = s.strip()
    if not s:
        return ("empty", None)
    m = re.fullmatch(r"\d{3,4}", s)
    if m:
        return ("int", int(s))
    m = re.fullmatch(r"(Før|Efter)\s+(\d{3,4})", s)
    if m:
        return ("int", int(m.group(2)))
    m = re.fullmatch(r"(\d{3,4})\s*-\s*(\d{3,4})", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > b:
            a, b = b, a
        return ("list", [a, b])
    m = re.fullmatch(r"(\d{3,4})'?erne", s, flags=re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return ("list", [n, n + 9])
    return ("malformed", s)


def apply_to_schema(kind, val):
    """Returns (year_created, year_published)."""
    if kind in ("empty", "malformed"):
        return (None, None)
    if kind == "int":
        return (val, val)
    if kind == "list":
        return (val, val[-1])


def fix_mojibake(s):
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


def clean_source_text(s):
    """v5b cleaning rules (in order):
      1. strip <sup>...</sup>
      2. loop-strip <div class="tooltip">...</div> and orphan <span class="tooltiptext|tooltip">...</span>
      3. strip <em>...</em>, keep inner letters
      4. strip <span class="layout">...</span>
      5. drop word FINIS
      6. [-]  ->  -                   (R4: keep the editorial hyphen)
      7. <[letter]{1,5}>  -> letter   (R2: editorial letter-insertion)
      8. [(content)]  -> content      (R1: editorial bracket around supplied word/phrase)
      9. collapse whitespace, trim
     10. unescape HTML entities
    """
    s = re.sub(r"<sup[^>]*>.*?</sup>", "", s, flags=re.DOTALL)
    prev = None
    while s != prev:
        prev = s
        s = re.sub(
            r'<div\b[^>]*class="[^"]*tooltip[^"]*"[^>]*>(?:(?!</div>).)*?</div>',
            "", s, flags=re.DOTALL,
        )
        s = re.sub(
            r'<span\b[^>]*class="[^"]*tooltiptext[^"]*"[^>]*>(?:(?!</span>).)*?</span>',
            "", s, flags=re.DOTALL,
        )
        s = re.sub(
            r'<span\b[^>]*class="[^"]*tooltip[^"]*"[^>]*>(?:(?!</span>).)*?</span>',
            "", s, flags=re.DOTALL,
        )
    s = re.sub(r"<em[^>]*>(.*?)</em>", r"\1", s, flags=re.DOTALL)
    s = re.sub(
        r'<span\b[^>]*class="[^"]*layout[^"]*"[^>]*>(?:(?!</span>).)*?</span>',
        "", s, flags=re.DOTALL,
    )
    # Manuscript-end markers: a small known-variants list, case-insensitive.
    # The classical Latin form is `FINIS`; `finis`/`Finis` cover case
    # variants; `Fenis` is a Swedish-influenced scribal form seen in
    # Dronning Sophia (DRS86). Each marker is stripped as a whole word
    # so that real words containing "finis" as a substring (none
    # expected in this corpus, but defensive) are preserved.
    for marker in ("FINIS", "FENIS"):
        s = re.sub(rf"\b{marker}\b", "", s, flags=re.IGNORECASE).strip()
    # <kommentar ...> strip: Karen Brahes has unclosed kommentar tags
    # that close via </span></div> in the source HTML. The kommentar
    # content is editorial apparatus ([Sic hs.], printer's notes, etc.)
    # and never belongs in the body text.
    s = re.sub(
        r'<kommentar\b[^>]*>(?:(?!</span>|</div>).)*</span>',
        "", s, flags=re.DOTALL,
    )
    # Editorial letter/word insertion regex: matches <letters>, optionally
    # containing internal hyphens. The hyphen is the 16th-c compound marker
    # (e.g. <brude-bench>, <sølle-spente>, <feste-mand>) — present in
    # Svaning I/II but absent from the Langebek pilot. The hyphen inside
    # the marker is the editorial one, so we strip it along with the
    # brackets (consistent with R4 `[-]` → `-`). Width {1,15} covers the
    # longest multi-letter insertions seen in Svaning I/II (up to 12 chars).
    # NOTE: explicit char class (NOT an f-string with [{LETTER}-] — that
    # produced double brackets due to f-string escaping).
    s = re.sub(
        r"<([a-zæøåA-ZÆØÅ][a-zæøåA-ZÆØÅ-]{0,14})>",
        lambda m: m.group(1),
        s, flags=re.IGNORECASE,
    )
    s = re.sub(r"\[([^\[\]]+?)\]", r"\1", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    # unescape FIRST so entities like &#x3C; become literal < before our editor-markup regex
    s = unescape(s)
    # ... but un-escape may re-introduce angle brackets for editorial letter insertions.
    # Re-run the angle-letter rule now that they're literal.
    s = re.sub(
        r"<([a-zæøåA-ZÆØÅ][a-zæøåA-ZÆØÅ-]{0,14})>",
        lambda m: m.group(1),
        s, flags=re.IGNORECASE,
    )
    # Same for square-bracket editor-content (may have entered via entities)
    s = re.sub(r"\[([^\[\]]+?)\]", r"\1", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def extract_title(body):
    """Extract 'Titel: ...' from the metadata block. Drop outer parens."""
    m = re.search(
        r"<b>\s*Titel:\s*</b>\s*(.*?)(?:<br\s*/?>|<b>|$)", body, re.DOTALL
    )
    if not m:
        return None
    raw = m.group(1)
    title = re.sub(r"<[^>]+>", "", raw)
    title = unescape(title).strip()
    m2 = re.match(r"^\((.*)\)$", title, re.DOTALL)
    if m2:
        title = m2.group(1).strip()
    return title


def parse_poem(html):
    """Parse one poem HTML to (title, body_lines, errors).

    body_lines entries: {id, stanza_id, text, part:False, marginal_notes:[]}
    """
    body = fix_mojibake(html)
    title = extract_title(body)
    table_match = re.search(
        r"<table[^>]*>(.*?)</table>", body, re.DOTALL | re.IGNORECASE
    )
    if not table_match:
        return title, [], []
    table = table_match.group(1)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL | re.IGNORECASE)
    lines, errors = [], []
    # Zero-based stanza_id. The first stanza's lines get stanza_id=0.
    # State machine:
    #   - stanza_id starts at -1 (no stanza started yet)
    #   - first stanza-number row seen: stanza_id becomes 0 (entering stanza 0)
    #   - subsequent stanza-number rows: stanza_id += 1
    #   - lines emitted between markers belong to the current stanza_id
    #   - lines emitted BEFORE any marker (rare: e.g. LNGK37, LNGK92)
    #     belong to an implicit stanza 0 — bump from -1 to 0 on first emit.
    stanza_id, line_id = -1, 0
    for r in rows:
        text_only = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", r)).strip()
        is_empty_break = re.fullmatch(
            r"(<br\s*/?>\s*)+", r.strip()
        ) or re.fullmatch(r"\s*<br\s*/?>\s*", r, flags=re.IGNORECASE)
        if is_empty_break:
            continue
        # Stanza-number row: contains a stanza marker. Three HTML forms observed
        # in the corpus so far:
        #   1. <br/>[N] (most common; sometimes followed by a footnote tooltip)
        #      — e.g. LNGK16's `<td><br/>[1]<div class="tooltip">...</div></td>`
        #   2. <br/>N</td> (bare number, e.g. LNGK10)
        #   3. <br/>N.</td> (number with trailing period, e.g. DRS86's
        #      `<td><br/>1.</td>` — Dronning Sophia's standard form)
        # Both the N-form and N.-form can have an optional tooltip div
        # between the number and the closing </td>. The marker must be the
        # only meaningful content of the cell (no source span, no prose).
        is_stanza_number = bool(
            re.search(r"<br\s*/?>\s*\[(\d+)\]", r)
            or re.search(
                r"<br\s*/?>\s*(\d+)\.?\s*"
                r"(?:<div\b[^>]*class=\"[^\"]*tooltip"
                r"[^\"]*\"[^>]*>.*?</div>\s*)?</td>",
                r, flags=re.DOTALL,
            )
        )
        if is_stanza_number:
            # First marker: -1 -> 0 (entering stanza 0).
            # Subsequent markers: bump by 1 (entering stanza 1, 2, ...).
            stanza_id += 1
            continue
        # Source span anchored on </span>&nbsp;</td> to avoid inner-tag non-greedy bug
        src_match = re.search(
            r'<span class="source">(.*?)</span>(?:&nbsp;)?</td>', r, re.DOTALL
        )
        if not src_match:
            continue
        text = clean_source_text(src_match.group(1))
        if not text:
            continue
        # v6: drop a line whose post-strip content is purely decorative sigils
        # or punctuation. The "decorative-only" set is the explicit
        # punctuation/sigil chars {*, |, :, (, ), ?, !, [, ], <, >}.
        # Letters, digits, and dashes are NEVER considered decorative —
        # dashes have pre-modernist uses as emphasis markers, so we
        # accept possible noise rather than strip them. Mid-line sigils
        # stay (e.g. `|` at end of a real verse line is preserved).
        if re.fullmatch(r"[\s\*\|:\(\)\?\!\[\]\<\>]*", text):
            continue
        # If no stanza-number row has appeared yet, this line begins the
        # implicit first stanza (id 0). Bump from -1 to 0 once.
        if stanza_id == -1:
            stanza_id = 0
        lines.append({
            "id": line_id,
            "stanza_id": stanza_id,
            "text": text,
            "part": False,
            "marginal_notes": [],
        })
        line_id += 1
    # v6: renumber stanza_ids contiguously 0..N-1. If the source had an
    # implicit or purely-decorative stanza at the start that got dropped
    # (e.g. LNGK62A's `[*]` row before the first real stanza), the
    # remaining stanzas compress down so stanza_ids are always 0..N-1
    # with no gaps. Preserves no source-structure info, but produces
    # clean contiguous indices for downstream analysis — the user's stated
    # goal is a useful dataset, not a manuscript facsimile.
    kept_stanza_ids = sorted({L["stanza_id"] for L in lines})
    if kept_stanza_ids != list(range(len(kept_stanza_ids))):
        remap = {old: new for new, old in enumerate(kept_stanza_ids)}
        for L in lines:
            L["stanza_id"] = remap[L["stanza_id"]]
    return title, lines, errors
