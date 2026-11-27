# Project-local extensions and conventions beyond the PoeTree schema

This file documents places where this dataset deviates from or extends
`poetree.schema.json`. It is the reference for discussions with the PoeTree
working group about which of these should be upstreamed.

## `source.url` (extension)

`string`. The live URL of the individual source page this poem was taken from.
Reader convenience; not in PoeTree core.

## `source.editor` (extension, added 2026-11-27)

`string | null`. The person who **collected / compiled / edited** the contents of
the source book and brought them to a printer. Filled for `dsl-reformationssalmer`
only, from DSL's *udgiver* metadata. Other corpora do not carry the key.

## `source.publisher` — convention for 16th-century books

PoeTree core field (`str|None`, "name of the publisher"). For early-modern prints
we follow standard bibliographic practice and treat the **printer-publisher** — the
person who owned the press and produced the physical book — as the publisher.
This keeps `publisher` semantically consistent across the corpus: Lorenz Benedicht
(1569) and Gyldendal (1869) both fit "the entity that produced the book".

Where the compiler and the printer were the same person (Ludwig Dietz, Hans Vingaard,
Oluf Ulriksen), the name legitimately appears in **both** `editor` and `publisher`.

### History

Until 2026-11-27 the two roles were stored under the wrong labels: DSL's *udgiver*
was written to `publisher` and DSL's *trykker* to a local `printer` field. The
migration `scripts/remap_dsl_publisher.py` moved `publisher` → `editor` and
`printer` → `publisher`, and retired `printer`.

### Name harmonisation

DSL's pages spell one printer two ways. We normalise to the form used in our
book slugs:

| DSL spelling | Canonical | Files |
|---|---|---|
| `Oluf Ulricksøn` | `Oluf Ulriksen` | 24 |
| `Oluf Ulriksen` | `Oluf Ulriksen` | 6 |

### Resulting editor → publisher pairs (`dsl-reformationssalmer`, 782 files)

| Book | `editor` | `publisher` |
|---|---|---|
| Thomissøn 1569 | Hans Thomissøn | Lorenz Benedicht |
| Jespersen 1573 | Niels Jespersen | Lorenz Benedicht |
| Malmø 1533 | Christiern Pedersen | Joh. Hoochstraten |
| Vingaard 1553 | Hans Vingaard | Hans Vingaard |
| Dietz 1529 / 1536 | Ludwig Dietz | Ludwig Dietz |
| Claus Mortensen 1529 | Claus Mortensen Tøndebinder | Oluf Ulriksen |
| Oluf Ulriksen 1535 | Oluf Ulriksen | Oluf Ulriksen |
| Frands Vormodsen 1539 | Frands Vormodsen | Oluf Ulriksen |

## Corpora that do not use `editor`

`dsl-tekstnet` and `early-danish-ballads` have `source.publisher: null` and no
`editor` key. The retired `printer: null` key was removed from them on 2026-11-27
(`remap_dsl_publisher.py --drop-null-printer`).

**Ballad scribes are deliberately not recorded as `publisher`.** The DUDS
overview states that within the court-circle manuscripts some ballads were
entered by their noble owners and others by professional scribes, so scribe
identity varies *per ballad*, and the index tables carry no scribe column. The
manuscript names (Karen Brahe, Anna Munk, Svaning, …) are mostly *owners*, which
would repeat the owner-as-producer mislabel this migration fixed. The manuscript
name in `source.title` already carries that provenance.

**Tekstnet** `publisher: null` is also deliberate (2026-07-03): Tekstnet's
"Udgiver" metadata is the editor of the *digital edition* (often a 21st-century
literary historian), not the historical publisher, so it must not be copied
into this field. The 19th-c. imprint may be extracted from the page text in a
future task.