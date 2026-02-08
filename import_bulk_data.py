"""
Import Wisconsin BRRTS bulk data into SQLite database.

Reads tab-delimited files from data/wdnr-brrts-data/ and imports:
- facility-activity.txt -> sites table (100,424 records)
- actions.txt -> actions table (917,904 records)
- substances.txt -> substances table (96,420 records)
- who.txt -> extracts project manager names into sites table
"""
import csv
import sqlite3
import sys
import time
from pathlib import Path

from config import DATABASE_PATH, BRRTS_BASE_URL, ensure_directories
import db

DATA_DIR = Path(__file__).parent / "data" / "wdnr-brrts-data"

# Increase CSV field size limit for large comment fields
csv.field_size_limit(sys.maxsize)


def flag_val(s: str) -> int:
    """Convert Y/N flag to integer."""
    return 1 if s and s.strip().upper() == 'Y' else 0


def clean(s: str) -> str | None:
    """Strip whitespace, return None for empty strings."""
    if s is None:
        return None
    s = s.strip()
    return s if s else None


def parse_float(s: str) -> float | None:
    if not s or not s.strip():
        return None
    try:
        return float(s.strip())
    except ValueError:
        return None


def import_sites(conn):
    """Import facility-activity.txt into sites table."""
    path = DATA_DIR / "facility-activity.txt"
    print(f"Importing sites from {path.name}...")
    t0 = time.time()

    # Build detail_seq_no -> brrts_number mapping as we go
    dsn_to_brrts = {}

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        batch = []
        count = 0

        for row in reader:
            brrts = clean(row.get('activity_display_number'))
            if not brrts:
                continue

            dsn = row.get('detail_seq_no', '').strip()
            site_id = row.get('site_id', '').strip()

            if dsn:
                dsn_to_brrts[dsn] = brrts

            source_url = f"{BRRTS_BASE_URL}/rrbotw/botw-activity-detail?dsn={dsn}" if dsn else None

            batch.append((
                brrts,
                int(dsn) if dsn else None,
                int(site_id) if site_id else None,
                clean(row.get('activity_name')),
                clean(row.get('activity_type')),
                clean(row.get('act_code')),
                clean(row.get('status')),
                clean(row.get('county_name')),
                clean(row.get('county')),
                clean(row.get('address')),
                clean(row.get('muni')),
                clean(row.get('zip')),
                clean(row.get('region')),
                clean(row.get('fid')),
                clean(row.get('location_name')),
                clean(row.get('start_date')),
                clean(row.get('end_date')),
                clean(row.get('last_action')),
                clean(row.get('activity_comment')),
                parse_float(row.get('ll_lat_dd_amt')),
                parse_float(row.get('ll_long_dd_amt')),
                source_url,
                flag_val(row.get('pecfa_eligible_flag')),
                flag_val(row.get('drycleaner_flag')),
                flag_val(row.get('co_contamination_flag')),
                flag_val(row.get('npl_flag')),
                flag_val(row.get('derf_flag')),
                flag_val(row.get('pfas_flag')),
                flag_val(row.get('sediments_flag')),
                flag_val(row.get('petrol_ust_flag')),
            ))
            count += 1

            if len(batch) >= 5000:
                conn.executemany("""
                    INSERT OR REPLACE INTO sites (
                        brrts_number, detail_seq_no, site_id,
                        activity_name, activity_type, act_code, status,
                        county, county_code, address, municipality, zip_code,
                        region, fid_number, location_name,
                        start_date, end_date, last_action, activity_comment,
                        latitude, longitude, source_url,
                        pecfa_flag, drycleaner_flag, co_contamination_flag,
                        npl_flag, derf_flag, pfas_flag, sediments_flag, petrol_ust_flag
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, batch)
                conn.commit()
                batch = []
                if count % 20000 == 0:
                    print(f"  ...{count:,} sites")

        if batch:
            conn.executemany("""
                INSERT OR REPLACE INTO sites (
                    brrts_number, detail_seq_no, site_id,
                    activity_name, activity_type, act_code, status,
                    county, county_code, address, municipality, zip_code,
                    region, fid_number, location_name,
                    start_date, end_date, last_action, activity_comment,
                    latitude, longitude, source_url,
                    pecfa_flag, drycleaner_flag, co_contamination_flag,
                    npl_flag, derf_flag, pfas_flag, sediments_flag, petrol_ust_flag
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, batch)
            conn.commit()

    elapsed = time.time() - t0
    print(f"  Imported {count:,} sites in {elapsed:.1f}s")
    return dsn_to_brrts


def import_who(conn, dsn_to_brrts: dict):
    """Extract DNR Project Manager names from who.txt and update sites."""
    path = DATA_DIR / "who.txt"
    print(f"Importing project managers from {path.name}...")
    t0 = time.time()

    pm_map = {}  # brrts_number -> project manager name
    rp_map = {}  # brrts_number -> responsible party name

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            dsn = row.get('detail_seq_no', '').strip()
            brrts = dsn_to_brrts.get(dsn)
            if not brrts:
                continue

            role = (row.get('role_desc') or '').strip()
            name = clean(row.get('full_name'))
            if not name:
                continue

            if role == 'DNR Project Manager' and brrts not in pm_map:
                pm_map[brrts] = name
            elif role == 'Responsible Party' and brrts not in rp_map:
                rp_map[brrts] = name

    # Batch update sites with PM and RP
    batch = [(pm_map.get(b), rp_map.get(b), b) for b in set(list(pm_map.keys()) + list(rp_map.keys()))]
    count = 0
    for i in range(0, len(batch), 5000):
        chunk = batch[i:i+5000]
        conn.executemany("""
            UPDATE sites SET
                project_manager = COALESCE(?, project_manager),
                responsible_party = COALESCE(?, responsible_party)
            WHERE brrts_number = ?
        """, chunk)
        conn.commit()
        count += len(chunk)

    elapsed = time.time() - t0
    print(f"  Updated {len(pm_map):,} project managers, {len(rp_map):,} responsible parties in {elapsed:.1f}s")


def import_actions(conn, dsn_to_brrts: dict):
    """Import actions.txt into actions table."""
    path = DATA_DIR / "actions.txt"
    print(f"Importing actions from {path.name}...")
    t0 = time.time()

    batch = []
    count = 0
    skipped = 0

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            dsn = row.get('detail_seq_no', '').strip()
            brrts = dsn_to_brrts.get(dsn)
            if not brrts:
                skipped += 1
                continue

            batch.append((
                brrts,
                int(dsn) if dsn else None,
                clean(row.get('action_date')),
                clean(row.get('action_code')),
                clean(row.get('action_name')),
                clean(row.get('action_desc')),
                clean(row.get('action_comment')),
            ))
            count += 1

            if len(batch) >= 10000:
                conn.executemany("""
                    INSERT INTO actions (brrts_number, detail_seq_no, action_date,
                                       action_code, action_name, action_desc, action_comment)
                    VALUES (?,?,?,?,?,?,?)
                """, batch)
                conn.commit()
                batch = []
                if count % 100000 == 0:
                    print(f"  ...{count:,} actions")

        if batch:
            conn.executemany("""
                INSERT INTO actions (brrts_number, detail_seq_no, action_date,
                                   action_code, action_name, action_desc, action_comment)
                VALUES (?,?,?,?,?,?,?)
            """, batch)
            conn.commit()

    elapsed = time.time() - t0
    print(f"  Imported {count:,} actions ({skipped:,} skipped) in {elapsed:.1f}s")


def import_substances(conn, dsn_to_brrts: dict):
    """Import substances.txt into substances table."""
    path = DATA_DIR / "substances.txt"
    print(f"Importing substances from {path.name}...")
    t0 = time.time()

    batch = []
    count = 0
    skipped = 0

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            dsn = row.get('detail_seq_no', '').strip()
            brrts = dsn_to_brrts.get(dsn)
            if not brrts:
                skipped += 1
                continue

            batch.append((
                brrts,
                int(dsn) if dsn else None,
                clean(row.get('substance_desc')),
                clean(row.get('spill_released_amt')),
                clean(row.get('spill_released_unit_code')),
            ))
            count += 1

            if len(batch) >= 10000:
                conn.executemany("""
                    INSERT INTO substances (brrts_number, detail_seq_no, substance_name,
                                           released_amount, released_unit)
                    VALUES (?,?,?,?,?)
                """, batch)
                conn.commit()
                batch = []

        if batch:
            conn.executemany("""
                INSERT INTO substances (brrts_number, detail_seq_no, substance_name,
                                       released_amount, released_unit)
                VALUES (?,?,?,?,?)
            """, batch)
            conn.commit()

    elapsed = time.time() - t0
    print(f"  Imported {count:,} substances ({skipped:,} skipped) in {elapsed:.1f}s")


def update_counts(conn):
    """Update action_count and substance_count on sites."""
    print("Updating action/substance counts on sites...")
    t0 = time.time()

    conn.execute("""
        UPDATE sites SET action_count = (
            SELECT COUNT(*) FROM actions WHERE actions.brrts_number = sites.brrts_number
        )
    """)
    conn.commit()

    conn.execute("""
        UPDATE sites SET substance_count = (
            SELECT COUNT(*) FROM substances WHERE substances.brrts_number = sites.brrts_number
        )
    """)
    conn.commit()

    elapsed = time.time() - t0
    print(f"  Counts updated in {elapsed:.1f}s")


def main():
    ensure_directories()

    # Delete old database and start fresh
    if DATABASE_PATH.exists():
        print(f"Removing old database: {DATABASE_PATH}")
        DATABASE_PATH.unlink()

    print("Initializing database schema...")
    db.init_db()

    conn = db.get_write_connection()
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        t_total = time.time()

        # 1. Import sites
        dsn_to_brrts = import_sites(conn)

        # 2. Import project managers from who.txt
        import_who(conn, dsn_to_brrts)

        # 3. Import actions
        import_actions(conn, dsn_to_brrts)

        # 4. Import substances
        import_substances(conn, dsn_to_brrts)

        # 5. Update counts
        update_counts(conn)

        elapsed_total = time.time() - t_total
        print(f"\n=== Import complete in {elapsed_total:.1f}s ===")

        # Summary
        conn.execute("PRAGMA query_only=ON")
        total = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        actions = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        substances = conn.execute("SELECT COUNT(*) FROM substances").fetchone()[0]
        with_pm = conn.execute("SELECT COUNT(*) FROM sites WHERE project_manager IS NOT NULL").fetchone()[0]
        with_rp = conn.execute("SELECT COUNT(*) FROM sites WHERE responsible_party IS NOT NULL").fetchone()[0]
        open_sites = conn.execute("SELECT COUNT(*) FROM sites WHERE status = 'OPEN'").fetchone()[0]
        closed_sites = conn.execute("SELECT COUNT(*) FROM sites WHERE status = 'CLOSED'").fetchone()[0]
        pfas = conn.execute("SELECT COUNT(*) FROM sites WHERE pfas_flag = 1").fetchone()[0]

        print(f"  Sites:         {total:>10,}")
        print(f"  Actions:       {actions:>10,}")
        print(f"  Substances:    {substances:>10,}")
        print(f"  With PM:       {with_pm:>10,}")
        print(f"  With RP:       {with_rp:>10,}")
        print(f"  Open:          {open_sites:>10,}")
        print(f"  Closed:        {closed_sites:>10,}")
        print(f"  PFAS flagged:  {pfas:>10,}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
