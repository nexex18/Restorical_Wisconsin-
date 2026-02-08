# Wisconsin BRRTS Bulk Data Import Prompt

**Date:** 2026-02-08
**Purpose:** Prompt for Claude Code on dev_server_1 to import official Wisconsin BRRTS data

---

## Context

Official bulk data was downloaded from Wisconsin DNR and uploaded to the server:
- Source: https://apps.dnr.wi.gov/rrbotw/download-document?docSeqNo=0&bulkDownload=wdnr-brrts-data.zip&sender=bulkData
- Local copy: `/Users/darrensilver/python_projects/Restorical/Wisconsin/data/`
- Server location: `/app/Wisconsin/data/wdnr-brrts-data/`

## Data Files

| File | Records | Description |
|------|---------|-------------|
| facility-activity.txt | 100,424 | Main site records |
| actions.txt | 917,904 | Remediation actions |
| substances.txt | 96,420 | Contaminants |
| impacts.txt | 121,366 | Environmental impacts |
| who.txt | 239,034 | Contact/party records |
| facility-owner.txt | 15,619 | Ownership records |
| spilldetails.txt | 104,630 | Spill information |
| spiller-actions.txt | 84,630 | Spill response actions |

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
Official Wisconsin BRRTS bulk data has been downloaded and placed at /app/Wisconsin/data/wdnr-brrts-data/

Data files (tab-delimited):
- facility-activity.txt (100,424 sites) - main site records with BRRTS number, address, county, status, lat/long
- actions.txt (917,904 records) - remediation actions linked by detail_seq_no
- substances.txt (96,420 records) - contaminants linked by detail_seq_no
- impacts.txt, who.txt, facility-owner.txt, spilldetails.txt, spiller-actions.txt

Key fields from readme.txt:
- SITE_ID is the key for facility/location records
- DETAIL_SEQ_NO links activity records to child records (actions, substances)

Your task:
1. Read the data files and understand the schema (check first few rows of each file)
2. Update db.py schema if needed to match the official data structure
3. Create import_bulk_data.py that:
   - Parses the tab-delimited files
   - Maps fields to database columns (activity_display_number = BRRTS number)
   - Imports all 100K+ sites, replacing seed data
   - Imports actions, substances linked by detail_seq_no
4. Run the import (this is real data, not seed data)
5. Update app.py if needed for any schema changes
6. Restart site browser and verify real data is showing

Reference the existing db.py for current schema. The goal is a working site browser with all 100,424 real Wisconsin BRRTS sites.
```
