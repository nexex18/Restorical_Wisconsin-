# Wisconsin BRRTS Project Status

**Date:** 2026-02-08
**Server:** dev_server_1 (104.248.183.188)
**Project Path:** `/app/Wisconsin/`

---

## Overview

The Wisconsin BRRTS (Bureau for Remediation and Redevelopment Tracking System) scraper and site browser was built autonomously by Claude Code running on a dedicated development VPS with `--dangerously-skip-permissions` enabled.

## What Was Built

Claude Code ran for approximately 19 minutes overnight and created the complete system:

| File | Lines | Description |
|------|-------|-------------|
| `config.py` | ~45 | Wisconsin-specific configuration (counties, activity types, URLs) |
| `db.py` | 489 | Database layer with WAL mode, read/write connection separation |
| `scraper.py` | 472 | Playwright-based scraper with checkpointing and resume capability |
| `seed_data.py` | 334 | Generates realistic test data for development |
| `app.py` | 1047 | Full site browser (FastHTML + MonsterUI + HTMX) |

### Architecture

The project follows the Oregon ECSI scraper patterns:

- **Database:** SQLite with WAL mode for concurrent access
- **Scraper:** Playwright browser automation, county-by-county search strategy
- **Site Browser:** FastHTML + MonsterUI + HTMX on port 5010
- **Checkpointing:** Scraper tracks `detail_scraped` flag (0=pending, 1=done, -1=failed)

### Database Schema

```
sites              - Main site records (BRRTS number, address, status, etc.)
documents          - Documents associated with each site
actions            - Remediation actions/activities
substances         - Contaminants found at each site
scrape_log         - Scraping progress tracking
document_review_selections - User selections for document review
site_qualification_notes   - Qualification notes (wisdom)
```

### Site Browser Features

- **Dashboard:** 6 KPI cards, breakdowns by type/status/county, global qualification notes
- **Sites List:** Filters (type, status, scrape status, county, search), sortable columns, pagination
- **Site Detail:** Header with badges, qualification notes, documents with checkboxes, site info, substances, actions timeline
- **HTMX:** Live filtering, OOB count updates, debounced search, auto-save notes

## Current State

### What Works

- ✅ Site browser running on port 5010 with 500 seed sites
- ✅ All HTMX interactions (filtering, sorting, search, notes)
- ✅ Document selection checkboxes
- ✅ Qualification notes save/display
- ✅ Playwright screenshot testing passed
- ✅ Scraper code complete and ready

### What Doesn't Work

- ❌ **DNS Resolution:** The VPS cannot resolve `.wi.gov` domains
- ❌ **Live Scraping:** Scraper cannot reach `apps.dnr.wi.gov`

## DNS Issue

### Problem

The development VPS (104.248.183.188) cannot resolve Wisconsin government domains:

```
$ curl -I https://apps.dnr.wi.gov
curl: (6) Could not resolve host: apps.dnr.wi.gov

$ nslookup apps.dnr.wi.gov
;; connection timed out; no servers could be reached
```

### Possible Causes

1. **VPS DNS misconfiguration** - Default DigitalOcean DNS may not resolve all domains
2. **Government site blocking** - Some .gov sites block cloud provider IP ranges
3. **Rate limiting** - DNS queries being throttled

### Attempted Solutions

Claude Code tried multiple approaches:
- Direct Playwright navigation
- curl requests
- DNS lookups via nslookup/host
- WebFetch tool

All failed with DNS resolution errors.

### Recommended Fix

Try adding public DNS servers:

```bash
ssh root@104.248.183.188
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf
curl -I https://apps.dnr.wi.gov
```

If that doesn't work, the .wi.gov sites may be blocking DigitalOcean IP ranges, which would require:
- Using a different cloud provider
- Using a residential proxy service
- Running the scraper from a different network

## How to Access

### View the Site Browser

```bash
# SSH tunnel from your local machine
ssh -L 5010:localhost:5010 root@104.248.183.188

# Then open in browser
open http://localhost:5010
```

### Connect to the Project

```bash
ssh root@104.248.183.188
su - claude-dev
cd /app/Wisconsin
source venv/bin/activate
```

### Run the Scraper (once DNS is fixed)

```bash
# Small test run
python scraper.py --counties "Dane" --max-sites 20

# Full run (up to 500 sites)
python scraper.py --max-sites 500
```

## Files on Server

```
/app/Wisconsin/
├── CLAUDE.md           # Project context for Claude Code
├── config.py           # Configuration
├── db.py               # Database layer
├── scraper.py          # Playwright scraper
├── seed_data.py        # Test data generator
├── app.py              # Site browser
├── requirements.txt    # Dependencies
├── venv/               # Python virtual environment
├── database/
│   └── wisconsin_brrts.db  # SQLite database (500 seed sites)
├── logs/               # Log files
├── docs/               # Reference materials from Oregon
│   ├── reference_app.py
│   ├── reference_db.py
│   ├── reference_config.py
│   ├── brainstorms/
│   └── plans/
├── oregon_reference/   # Symlink to /app/Oregon_test
└── screenshots/        # Playwright test screenshots
    ├── 01_dashboard.png
    ├── 02_sites.png
    ├── 03_site_detail.png
    └── ...
```

## Next Steps

1. **Fix DNS** - Try the recommended DNS fix above
2. **Test Scraper** - Once DNS works, run a small test scrape
3. **Validate Data** - Compare scraped data to website
4. **Scale Up** - Run full 500-site scrape
5. **Deploy** - Consider deploying site browser to production

## Lessons Learned

1. **Autonomous agents adapt** - Claude Code pivoted from live scraping to seed data when blocked
2. **DNS matters** - Government sites may have access restrictions from cloud IPs
3. **Reference code helps** - Having Oregon patterns available guided consistent architecture
4. **CLAUDE.md is essential** - Gave Claude Code the context needed to build the right thing

## References

- Target website: https://apps.dnr.wi.gov/rrbotw/botw-search
- Oregon reference: `/app/Oregon_test/site_browser/`
- Server: dev_server_1 (104.248.183.188)
- User: `claude-dev` (non-root for `--dangerously-skip-permissions`)
