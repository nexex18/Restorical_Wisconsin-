# Scraper Architecture Comparison: Wisconsin vs Oregon

**Date:** 2026-02-08
**Status:** Research complete

---

## Context

The Wisconsin BRRTS scraper was built autonomously by Claude Code on dev_server_1 (104.248.183.188), following patterns from the Oregon ECSI scraper. This brainstorm documents the architectural comparison between the two approaches.

## Key Finding

**Both scrapers use CSS selectors and DOM parsing - neither uses screenshots or vision/OCR for data extraction.**

The Wisconsin scraper follows the same fundamental approach as Oregon: navigate to pages with Playwright, query the DOM for elements, extract text from those elements, and parse structured data.

## Architecture Comparison

### Oregon ECSI Scraper

**Location:** `/Users/darrensilver/python_projects/Restorical/Oregon_2/`

**Approach:** JavaScript-heavy with `page.evaluate()`

```python
# Oregon uses page.evaluate() to run JavaScript in the browser
projects = await page.evaluate("""
    () => {
        const rows = document.querySelectorAll('tr.hover-light-bg');
        return Array.from(rows).map(row => ({
            ecsi_number: row.querySelector('td:nth-child(1)')?.textContent,
            name: row.querySelector('td:nth-child(2)')?.textContent,
            // ... more fields
        }));
    }
""")

# Also uses query_selector for specific elements
project_badge = await page.query_selector('span.badge-primary.mb-0[title="Project Number"]')
```

**Key characteristics:**
- Inline JavaScript for complex extractions
- Returns structured objects directly from browser context
- Tab-based navigation (8 tabs per site)
- Extracts from grid pages and info pages

### Wisconsin BRRTS Scraper

**Location:** `root@104.248.183.188:/app/Wisconsin/`

**Approach:** Python-heavy with `query_selector()`

```python
# Wisconsin uses query_selector from Python
county_select = await self.page.wait_for_selector(
    'select[name="county"], select#county, #ddlCounty'
)

# Extracts text from elements in Python
cells = await row.query_selector_all('td')
for cell in cells:
    cell_text = (await cell.inner_text()).strip()

# Maps labeled fields to database columns
labels = await self.page.query_selector_all('.detail-label, dt, th, label')
for label_el in labels:
    label_text = (await label_el.inner_text()).strip()
    value_el = await label_el.evaluate_handle(
        'el => el.nextElementSibling'
    )
```

**Key characteristics:**
- CSS selectors called from Python
- Manual text parsing and field mapping
- County-by-county search strategy
- Extracts from search results and detail pages

## Side-by-Side Comparison

| Aspect | Oregon | Wisconsin |
|--------|--------|-----------|
| **Primary method** | `page.evaluate()` with JS | `query_selector()` from Python |
| **Field extraction** | JS returns structured objects | Python parses element text |
| **Selector style** | Mix of CSS and JS queries | Pure CSS selectors |
| **Navigation** | Direct URL + tab clicks | Form submission + pagination |
| **Checkpointing** | `detail_scraped` flag (0/1/-1) | Same pattern |
| **Database** | SQLite with WAL | Same pattern |
| **Rate limiting** | Delays between requests | Same pattern |

## Data Extraction Methods

### Neither Uses Screenshots/Vision

Both scrapers extract data by:

1. **Navigating** to a URL with Playwright
2. **Waiting** for page load / network idle
3. **Querying** the DOM with CSS selectors
4. **Extracting** text content from elements
5. **Parsing** structured data (tables, key-value pairs)
6. **Storing** in SQLite database

### Oregon's JavaScript Approach

```python
# Runs in browser context, returns structured data
data = await page.evaluate("""
    () => {
        const table = document.querySelector('#documentsTable');
        return Array.from(table.querySelectorAll('tr')).map(row => ({
            title: row.cells[0]?.textContent?.trim(),
            date: row.cells[1]?.textContent?.trim(),
            url: row.querySelector('a')?.href
        }));
    }
""")
```

**Pros:**
- Single round-trip for complex extractions
- Native DOM API access
- Can handle dynamic content

**Cons:**
- Harder to debug (JS errors in browser)
- Must serialize everything to JSON
- More complex syntax

### Wisconsin's Python Approach

```python
# Runs in Python, queries DOM element by element
rows = await self.page.query_selector_all('table tbody tr')
for row in rows:
    cells = await row.query_selector_all('td')
    title = (await cells[0].inner_text()).strip()
    date = (await cells[1].inner_text()).strip()
    link = await row.query_selector('a')
    url = await link.get_attribute('href') if link else None
```

**Pros:**
- Easier to debug (Python exceptions)
- More readable/maintainable
- Better IDE support

**Cons:**
- More round-trips to browser
- Slightly slower for large extractions
- More verbose code

## Why Claude Code Chose Python-Heavy

Claude Code built the Wisconsin scraper using the Python-heavy approach because:

1. **Reference materials** - The `reference_app.py` and `reference_db.py` showed the data structures, but not the full Oregon scraper extraction code
2. **Simpler debugging** - Autonomous agent can more easily catch and fix Python exceptions
3. **Incremental testing** - Easier to test individual selector queries
4. **No prior JS context** - Without seeing Oregon's `page.evaluate()` patterns, defaulted to simpler approach

## Recommendations

### For Future Scrapers

1. **Use `page.evaluate()` for bulk extraction** - When scraping tables with many rows, JS is more efficient
2. **Use `query_selector()` for single elements** - For individual fields, Python is clearer
3. **Hybrid approach** - Oregon's pattern is optimal: JS for bulk, Python for navigation

### For Wisconsin Scraper Optimization

If performance becomes an issue, refactor `_parse_results_page()` and `_scrape_detail_page()` to use `page.evaluate()` for bulk table extraction:

```python
# Current (multiple round-trips)
rows = await self.page.query_selector_all('table tbody tr')
for row in rows:
    cells = await row.query_selector_all('td')  # N queries

# Optimized (single round-trip)
data = await self.page.evaluate("""
    () => Array.from(document.querySelectorAll('table tbody tr'))
        .map(row => Array.from(row.cells).map(c => c.textContent.trim()))
""")
```

## Open Questions

1. **DNS Resolution** - Wisconsin scraper cannot currently reach `.wi.gov` domains from the VPS. Need to investigate:
   - Is it a DNS configuration issue?
   - Are government sites blocking DigitalOcean IPs?
   - Would a residential proxy work?

2. **Performance** - Once DNS is fixed, benchmark the Wisconsin scraper vs Oregon to quantify the round-trip overhead

3. **Maintainability** - Which approach is easier to maintain when the target website changes?

## References

- Oregon scraper: `/Users/darrensilver/python_projects/Restorical/Oregon_2/`
- Wisconsin scraper: `root@104.248.183.188:/app/Wisconsin/`
- Wisconsin status doc: `/Users/darrensilver/python_projects/Restorical/Oregon_2/docs/discussions/2026-02-08-wisconsin-project-status.md`
- Dev server: 104.248.183.188 (dev_server_1)
