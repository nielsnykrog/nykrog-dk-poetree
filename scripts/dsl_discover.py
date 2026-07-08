"""
dsl_discover.py -- enumerate all (chapter, verse) URLs in a DSL book,
fetch and cache each one, and report which pages contain poems.

Strategy:
  1. Fetch the book's first page (e.g. /<slug>/1/1).
  2. Extract every data-ajax-url from it -- this gives the full table of contents
     (every chapter/verse DSL knows about for that book).
  3. Fetch each one (if not already cached), cache under sources/.../raw/.
  4. Probe each: poem-bearing iff >= 1 <div class="poetry">.
  5. Write a manifest:<slug>.json with:
     - list of all URLs
     - which are poem-bearing
     - per-poem count of stanzas + verse-lines (from a quick <div>-count scan)

This is intentionally conservative: we don't PARSE here, just discover and count.
"""

import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_BASE = "https://salmer.dsl.dk"
DEFAULT_RAW  = Path(r"C:\Users\niels\Documents\nykrog-dk-poetry\sources\dsl-reformationssalmer\raw")
DEFAULT_OUT  = Path(r"C:\Users\niels\Documents\nykrog-dk-poetry\sources\dsl-reformationssalmer\discovery")


def fetch(url: str, cache_path: Path, max_retries: int = 3) -> bytes:
    """Fetch a URL, caching to disk. Skip if already cached. Retries with backoff."""
    if cache_path.exists():
        return cache_path.read_bytes()
    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nykrog-dk-poetry-discover/1.0"})
            body = urllib.request.urlopen(req, timeout=60).read()
            cache_path.write_bytes(body)
            return body
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (2 ** attempt))
    raise last_err


def safe_slug(url: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '_', url.replace('https://', '').replace('http://', ''))
    return s.strip('_')


def discover_urls(book_slug: str) -> list:
    """Return the list of all <chapter>/<verse> URLs for a book, in stable order.
    Walks the book's first page to find every data-ajax-url.
    """
    raw_dir = DEFAULT_RAW
    first_url = f"{DEFAULT_BASE}/{book_slug}/1/1"
    body = fetch(first_url, raw_dir / f"{safe_slug(first_url)}.html")
    html = body.decode('utf-8', errors='replace')

    urls = set()
    for m in re.finditer(r'data-ajax-url="(/[^"]+)"', html):
        urls.add(m.group(1))

    # Filter: only keep paths under our book-slug. Strip query strings.
    filtered = []
    for u in sorted(urls):
        # Remove any query
        path = u.split('?')[0]
        if path.startswith(f'/{book_slug}/') and path != f'/{book_slug}':
            filtered.append(path)
    return filtered


def probe(html_bytes: bytes) -> tuple:
    """Return (n_poetry, n_verse_line) counts in the page."""
    html = html_bytes.decode('utf-8', errors='replace')
    # Strip script/style first
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    n_p = len(re.findall(r'<div[^>]+class="[^"]*\bpoetry\b[^"]*"', html))
    n_v = len(re.findall(r'<div[^>]+class="[^"]*\bverse-line\b[^"]*"', html))
    return n_p, n_v


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-slug", required=True, action='append',
                    help="Book slug (e.g. dietz-salmebog-1529). Repeat for multiple.")
    args = ap.parse_args()

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    for slug in args.book_slug:
        print(f"\n=== {slug} ===")
        urls = discover_urls(slug)
        print(f"  discovered {len(urls)} URLs")

        results = []
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {}
            for path in urls:
                full = f"{DEFAULT_BASE}{path}"
                cache = DEFAULT_RAW / f"{safe_slug(full)}.html"
                futures[ex.submit(fetch, full, cache)] = path

            done = 0
            for fut in as_completed(futures):
                path = futures[fut]
                done += 1
                try:
                    body = fut.result()
                    n_p, n_v = probe(body)
                    full = f"{DEFAULT_BASE}{path}"
                    cache = DEFAULT_RAW / f"{safe_slug(full)}.html"
                    results.append({"path": path, "url": full,
                                    "n_poetry": n_p, "n_verse_line": n_v,
                                    "cached": str(cache.relative_to(DEFAULT_RAW.parent.parent))})
                except Exception as e:
                    print(f"  FAIL {path}: {e}")
                    results.append({"path": path, "url": f"{DEFAULT_BASE}{path}", "error": str(e)})
                if done % 25 == 0:
                    print(f"  ... {done}/{len(urls)} done", flush=True)

        n_poem_pages = sum(1 for r in results if r.get('n_poetry', 0) > 0)
        n_poems = sum(r.get('n_poetry', 0) for r in results)
        n_lines = sum(r.get('n_verse_line', 0) for r in results)
        print(f"  → {n_poem_pages}/{len(results)} pages have poems")
        print(f"  → {n_poems} total <div class=\"poetry\"> blocks across the book")
        print(f"  → {n_lines} total <div class=\"verse-line\"> blocks across the book")

        # Anomaly flagging: pages that have verse-line but no poetry, or vice versa
        anomalies = [r for r in results
                     if (r.get('n_verse_line', 0) > 0 and r.get('n_poetry', 0) == 0)
                     or (r.get('n_poetry', 0) > 0 and r.get('n_verse_line', 0) == 0)]
        if anomalies:
            print(f"  ⚠️  {len(anomalies)} anomalous pages (verse-line without poetry, or vice versa):")
            for r in anomalies:
                print(f"      {r['path']}: poetry={r.get('n_poetry')}, verse-line={r.get('n_verse_line')}")

        # Save per-book discovery file
        out = DEFAULT_OUT / f"{slug}.json"
        out.write_text(json.dumps({
            "book_slug": slug,
            "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_urls": len(results),
            "n_poem_pages": n_poem_pages,
            "n_poems_total": n_poems,
            "n_verse_lines_total": n_lines,
            "n_anomalies": len(anomalies),
            "pages": results,
        }, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"  saved {out}")


if __name__ == "__main__":
    main()