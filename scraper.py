"""
Wisconsin DNR BRRTS Scraper

Scrapes contaminated site data from the Wisconsin BRRTS (Bureau for
Remediation and Redevelopment Tracking System) at:
  https://apps.dnr.wi.gov/rrbotw/botw-search

Phase 1: List scraper - searches county by county to collect site IDs
Phase 2: Detail scraper - visits each site detail page for full data

Supports checkpointing (resumes from where it left off).
"""
import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from config import (
    BRRTS_BASE_URL, BRRTS_SEARCH_URL, BRRTS_DETAIL_URL, BRRTS_RESULTS_URL,
    TIMEOUTS, MAX_RETRIES, RETRY_DELAY, DEFAULT_HEADLESS, MAX_SITES,
    LOG_DIR, WISCONSIN_COUNTIES, ensure_directories,
)
import db

ensure_directories()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'scraper.log'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


class BRRTSScraper:
    def __init__(self, headless=DEFAULT_HEADLESS):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.sites_scraped = 0

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()

    async def navigate(self, url, wait_for='networkidle'):
        for attempt in range(MAX_RETRIES):
            try:
                await self.page.goto(url, timeout=TIMEOUTS['page_load'],
                                     wait_until=wait_for)
                return True
            except PlaywrightTimeout:
                log.warning(f"Timeout navigating to {url} (attempt {attempt + 1})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
        return False

    # ------------------------------------------------------------------
    # Phase 1: List scraper
    # ------------------------------------------------------------------

    async def scrape_list(self):
        """Search county by county to collect all site records from the results page."""
        log.info("=== Phase 1: List Scraping ===")
        db.log_scrape('list', 'started')
        known = db.get_all_brrts_numbers()
        total_new = 0

        for county in WISCONSIN_COUNTIES:
            if self.sites_scraped >= MAX_SITES:
                log.info(f"Reached max sites limit ({MAX_SITES})")
                break

            log.info(f"Searching county: {county}")

            ok = await self.navigate(BRRTS_SEARCH_URL)
            if not ok:
                log.error(f"Could not load search page for county {county}")
                continue

            await asyncio.sleep(1)

            try:
                # Fill in the county field and submit search
                county_select = await self.page.wait_for_selector(
                    'select[name="county"], select#county, #ddlCounty',
                    timeout=TIMEOUTS['selector_wait']
                )
                if county_select:
                    await county_select.select_option(label=county)

                # Click search button
                search_btn = await self.page.query_selector(
                    'button[type="submit"], input[type="submit"], #btnSearch, .btn-search'
                )
                if search_btn:
                    await search_btn.click()

                await self.page.wait_for_load_state('networkidle',
                                                     timeout=TIMEOUTS['networkidle'])
                await asyncio.sleep(2)

                # Parse results
                new_sites = await self._parse_results_page(county, known)
                total_new += new_sites

                # Handle pagination
                while True:
                    next_btn = await self.page.query_selector(
                        'a:has-text("Next"), .next-page, [aria-label="Next page"]'
                    )
                    if not next_btn or not await next_btn.is_visible():
                        break

                    await next_btn.click()
                    await self.page.wait_for_load_state('networkidle',
                                                         timeout=TIMEOUTS['networkidle'])
                    await asyncio.sleep(1)

                    new_in_page = await self._parse_results_page(county, known)
                    total_new += new_in_page

                    if self.sites_scraped >= MAX_SITES:
                        break

            except PlaywrightTimeout:
                log.warning(f"Timeout searching county {county}")
            except Exception as e:
                log.error(f"Error searching county {county}: {e}")

            await asyncio.sleep(1)  # Rate limiting

        db.log_scrape('list', 'completed', f"Found {total_new} new sites", total_new)
        log.info(f"=== List scraping complete: {total_new} new sites ===")
        return total_new

    async def _parse_results_page(self, county, known):
        """Parse the results table and insert new sites."""
        new_count = 0

        # Try to find result rows in a table
        rows = await self.page.query_selector_all(
            'table tbody tr, .results-table tr, .grid-row'
        )

        for row in rows:
            if self.sites_scraped >= MAX_SITES:
                break

            try:
                cells = await row.query_selector_all('td')
                if len(cells) < 3:
                    continue

                # Try to extract BRRTS number from a link
                link = await row.query_selector('a[href*="botw-activity-detail"], a[href*="dsn="]')
                brrts_number = None
                source_url = None
                dsn = None

                if link:
                    href = await link.get_attribute('href')
                    text = (await link.inner_text()).strip()
                    # Extract BRRTS number
                    brrts_match = re.search(r'(\d{2}-\d{2}-\d{6})', text)
                    if brrts_match:
                        brrts_number = brrts_match.group(1)
                    # Extract DSN from URL
                    dsn_match = re.search(r'dsn=(\d+)', href or '')
                    if dsn_match:
                        dsn = dsn_match.group(1)
                        source_url = f"{BRRTS_BASE_URL}{href}" if href.startswith('/') else href

                if not brrts_number:
                    # Try to find BRRTS number in any cell
                    for cell in cells:
                        cell_text = (await cell.inner_text()).strip()
                        brrts_match = re.search(r'(\d{2}-\d{2}-\d{6})', cell_text)
                        if brrts_match:
                            brrts_number = brrts_match.group(1)
                            break

                if not brrts_number or brrts_number in known:
                    continue

                # Extract other fields from cells
                cell_texts = []
                for cell in cells:
                    cell_texts.append((await cell.inner_text()).strip())

                # Determine activity type from BRRTS number prefix
                prefix = brrts_number[:2]
                from config import ACTIVITY_TYPES
                activity_type = ACTIVITY_TYPES.get(prefix, 'Unknown')

                site_data = {
                    'brrts_number': brrts_number,
                    'activity_name': cell_texts[1] if len(cell_texts) > 1 else None,
                    'activity_type': activity_type,
                    'status': cell_texts[3] if len(cell_texts) > 3 else None,
                    'county': county,
                    'address': cell_texts[2] if len(cell_texts) > 2 else None,
                    'municipality': None,
                    'region': None,
                    'fid_number': None,
                    'site_id': dsn,
                    'responsible_party': None,
                    'project_manager': None,
                    'detail_scraped': 0,
                    'detail_data': None,
                    'document_count': 0,
                    'source_url': source_url or f"{BRRTS_DETAIL_URL}?dsn={dsn}" if dsn else None,
                    'last_scraped_at': None,
                    'updated_date': None,
                }

                db.upsert_site(site_data)
                known.add(brrts_number)
                self.sites_scraped += 1
                new_count += 1

            except Exception as e:
                log.warning(f"Error parsing row: {e}")

        if new_count > 0:
            log.info(f"  {county}: found {new_count} new sites (total: {self.sites_scraped})")

        return new_count

    # ------------------------------------------------------------------
    # Phase 2: Detail scraper
    # ------------------------------------------------------------------

    async def scrape_details(self):
        """Visit each site's detail page and extract full data."""
        log.info("=== Phase 2: Detail Scraping ===")
        db.log_scrape('detail', 'started')

        # Get sites that need detail scraping
        pending = db.query(
            "SELECT brrts_number, site_id, source_url FROM sites WHERE detail_scraped = 0 LIMIT ?",
            (MAX_SITES,)
        )

        log.info(f"Sites to detail-scrape: {len(pending)}")
        success = 0
        failed = 0

        for i, site in enumerate(pending):
            brrts = site['brrts_number']
            url = site['source_url']

            if not url and site.get('site_id'):
                url = f"{BRRTS_DETAIL_URL}?dsn={site['site_id']}"

            if not url:
                log.warning(f"No URL for {brrts}, skipping")
                continue

            log.info(f"[{i+1}/{len(pending)}] Scraping detail: {brrts}")

            try:
                detail = await self._scrape_detail_page(url, brrts)
                if detail:
                    db.upsert_site(detail['site'])
                    if detail.get('documents'):
                        db.upsert_documents(brrts, detail['documents'])
                    if detail.get('actions'):
                        db.upsert_actions(brrts, detail['actions'])
                    if detail.get('substances'):
                        db.upsert_substances(brrts, detail['substances'])
                    success += 1
                else:
                    db.upsert_site({
                        'brrts_number': brrts,
                        'activity_name': site.get('activity_name'),
                        'activity_type': site.get('activity_type'),
                        'status': site.get('status'),
                        'county': site.get('county'),
                        'address': site.get('address'),
                        'municipality': None, 'region': None,
                        'fid_number': None, 'site_id': site.get('site_id'),
                        'responsible_party': None, 'project_manager': None,
                        'detail_scraped': -1,
                        'detail_data': None,
                        'document_count': 0,
                        'source_url': url,
                        'last_scraped_at': datetime.now().isoformat(),
                        'updated_date': None,
                    })
                    failed += 1

            except Exception as e:
                log.error(f"Error scraping {brrts}: {e}")
                failed += 1

            await asyncio.sleep(1)  # Rate limiting

        db.log_scrape('detail', 'completed',
                       f"Success: {success}, Failed: {failed}", success)
        log.info(f"=== Detail scraping complete: {success} ok, {failed} failed ===")

    async def _scrape_detail_page(self, url, brrts_number):
        """Scrape a single activity detail page."""
        ok = await self.navigate(url)
        if not ok:
            return None

        await asyncio.sleep(1)

        try:
            # Extract the page content
            content = await self.page.content()

            # Try to parse structured data from the page
            detail = {
                'site': {
                    'brrts_number': brrts_number,
                    'detail_scraped': 1,
                    'last_scraped_at': datetime.now().isoformat(),
                    'source_url': url,
                },
                'documents': [],
                'actions': [],
                'substances': [],
            }

            # Extract key-value pairs from detail sections
            detail_data = {}

            # Try to read labeled fields
            labels = await self.page.query_selector_all(
                '.detail-label, .field-label, dt, th, label'
            )
            for label_el in labels:
                label_text = (await label_el.inner_text()).strip().rstrip(':')
                # Find the associated value element
                value_el = await label_el.evaluate_handle(
                    'el => el.nextElementSibling || el.parentElement.querySelector("dd, td, .field-value, .detail-value")'
                )
                if value_el:
                    try:
                        value_text = (await value_el.inner_text()).strip()
                    except:
                        value_text = ''

                    detail_data[label_text] = value_text

                    # Map known fields
                    field_map = {
                        'Activity Name': 'activity_name',
                        'Activity Type': 'activity_type',
                        'Status': 'status',
                        'County': 'county',
                        'Address': 'address',
                        'Municipality': 'municipality',
                        'Region': 'region',
                        'FID Number': 'fid_number',
                        'FID': 'fid_number',
                        'Responsible Party': 'responsible_party',
                        'Project Manager': 'project_manager',
                    }
                    if label_text in field_map:
                        detail['site'][field_map[label_text]] = value_text

            detail['site']['detail_data'] = json.dumps(detail_data) if detail_data else None

            # Extract documents from table
            doc_rows = await self.page.query_selector_all(
                '#documents table tr, .documents-table tr, [id*="document"] table tr'
            )
            for row in doc_rows[1:]:  # Skip header
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    cell_texts = [await c.inner_text() for c in cells]
                    link = await row.query_selector('a[href*="download-document"]')
                    doc_url = None
                    doc_seq = None
                    if link:
                        href = await link.get_attribute('href')
                        doc_url = f"{BRRTS_BASE_URL}{href}" if href and href.startswith('/') else href
                        seq_match = re.search(r'docSeqNo=(\d+)', href or '')
                        if seq_match:
                            doc_seq = seq_match.group(1)

                    detail['documents'].append({
                        'title': cell_texts[0].strip() if cell_texts else None,
                        'date': cell_texts[1].strip() if len(cell_texts) > 1 else None,
                        'type': cell_texts[2].strip() if len(cell_texts) > 2 else None,
                        'url': doc_url,
                        'doc_seq_no': doc_seq,
                    })

            detail['site']['document_count'] = len(detail['documents'])

            # Extract substances
            sub_rows = await self.page.query_selector_all(
                '#substances table tr, .substances-table tr, [id*="substance"] table tr'
            )
            for row in sub_rows[1:]:
                cells = await row.query_selector_all('td')
                if cells:
                    cell_texts = [await c.inner_text() for c in cells]
                    detail['substances'].append({
                        'name': cell_texts[0].strip() if cell_texts else None,
                        'medium': cell_texts[1].strip() if len(cell_texts) > 1 else None,
                    })

            # Extract actions
            act_rows = await self.page.query_selector_all(
                '#actions table tr, .actions-table tr, [id*="action"] table tr'
            )
            for row in act_rows[1:]:
                cells = await row.query_selector_all('td')
                if cells:
                    cell_texts = [await c.inner_text() for c in cells]
                    detail['actions'].append({
                        'name': cell_texts[0].strip() if cell_texts else None,
                        'date': cell_texts[1].strip() if len(cell_texts) > 1 else None,
                        'description': cell_texts[2].strip() if len(cell_texts) > 2 else None,
                    })

            return detail

        except Exception as e:
            log.error(f"Error parsing detail page for {brrts_number}: {e}")
            return None


async def main():
    db.init_db()

    scraper = BRRTSScraper()
    await scraper.start()

    try:
        # Phase 1: List scraping
        await scraper.scrape_list()

        # Phase 2: Detail scraping
        await scraper.scrape_details()

    finally:
        await scraper.stop()

    log.info("Scraping complete!")


if __name__ == '__main__':
    asyncio.run(main())
