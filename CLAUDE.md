# Wisconsin BRRTS Project

## Overview

Scraper and site browser for Wisconsin DNR BRRTS (Bureau for Remediation and Redevelopment Tracking System) contaminated sites data.

## Project Locations

| Location | Description |
|----------|-------------|
| **Local docs** | `/Users/darrensilver/python_projects/Restorical/Wisconsin/` |
| **Server code** | `root@104.248.183.188:/app/Wisconsin/` |
| **Dev server** | dev_server_1 (104.248.183.188) |

## Architecture

- **Scraper:** Playwright-based, county-by-county search strategy
- **Database:** SQLite with WAL mode
- **Site Browser:** FastHTML + MonsterUI + HTMX on port 5010
- **Pattern:** Mirrors Oregon ECSI scraper architecture

## Target Website

- Search: https://apps.dnr.wi.gov/rrbotw/botw-search
- Detail: https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn={id}

## Current Status

- Code complete (built autonomously by Claude Code)
- Site browser running with 500 seed sites
- **Blocked:** DNS cannot resolve `.wi.gov` from VPS

## Key Files on Server

```
/app/Wisconsin/
├── app.py           # Site browser (1047 lines)
├── scraper.py       # Playwright scraper (472 lines)
├── db.py            # Database layer (489 lines)
├── seed_data.py     # Test data generator
├── config.py        # Configuration
└── database/wisconsin_brrts.db
```

## Access

```bash
# SSH to server
ssh root@104.248.183.188
su - claude-dev
cd /app/Wisconsin

# View site browser (from local machine)
ssh -L 5010:localhost:5010 root@104.248.183.188
# Then open http://localhost:5010
```

## References

- Status doc: `docs/discussions/2026-02-08-wisconsin-project-status.md` (in Oregon_2)
- Architecture comparison: `docs/brainstorms/2026-02-08-scraper-architecture-comparison-brainstorm.md`
- Oregon reference: `/Users/darrensilver/python_projects/Restorical/Oregon_2/`
