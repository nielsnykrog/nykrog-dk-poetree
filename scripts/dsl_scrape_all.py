"""
dsl_scrape_all.py -- run the DSL parser across every poem-bearing page
discovered by dsl_discover.py, writing one JSON file per poem to poems/.

Reads:   sources/dsl-reformationssalmer/discovery/<book-slug>.json
         sources/dsl-reformationssalmer/raw/*.html
Writes:  poems/<source>--<author>--<title>--<book>.json

Duplicate-handling: if two pages in the same book produce the same
filename (e.g. same first-verse-line), append an incrementing suffix
--2, --3, ... to disambiguate. Also writes a per-book scrape log so
we know what happened to every page.

Concurrency: 4 workers (be polite to DSL).
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Import the parser
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dsl_parser import build_poem, clean_html, is_poem_page, slugify, make_filename

DEFAULT_RAW   = Path(r"C:\Users\niels\Documents\nykrog-dk-poetree\sources\dsl-reformationssalmer\raw")
DEFAULT_DISC  = Path(r"C:\Users\niels\Documents\nykrog-dk-poetree\sources\dsl-reformationssalmer\discovery")
DEFAULT_OUT   = Path(r"C:\Users\niels\Documents\nykrog-dk-poetree\poems")
DEFAULT_MANIF = Path(r"C:\Users\niels\Documents\nykrog-dk-poetree\sources\dsl-reformationssalmer\manifest.json")
DEFAULT_SRC_ID = "dsl-reformationssalmer"


def safe_slug(url: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '_', url.replace('https://', '').replace('http://', ''))
    return s.strip('_')


def parse_one_page(page_info: dict, book: dict, source_id: str) -> dict:
    """Parse one poem-bearing page into a poem dict. Returns {ok, poem, path, ...}."""
    url = page_info['url']
    cache = DEFAULT_RAW / f"{safe_slug(url)}.html"
    if not cache.exists():
        return {"ok": False, "url": url, "error": "no cache file"}
    try:
        html = cache.read_text(encoding='utf-8')
        html = clean_html(html)
        if not is_poem_page(html):
            return {"ok": False, "url": url, "error": "not a poem page (0 .poetry divs)"}
        poem = build_poem(html, book, url)
        author_slug = slugify(poem['author']['name'])
        title_slug = slugify(poem['title'])
        fname = make_filename(source_id, author_slug, title_slug, book['slug'])
        return {"ok": True, "poem": poem, "url": url, "filename": fname, "stanzas": len({ln['stanza_id'] for ln in poem['body']}), "lines": len(poem['body'])}
    except Exception as e:
        return {"ok": False, "url": url, "error": f"{type(e).__name__}: {e}"}


def main():
    manifest = json.loads(DEFAULT_MANIF.read_text(encoding='utf-8'))
    books = {b['slug']: b for b in manifest['books']}

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    scrape_log = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "per_book": {}}

    # Get all discovery files
    disc_files = sorted(DEFAULT_DISC.glob('*.json'))
    if not disc_files:
        print("No discovery files found. Run dsl_discover.py first.")
        sys.exit(1)

    # Aggregate all poem-bearing pages across all books
    all_jobs = []
    for disc_path in disc_files:
        data = json.loads(disc_path.read_text(encoding='utf-8'))
        slug = data['book_slug']
        if slug not in books:
            print(f"  skip {slug}: not in manifest")
            continue
        book = books[slug]
        for page in data['pages']:
            if page.get('n_poetry', 0) > 0:
                all_jobs.append((page, book))

    print(f"Total poem-bearing pages to parse: {len(all_jobs)}")
    print(f"Source id: {DEFAULT_SRC_ID}")
    print()

    # Track used filenames in poems/ to detect collisions
    used_filenames = set()
    # Pre-populate with what's already in poems/ (the 3 pilot)
    for f in DEFAULT_OUT.glob('*.json'):
        used_filenames.add(f.name)

    # Process with concurrency
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(parse_one_page, page, book, DEFAULT_SRC_ID): (page['url'], book['slug'])
                   for page, book in all_jobs}
        done = 0
        for fut in as_completed(futures):
            url, slug = futures[fut]
            done += 1
            r = fut.result()
            r['book_slug'] = slug
            results.append(r)
            if done % 25 == 0:
                ok = sum(1 for x in results if x['ok'])
                print(f"  ... {done}/{len(all_jobs)} done, {ok} ok so far", flush=True)

    # Now write outputs, handling filename collisions
    written = 0
    failed = []
    n_collisions = 0
    for r in results:
        if not r['ok']:
            failed.append(r)
            continue
        fname = r['filename']
        # Detect collision (filename already in used_filenames)
        if fname in used_filenames:
            n_collisions += 1
            stem = fname[:-5]   # drop .json
            for i in range(2, 100):
                candidate = f"{stem}--{i}.json"
                if candidate not in used_filenames:
                    fname = candidate
                    break
        out_path = DEFAULT_OUT / fname
        out_path.write_text(json.dumps(r['poem'], ensure_ascii=False, indent=2), encoding='utf-8')
        used_filenames.add(fname)
        r['written_path'] = str(out_path)
        r['written_filename'] = fname
        written += 1

    print()
    print(f"Wrote {written} poem JSON files to {DEFAULT_OUT}")
    print(f"Failed: {len(failed)}")
    print(f"Filename collisions resolved: {n_collisions}")

    # Write the per-book + overall scrape log
    log = {
        "started_at": scrape_log['started_at'],
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_pages_attempted": len(results),
        "total_ok": written,
        "total_failed": len(failed),
        "filename_collisions": n_collisions,
        "per_book": {},
    }
    for r in results:
        slug = r['book_slug']
        log['per_book'].setdefault(slug, {"ok": 0, "failed": 0, "failures": []})
        if r['ok']:
            log['per_book'][slug]['ok'] += 1
        else:
            log['per_book'][slug]['failed'] += 1
            log['per_book'][slug]['failures'].append({"url": r['url'], "error": r['error']})
    log_path = Path(r"C:\Users\niels\Documents\nykrog-dk-poetree\sources\dsl-reformationssalmer\scrape_log.json")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved scrape log to {log_path}")

    # Per-book summary
    print()
    print("Per-book summary:")
    for slug, info in sorted(log['per_book'].items()):
        print(f"  {slug:35s}  ok={info['ok']:4d}  failed={info['failed']:3d}")

    return 0 if not failed else 0   # don't fail on per-page errors


if __name__ == "__main__":
    sys.exit(main())