# Wisconsin BRRTS Document URL Scraper Prompt

**Date:** 2026-02-08
**Purpose:** Prompt for Claude Code on dev_server_1 to scrape document URLs via Cloudflare Worker

---

## Context

The bulk data import is complete - 99,925 real Wisconsin BRRTS sites are in the database. However, the bulk data doesn't include document URLs. We need to scrape document URLs from the Wisconsin DNR website.

**Problem:** The dev server (104.248.183.188) cannot directly reach Wisconsin DNR sites - they block DigitalOcean IPs.

**Solution:** A Cloudflare Worker has been set up as a proxy. It CAN reach Wisconsin DNR.

## Cloudflare Worker Details

- **Worker URL:** `https://browser-scraper.darrenwsilver.workers.dev/`
- **Status:** Working - tested and confirmed HTTP 200 from Wisconsin DNR
- **Test result:** `{"success":true,"status":200,"title":"RR BOTW | Wisconsin DNR","message":"Cloudflare CAN reach Wisconsin DNR!"}`

## Wisconsin DNR Site Detail URL Pattern

Site detail pages are at:
```
https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn={DETAIL_SEQ_NO}
```

Example: `https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn=12345`

The `DETAIL_SEQ_NO` field is already in the database (mapped to `detail_seq_no` column in sites table).

## How to Run

```bash
ssh root@104.248.183.188
su - claude-dev
cd /app/Wisconsin
source venv/bin/activate
claude --dangerously-skip-permissions
```

Then paste the prompt below.

---

## Prompt

```
A Cloudflare Worker proxy has been set up to bypass Wisconsin DNR's IP blocking.

Worker URL: https://browser-scraper.darrenwsilver.workers.dev/

The worker currently just tests connectivity. You need to:

1. First, understand the current worker code and how to update it:
   - The worker is deployed at Cloudflare
   - To update it, we'll need to provide new code that the user can paste into the Cloudflare dashboard

2. Analyze the Wisconsin DNR site detail page structure:
   - Use the worker to fetch a sample detail page
   - Example URL: https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn=1
   - Find where document links are in the HTML (look for PDF links, document tables, etc.)

3. Design a scraping approach:
   - Worker accepts a detail_seq_no parameter
   - Worker fetches the detail page
   - Worker parses HTML and extracts document URLs
   - Worker returns JSON with document URLs

4. Create a Python script (scrape_documents.py) that:
   - Reads sites from the database that don't have documents yet
   - Calls the Cloudflare Worker for each site
   - Parses the response and stores document URLs in the database
   - Implements rate limiting (be respectful - maybe 1 request per second)
   - Implements checkpointing (so it can resume if interrupted)
   - Handles errors gracefully

5. The database already has a documents table. Check db.py for the schema.

Start by updating the worker to fetch and return the HTML of a sample detail page, so we can analyze the structure. Then we'll refine the worker to extract just the document URLs.

The goal is to get document URLs for all 99,925 sites in the database.
```

---

## Worker Code to Update

The user will need to update the Cloudflare Worker code in the dashboard. Here's the current working code that just tests connectivity:

```javascript
export default {
  async fetch(request, env) {
    try {
      const response = await fetch("https://apps.dnr.wi.gov/rrbotw/botw-search", {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
      });

      const status = response.status;
      const text = await response.text();
      const titleMatch = text.match(/<title>(.*?)<\/title>/i);
      const title = titleMatch ? titleMatch[1] : "No title found";

      return new Response(JSON.stringify({
        success: true,
        status: status,
        title: title,
        message: "Cloudflare CAN reach Wisconsin DNR!"
      }), {
        headers: { "content-type": "application/json" }
      });
    } catch (error) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message
      }), {
        headers: { "content-type": "application/json" }
      });
    }
  },
};
```

The first step is to modify this worker to accept a URL parameter and fetch any Wisconsin DNR page.
