"""
Scrape document URLs from Wisconsin DNR BRRTS site detail pages
via Cloudflare Worker proxy.

Usage:
    python scrape_documents.py              # Scrape all unscraped sites
    python scrape_documents.py --limit 100  # Scrape 100 sites
    python scrape_documents.py --test 20001 # Test with a single DSN
    python scrape_documents.py --status     # Show progress
    python scrape_documents.py --retry-failed  # Retry previously failed
"""
import argparse
import asyncio
import logging
import re
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from config import WORKER_URL, BRRTS_BASE_URL, LOG_DIR, ensure_directories
import db

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

REQUEST_DELAY = 1.5    # seconds between requests
REQUEST_TIMEOUT = 30   # seconds per request
MAX_RETRIES = 3
RETRY_DELAY = 5        # seconds between retries (multiplied by attempt)
PROGRESS_INTERVAL = 100  # log progress every N sites

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

ensure_directories()
log = logging.getLogger("scrape_documents")
log.setLevel(logging.DEBUG)

_fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

_fh = logging.FileHandler(LOG_DIR / "scrape_documents.log")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
log.addHandler(_fh)

_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_fmt)
log.addHandler(_ch)


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_documents_from_response(result: dict, dsn: int) -> list[dict]:
    """Parse document links from worker response.

    The worker fetches three AJAX endpoints:
    - WizSiteFiles: downloadable documents (PDFs etc.)
    - WizAddtionalURLsDocs: additional URL links
    - WizActions: actions with attached documents

    All return HTML fragments with links.
    """
    docs = []
    seen_seqs = set()

    # Parse all HTML fragments
    for html_key in ('site_files_html', 'addtl_docs_html', 'actions_html'):
        html = result.get(html_key, '')
        if not html or len(html) < 10:
            continue

        soup = BeautifulSoup(html, 'lxml')

        # Look for download-document links
        for link in soup.select('a[href*="download-document"]'):
            href = link.get('href', '')
            seq_match = re.search(r'docSeqNo=(\d+)', href)
            if not seq_match:
                continue

            doc_seq = int(seq_match.group(1))
            if doc_seq in seen_seqs:
                continue
            seen_seqs.add(doc_seq)

            # Build full URL
            if href.startswith('/'):
                doc_url = f"{BRRTS_BASE_URL}{href}"
            elif href.startswith('http'):
                doc_url = href
            else:
                doc_url = f"{BRRTS_BASE_URL}/rrbotw/{href}"

            # Walk up to find the table row for metadata
            # WizSiteFiles table: td[0]=icon/link, td[1]=description, td[2]=filename, td[3]=size
            row = link.find_parent('tr')
            title = None
            doc_date = None
            doc_type = None

            if row:
                cells = row.find_all('td')
                texts = [c.get_text(strip=True) for c in cells]
                # td[0] is the icon/download link cell - skip it for metadata
                if len(texts) >= 2:
                    title = texts[1] or None  # Description
                if len(texts) >= 3:
                    doc_type = texts[2] or None  # Filename
                # No date column in WizSiteFiles - leave doc_date as None
            else:
                title = link.get_text(strip=True) or None

            docs.append({
                'doc_seq_no': doc_seq,
                'title': title,
                'document_date': doc_date,
                'document_type': doc_type,
                'document_url': doc_url,
            })

        # Also look for any other document-like links (non download-document)
        for link in soup.select('a[href]'):
            href = link.get('href', '')
            if 'download-document' in href:
                continue  # Already handled above
            if not href or href.startswith('#') or href.startswith('javascript'):
                continue
            # Check for PDF or document-like URLs
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.xls', '.csv']):
                if href.startswith('/'):
                    doc_url = f"{BRRTS_BASE_URL}{href}"
                elif href.startswith('http'):
                    doc_url = href
                else:
                    continue

                title = link.get_text(strip=True) or None
                if not title:
                    continue

                # Use a hash as pseudo doc_seq_no for non-DNR docs
                pseudo_seq = hash(doc_url) & 0x7FFFFFFF
                if pseudo_seq in seen_seqs:
                    continue
                seen_seqs.add(pseudo_seq)

                row = link.find_parent('tr')
                doc_date = None
                doc_type = 'External Link'
                if row:
                    cells = row.find_all('td')
                    texts = [c.get_text(strip=True) for c in cells]
                    if len(texts) >= 2:
                        doc_date = texts[1] or None

                docs.append({
                    'doc_seq_no': pseudo_seq,
                    'title': title,
                    'document_date': doc_date,
                    'document_type': doc_type,
                    'document_url': doc_url,
                })

    return docs


# ---------------------------------------------------------------------------
# Worker communication
# ---------------------------------------------------------------------------

async def fetch_detail_page(client: httpx.AsyncClient, dsn: int) -> dict | None:
    """Fetch a detail page via the Cloudflare Worker proxy with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(
                WORKER_URL,
                params={"dsn": str(dsn)},
                timeout=REQUEST_TIMEOUT,
            )
            data = resp.json()

            if data.get("success"):
                return data

            status = data.get("status")
            # 404 or other client errors -- no point retrying
            if status and 400 <= status < 500:
                log.debug(f"DSN {dsn}: HTTP {status} (no retry)")
                return data

            log.warning(f"DSN {dsn}: Worker returned success=false, status={status}")

        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            log.warning(f"DSN {dsn}: attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
        except Exception as e:
            log.error(f"DSN {dsn}: unexpected error: {e}")

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    return None


# ---------------------------------------------------------------------------
# Main scraping loop
# ---------------------------------------------------------------------------

async def scrape_sites(sites: list[dict], label: str = "Scrape"):
    """Scrape documents for a list of sites."""
    total = len(sites)
    if total == 0:
        log.info("No sites to scrape.")
        return

    log.info(f"{label}: {total:,} sites to process")

    stats = {'success': 0, 'empty': 0, 'failed': 0, 'docs_found': 0}
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        for i, site in enumerate(sites):
            dsn = site['detail_seq_no']
            brrts = site['brrts_number']

            result = await fetch_detail_page(client, dsn)

            if result and result.get('success'):
                docs = parse_documents_from_response(result, dsn)

                if docs:
                    db.insert_documents(brrts, dsn, docs)
                    stats['docs_found'] += len(docs)
                    stats['success'] += 1
                    log.debug(f"DSN {dsn} ({brrts}): {len(docs)} documents")
                else:
                    stats['empty'] += 1
                    log.debug(f"DSN {dsn} ({brrts}): no documents")

                db.mark_docs_scraped(brrts, status=1)

            elif result and not result.get('success') and result.get('status') and 400 <= result['status'] < 500:
                # Page doesn't exist or access denied -- mark as done
                db.mark_docs_scraped(brrts, status=1)
                stats['empty'] += 1
                log.debug(f"DSN {dsn} ({brrts}): HTTP {result['status']}")

            else:
                db.mark_docs_scraped(brrts, status=-1)
                stats['failed'] += 1
                log.warning(f"DSN {dsn} ({brrts}): FAILED")

            # Progress logging
            done = i + 1
            if done % PROGRESS_INTERVAL == 0 or done == total:
                elapsed = time.time() - start_time
                rate = done / elapsed if elapsed > 0 else 0
                remaining = total - done
                eta_min = remaining / rate / 60 if rate > 0 else 0
                log.info(
                    f"Progress: {done:,}/{total:,} "
                    f"({stats['success']} ok, {stats['empty']} empty, "
                    f"{stats['failed']} fail, {stats['docs_found']} docs) "
                    f"[{rate:.1f}/s, ETA {eta_min:.0f}m]"
                )

            # Rate limiting
            await asyncio.sleep(REQUEST_DELAY)

    elapsed = time.time() - start_time
    log.info(
        f"{label} complete in {elapsed / 60:.1f}m: "
        f"{stats['success']} ok, {stats['empty']} empty, "
        f"{stats['failed']} failed, {stats['docs_found']} documents found"
    )


async def scrape_all(limit: int = 0):
    """Scrape documents for all unscraped sites."""
    db.ensure_documents_table()
    batch_limit = limit if limit > 0 else 999999
    sites = db.get_unscraped_dsns(batch_limit)
    await scrape_sites(sites, label="Scrape")


async def retry_failed(limit: int = 0):
    """Retry sites that previously failed."""
    db.ensure_documents_table()
    batch_limit = limit if limit > 0 else 999999
    sites = db.get_failed_dsns(batch_limit)
    # Reset their status to 0 so they can be re-scraped
    conn = db.get_write_connection()
    try:
        for s in sites:
            conn.execute(
                "UPDATE sites SET docs_scraped = 0 WHERE brrts_number = ?",
                (s['brrts_number'],)
            )
        conn.commit()
    finally:
        conn.close()
    await scrape_sites(sites, label="Retry")


# ---------------------------------------------------------------------------
# Test mode
# ---------------------------------------------------------------------------

async def test_single(dsn: int):
    """Fetch a single DSN and display results for debugging."""
    db.ensure_documents_table()
    print(f"Fetching DSN {dsn} via worker...")

    async with httpx.AsyncClient() as client:
        result = await fetch_detail_page(client, dsn)

    if not result:
        print("ERROR: No response from worker")
        return

    if not result.get('success'):
        print(f"ERROR: Worker returned success=false, status={result.get('status')}")
        print(f"  Error: {result.get('error', 'unknown')}")
        return

    # Save HTML fragments for analysis
    for key in ('site_files_html', 'addtl_docs_html'):
        html = result.get(key, '')
        status = result.get(key.replace('_html', '_status'), '?')
        print(f"\n{key}: {len(html):,} bytes (HTTP {status})")
        if html:
            sample_path = LOG_DIR / f"sample_dsn_{dsn}_{key}.html"
            sample_path.write_text(html, encoding='utf-8')
            print(f"  Saved to: {sample_path}")

    # Parse documents
    docs = parse_documents_from_response(result, dsn)
    print(f"\nDocuments found: {len(docs)}")
    for d in docs:
        print(f"  [{d['doc_seq_no']}] {d['title']}")
        print(f"       Date: {d['document_date']}  Type: {d['document_type']}")
        print(f"       URL: {d['document_url']}")

    if not docs:
        # Debug: show HTML structure
        for key in ('site_files_html', 'addtl_docs_html'):
            html = result.get(key, '')
            if html:
                soup = BeautifulSoup(html, 'lxml')
                links = soup.find_all('a')
                tables = soup.find_all('table')
                print(f"\n{key} structure:")
                print(f"  Links: {len(links)}")
                for a in links[:5]:
                    print(f"    {a.get_text(strip=True)[:60]} -> {a.get('href', '')[:80]}")
                print(f"  Tables: {len(tables)}")
                for j, table in enumerate(tables[:3]):
                    rows = table.find_all('tr')
                    print(f"    Table {j}: {len(rows)} rows")
                    if rows:
                        print(f"      Row 0: {rows[0].get_text(strip=True)[:100]}")


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def show_status():
    """Display document scraping progress."""
    db.ensure_documents_table()
    p = db.get_docs_scrape_progress()

    print(f"\nDocument Scrape Progress")
    print(f"{'─' * 40}")
    print(f"  Total sites:       {p['total']:>10,}")
    print(f"  Scraped (done):    {p['scraped']:>10,}")
    print(f"  Failed:            {p['failed']:>10,}")
    print(f"  Pending:           {p['pending']:>10,}")
    print(f"  {'─' * 36}")
    print(f"  Total documents:   {p['total_documents']:>10,}")
    print(f"  Sites with docs:   {p['sites_with_docs']:>10,}")

    pct = (p['scraped'] / p['total'] * 100) if p['total'] else 0
    print(f"  Progress:          {pct:>9.1f}%")

    if p['scraped'] > 0 and p['total_documents'] > 0:
        avg = p['total_documents'] / p['scraped']
        print(f"  Avg docs/site:     {avg:>10.1f}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape document URLs from Wisconsin DNR BRRTS detail pages"
    )
    parser.add_argument('--limit', type=int, default=0,
                        help='Max sites to scrape (0 = all)')
    parser.add_argument('--test', type=int, metavar='DSN',
                        help='Test with a single detail_seq_no')
    parser.add_argument('--status', action='store_true',
                        help='Show scraping progress')
    parser.add_argument('--retry-failed', action='store_true',
                        help='Retry previously failed sites')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.test:
        asyncio.run(test_single(args.test))
    elif args.retry_failed:
        asyncio.run(retry_failed(args.limit))
    else:
        asyncio.run(scrape_all(args.limit))


if __name__ == '__main__':
    main()
