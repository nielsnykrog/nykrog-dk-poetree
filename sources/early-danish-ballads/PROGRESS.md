# Early Danish Ballads — Source Progress

## Pilot 1: Langebeks Kvart (DONE — v6.2 re-emitted 2026-07-03)

### Status
- **Poems**: 106 (95 unique titles + 11 collision-suffix duplicates)
- **Total lines**: 5501 (was 5526 at v5b; 25 lone-sigil/finis lines dropped in v6/v6.1)
- **Distinct stanzas**: 88 (0..87 across the corpus)
- **Filename collisions**: 11 (resolved by `--2`, `--3` suffix)

### Parser
- **v6.2** (frozen 2026-07-03). Docstring at top of `parser.py` lists all changes.
- v5b → v6.2 cumulative changes:
  - stanza_id is **zero-based** (schema line 114); renumbered contiguously 0..N-1 after parsing.
  - Drop a line whose post-strip content is only the decorative set `{*, |, :, (, ), ?, !, [, ], <, >}` (letters, digits, dashes always preserved).
  - Stanza-number detection matches `<br/>[N]`, `<br/>N</td>`, `<br/>N.</td>` (Dronning Sophia's form).
  - FINIS strip is case-insensitive; Fenis also stripped (Swedish scribal variant).
  - Editorial letter/word insertion regex widened from {1,5} to {1,15} chars, allows internal hyphens.
  - `<kommentar ...>` strip rule for Karen Brahes's unclosed tags.

---

## Pilot 2 + full corpus: ALL 9 MANUSCRIPTS DONE (2026-07-03)

### Coverage
- **Total poems scraped**: 937 unique index entries
- **Total JSON files**: 949 (937 + 12 in-ms filename collisions)
- **Total lines**: 79,970
- **Distinct stanza_ids**: 233 (0..232)

### Per-manuscript counts
| Slug | Title | Index entries | JSONs (incl. --N) | Date forms |
|---|---|---|---|---|
| hjertebogen | Hjertebogen | 83 | 83 | `1553-1555` |
| jens-billes-haandskrift | Jens Billes Håndskrift | 88 | 88 | `1555-1559`, `Før 1555`, `1589` |
| langebeks-kvart | Langebeks kvart | 106 | 106 (+ 11 collisions → 117 files) | `1560-1562`, `1570-1573`, `1579-1583`, `1593-1596` |
| karen-brahes-folio-aeldre-del | Karen Brahes folio, ældre del | 201 | 201 | `Før 1583` |
| dronning-sophias-visebog | Dronning Sophias visebog | 118 | 117 | `Før 1584`, `Før 1605`, `Efter 1598`, `1630'erne`, bare years; index has 118 entries but only 117 unique URLs (DRSXV.htm mis-attribution — see Phase 5) |
| anna-munks-haandskrift | Anna Munks Håndskrift | 51 | 51 | `1590-1591` |
| rentzells-haandskrift | Rentzells Håndskrift | 72 | 72 | `1575-1590` |
| svanings-haandskrift-i | Svanings Håndskrift I | 141 | 141 | `1575-1590` |
| svanings-haandskrift-ii | Svanings Håndskrift II | 77 | 77 | `1575-1590` |

(Note: DRS shows 117 JSONs from 118 index entries because one href `DRSXV.htm` is shared by two different poems — handled by `-A`/`-B` filename suffix.)

### Date-form coverage across the 9 manuscripts
| Form | Total entries | Manuscripts |
|---|---|---|
| Bare year (`1589`) | 100+ | All (varies) |
| `Før N` | 122 | DRS, BILL |
| `Efter N` | 3 | DRS |
| `A-B` range (`1575-1590`) | 600+ | LNGK, KBRA, MUNK, RNZ, SVI, SVII |
| `N'erne` decade (`1630'erne`) | 20 | DRS |
| (`Efter` and `N'erne` were unverified before DRS pilot; now exercised.) |

### v6.2 audit (post-full-scrape, 937 raw pages)
- Tag leakage: **0**
- Square-bracket leakage: **0**
- Entity leakage: **0**
- Lone-sigil survivors: **0**
- FINIS/Fenis survivors: **0**
- All 937 poems start at stanza_id=0
- All 937 poems have contiguous stanza_ids 0..N-1
- 1731 files validated end-to-end (949 EDB + 782 DSL), **0 schema errors, 0 warnings**

### Files
- **Raw HTML (937 pages)**: `sources/early-danish-ballads/raw/<ms-slug>/`
- **JSONs (949)**: `poems/early-danish-ballads--anonymous--*--<ms-slug>.json`
- **Per-ms audit copies**: `sources/early-danish-ballads/pilot/<ms-slug>/`
- **Per-ms indexes**: `sources/early-danish-ballads/index/<ms-slug>_parsed.json`

---

## Known caveats / next phases

### Phase 4 — content/language review
Not yet run. The corpus is overwhelmingly Danish but may contain:
- Latin liturgical fragments (similar to DSL source).
- Low-German or Swedish-influenced passages (esp. DRS, MUNK).
- Genuinely corrupt or non-poem pages that escaped parsing.

A language classifier pass on the 949 EDB poems is recommended. Reuse the `literary-dataset-building` skill's WORDS-based Latin detector + closed-vocab heuristic.

### Phase 5 — deduplication review (done 2026-07-03)

**Files**: 936 EDB poems (1:1 with unique source URLs).
**Cross-ms**: 198 titles appear in 2+ manuscripts — expected per user rule #4a.
**Pilot redundant scrapes**: 12 found, all quarantined to
`sources/early-danish-ballads/pilot_redundant_quarantine/` (recoverable, not deleted).
**DRS index quirk**: the index claims 118 entries but only 117 unique URLs.
Two entries (nr XV Bejlekunsten and nr XI I Guds händer) share `DRSXV.htm` in
the index, but only Bejlekunsten actually lives at DRSXV.htm — I Guds händer's
real URL is `DRSXI.htm`. The parser correctly mapped each entry to its actual
URL, so we have 117 DRS files matching 117 URLs. Index has a metadata bug;
the 2 `Datering` values for "I Guds hænder" (Efter 1598 vs 1630'erne) and
the corresponding source-vs-actual URL mismatch should be flagged upstream.
**Validation**: 1718 files end-to-end (782 DSL + 936 EDB), 0 errors.
In-ms collisions (12) were handled with `--2`/`--3` suffix. **Cross-ms collisions** (same ballad appearing in multiple manuscripts) are expected and *should be preserved* as separate witnesses per user rule #4a — but a line-set containment check may catch redundant scrapes within the same ms that slipped through.