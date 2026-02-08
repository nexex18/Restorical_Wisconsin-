"""
Database utilities for Wisconsin BRRTS Site Browser.

Read access to the BRRTS database, plus write access
for document review selections and qualification notes.
Mirrors the Oregon ECSI / MILO CRM db.py pattern.
"""
import sqlite3
from pathlib import Path

from config import DATABASE_PATH

VALID_SORT_COLUMNS = {
    'brrts_number', 'activity_name', 'activity_type', 'status',
    'county', 'address', 'start_date', 'end_date',
    'action_count', 'substance_count', 'document_count', 'municipality',
}


def get_connection():
    """Get a read-only database connection with WAL mode."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA query_only=ON")
    return conn


def get_write_connection():
    """Get a write-capable connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def scalar(sql: str, params: tuple = ()):
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they don't exist."""
    conn = get_write_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT UNIQUE NOT NULL,
                detail_seq_no INTEGER,
                site_id INTEGER,
                activity_name TEXT,
                activity_type TEXT,
                act_code TEXT,
                status TEXT,
                county TEXT,
                county_code TEXT,
                address TEXT,
                municipality TEXT,
                zip_code TEXT,
                region TEXT,
                fid_number TEXT,
                location_name TEXT,
                start_date TEXT,
                end_date TEXT,
                last_action TEXT,
                activity_comment TEXT,
                latitude REAL,
                longitude REAL,
                project_manager TEXT,
                responsible_party TEXT,
                action_count INTEGER DEFAULT 0,
                substance_count INTEGER DEFAULT 0,
                source_url TEXT,
                /* Flags from bulk data */
                pecfa_flag INTEGER DEFAULT 0,
                drycleaner_flag INTEGER DEFAULT 0,
                co_contamination_flag INTEGER DEFAULT 0,
                npl_flag INTEGER DEFAULT 0,
                derf_flag INTEGER DEFAULT 0,
                pfas_flag INTEGER DEFAULT 0,
                sediments_flag INTEGER DEFAULT 0,
                petrol_ust_flag INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_sites_brrts ON sites(brrts_number);
            CREATE INDEX IF NOT EXISTS idx_sites_dsn ON sites(detail_seq_no);
            CREATE INDEX IF NOT EXISTS idx_sites_type ON sites(activity_type);
            CREATE INDEX IF NOT EXISTS idx_sites_status ON sites(status);
            CREATE INDEX IF NOT EXISTS idx_sites_county ON sites(county);

            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT NOT NULL,
                detail_seq_no INTEGER,
                action_date TEXT,
                action_code TEXT,
                action_name TEXT,
                action_desc TEXT,
                action_comment TEXT,
                FOREIGN KEY (brrts_number) REFERENCES sites(brrts_number)
            );

            CREATE INDEX IF NOT EXISTS idx_actions_brrts ON actions(brrts_number);

            CREATE TABLE IF NOT EXISTS substances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT NOT NULL,
                detail_seq_no INTEGER,
                substance_name TEXT,
                released_amount TEXT,
                released_unit TEXT,
                FOREIGN KEY (brrts_number) REFERENCES sites(brrts_number)
            );

            CREATE INDEX IF NOT EXISTS idx_substances_brrts ON substances(brrts_number);

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT NOT NULL,
                detail_seq_no INTEGER,
                doc_seq_no INTEGER UNIQUE,
                title TEXT,
                document_date TEXT,
                document_type TEXT,
                document_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brrts_number) REFERENCES sites(brrts_number)
            );

            CREATE INDEX IF NOT EXISTS idx_documents_brrts ON documents(brrts_number);
            CREATE INDEX IF NOT EXISTS idx_documents_doc_seq ON documents(doc_seq_no);

            CREATE TABLE IF NOT EXISTS document_review_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                brrts_number TEXT NOT NULL,
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id)
            );

            CREATE TABLE IF NOT EXISTS site_qualification_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Site queries
# ---------------------------------------------------------------------------

def get_sites(activity_type='', status='', county='', search='',
              has_substances='', has_documents='', pfas_flag='',
              sort='start_date', order='desc',
              page=1, per_page=25) -> tuple[list[dict], int]:
    conditions = []
    params = []

    if activity_type:
        conditions.append("s.activity_type = ?")
        params.append(activity_type)

    if status:
        conditions.append("s.status = ?")
        params.append(status)

    if county:
        conditions.append("s.county = ?")
        params.append(county)

    if has_substances == '1':
        conditions.append("s.brrts_number IN (SELECT DISTINCT brrts_number FROM substances)")

    if has_documents == '1':
        conditions.append("s.brrts_number IN (SELECT DISTINCT brrts_number FROM documents)")

    if pfas_flag == '1':
        conditions.append("s.pfas_flag = 1")

    if search:
        conditions.append("(s.activity_name LIKE ? OR s.brrts_number LIKE ? OR s.address LIKE ? OR s.municipality LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # For count query, replace s. prefix since it has no alias
    count_where = where.replace("s.", "")
    total = scalar(f"SELECT COUNT(*) FROM sites {count_where}", tuple(params))

    if sort not in VALID_SORT_COLUMNS:
        sort = 'start_date'
    order_dir = 'ASC' if order == 'asc' else 'DESC'

    null_sort = f"s.{sort} IS NULL," if sort in ('start_date', 'end_date') else ""
    order_clause = f"ORDER BY {null_sort} s.{sort} {order_dir}"

    offset = (page - 1) * per_page
    data_sql = f"""
        SELECT s.brrts_number, s.activity_name, s.activity_type, s.status,
               s.county, s.address, s.municipality, s.region, s.start_date, s.end_date,
               s.last_action, s.action_count, s.substance_count, s.latitude, s.longitude,
               s.project_manager, s.source_url,
               (SELECT COUNT(*) FROM documents d WHERE d.brrts_number = s.brrts_number) as document_count
        FROM sites s
        {where}
        {order_clause}
        LIMIT ? OFFSET ?
    """
    rows = query(data_sql, tuple(params) + (per_page, offset))
    return rows, total


def get_site(brrts_number: str) -> dict | None:
    return query_one("SELECT * FROM sites WHERE brrts_number = ?", (brrts_number,))


def get_site_actions(brrts_number: str) -> list[dict]:
    return query(
        """SELECT id, action_date, action_code, action_name, action_desc, action_comment
           FROM actions WHERE brrts_number = ?
           ORDER BY action_date DESC, id DESC""",
        (brrts_number,)
    )


def get_site_substances(brrts_number: str) -> list[dict]:
    return query(
        """SELECT id, substance_name, released_amount, released_unit
           FROM substances WHERE brrts_number = ?
           ORDER BY substance_name""",
        (brrts_number,)
    )


def get_filter_options() -> dict:
    return {
        'activity_types': [r['activity_type'] for r in query(
            "SELECT DISTINCT activity_type FROM sites WHERE activity_type IS NOT NULL ORDER BY activity_type"
        )],
        'statuses': [r['status'] for r in query(
            "SELECT DISTINCT status FROM sites WHERE status IS NOT NULL ORDER BY status"
        )],
        'counties': [r['county'] for r in query(
            "SELECT DISTINCT county FROM sites WHERE county IS NOT NULL AND county != '' ORDER BY county"
        )],
    }


def get_dashboard_stats() -> dict:
    stats = {}
    stats['total_sites'] = scalar("SELECT COUNT(*) FROM sites") or 0
    stats['open_sites'] = scalar(
        "SELECT COUNT(*) FROM sites WHERE status = 'OPEN'") or 0
    stats['closed_sites'] = scalar(
        "SELECT COUNT(*) FROM sites WHERE status = 'CLOSED'") or 0
    stats['with_actions'] = scalar(
        "SELECT COUNT(DISTINCT brrts_number) FROM actions") or 0
    stats['with_substances'] = scalar(
        "SELECT COUNT(DISTINCT brrts_number) FROM substances") or 0
    stats['total_actions'] = scalar("SELECT COUNT(*) FROM actions") or 0
    stats['total_substances'] = scalar("SELECT COUNT(*) FROM substances") or 0
    stats['pfas_sites'] = scalar(
        "SELECT COUNT(*) FROM sites WHERE pfas_flag = 1") or 0
    stats['total_documents'] = scalar("SELECT COUNT(*) FROM documents") or 0
    stats['with_documents'] = scalar(
        "SELECT COUNT(DISTINCT brrts_number) FROM documents") or 0

    stats['by_type'] = query("""
        SELECT activity_type, COUNT(*) as count
        FROM sites WHERE activity_type IS NOT NULL
        GROUP BY activity_type ORDER BY count DESC
    """)
    stats['by_status'] = query("""
        SELECT status, COUNT(*) as count
        FROM sites WHERE status IS NOT NULL
        GROUP BY status ORDER BY count DESC
    """)
    stats['by_county'] = query("""
        SELECT county, COUNT(*) as count
        FROM sites WHERE county IS NOT NULL AND county != ''
        GROUP BY county ORDER BY count DESC
        LIMIT 20
    """)
    return stats


# ---------------------------------------------------------------------------
# Document review selections
# ---------------------------------------------------------------------------

def get_site_selections(brrts_number: str) -> set[int]:
    rows = query(
        "SELECT document_id FROM document_review_selections WHERE brrts_number = ?",
        (brrts_number,)
    )
    return {r['document_id'] for r in rows}


def get_selection_count(brrts_number: str) -> int:
    return scalar(
        "SELECT COUNT(*) FROM document_review_selections WHERE brrts_number = ?",
        (brrts_number,)
    ) or 0


def toggle_document_selection(document_id: int, brrts_number: str) -> bool:
    conn = get_write_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM document_review_selections WHERE document_id = ?",
            (document_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM document_review_selections WHERE document_id = ?",
                (document_id,)
            )
            conn.commit()
            return False
        else:
            conn.execute(
                "INSERT INTO document_review_selections (document_id, brrts_number) VALUES (?, ?)",
                (document_id, brrts_number)
            )
            conn.commit()
            return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Qualification notes
# ---------------------------------------------------------------------------

def get_site_notes(brrts_number: str) -> list[dict]:
    return query(
        """SELECT id, brrts_number, note_text, created_at, updated_at
           FROM site_qualification_notes
           WHERE brrts_number = ? ORDER BY created_at DESC""",
        (brrts_number,)
    )


def add_site_note(brrts_number: str, note_text: str) -> dict:
    conn = get_write_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO site_qualification_notes (brrts_number, note_text) VALUES (?, ?)",
            (brrts_number, note_text)
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM site_qualification_notes WHERE id = ?", (new_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Document scraping support
# ---------------------------------------------------------------------------

def ensure_documents_table():
    """Create documents table and add scraping columns to sites.

    Safe to call multiple times -- uses IF NOT EXISTS and catches
    'duplicate column' errors from ALTER TABLE.
    """
    conn = get_write_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brrts_number TEXT NOT NULL,
                detail_seq_no INTEGER,
                doc_seq_no INTEGER UNIQUE,
                title TEXT,
                document_date TEXT,
                document_type TEXT,
                document_url TEXT,
                document_category TEXT,
                action_code TEXT,
                action_name TEXT,
                comment TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brrts_number) REFERENCES sites(brrts_number)
            );
            CREATE INDEX IF NOT EXISTS idx_documents_brrts ON documents(brrts_number);
            CREATE INDEX IF NOT EXISTS idx_documents_doc_seq ON documents(doc_seq_no);
        """)
        # Add new columns to existing documents table if missing
        for col_sql in [
            "ALTER TABLE documents ADD COLUMN document_category TEXT",
            "ALTER TABLE documents ADD COLUMN action_code TEXT",
            "ALTER TABLE documents ADD COLUMN action_name TEXT",
            "ALTER TABLE documents ADD COLUMN comment TEXT",
        ]:
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass  # Column already exists
        for col_sql in [
            "ALTER TABLE sites ADD COLUMN document_count INTEGER DEFAULT 0",
            "ALTER TABLE sites ADD COLUMN docs_scraped INTEGER DEFAULT 0",
            "ALTER TABLE sites ADD COLUMN docs_scraped_at TIMESTAMP",
        ]:
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sites_docs_scraped ON sites(docs_scraped)")
        conn.commit()
    finally:
        conn.close()


def insert_documents(brrts_number: str, detail_seq_no: int, docs: list[dict]):
    """Insert documents for a site and update the document_count."""
    conn = get_write_connection()
    try:
        for d in docs:
            conn.execute("""
                INSERT OR IGNORE INTO documents
                    (brrts_number, detail_seq_no, doc_seq_no, title,
                     document_date, document_type, document_url,
                     document_category, action_code, action_name, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brrts_number, detail_seq_no,
                d.get('doc_seq_no'), d.get('title'),
                d.get('document_date'), d.get('document_type'),
                d.get('document_url'),
                d.get('document_category'), d.get('action_code'),
                d.get('action_name'), d.get('comment'),
            ))
        conn.execute(
            "UPDATE sites SET document_count = ? WHERE brrts_number = ?",
            (len(docs), brrts_number)
        )
        conn.commit()
    finally:
        conn.close()


def mark_docs_scraped(brrts_number: str, status: int = 1):
    """Mark a site's document scrape status (1=done, -1=failed)."""
    conn = get_write_connection()
    try:
        conn.execute(
            "UPDATE sites SET docs_scraped = ?, docs_scraped_at = CURRENT_TIMESTAMP WHERE brrts_number = ?",
            (status, brrts_number)
        )
        conn.commit()
    finally:
        conn.close()


def get_unscraped_dsns(limit: int = 1000) -> list[dict]:
    """Get sites that haven't been scraped for documents yet.

    Orders by start_date DESC (newest first) so recent sites are prioritized.
    """
    return query(
        """SELECT brrts_number, detail_seq_no
           FROM sites
           WHERE docs_scraped = 0 AND detail_seq_no IS NOT NULL
           ORDER BY start_date DESC NULLS LAST, detail_seq_no DESC
           LIMIT ?""",
        (limit,)
    )


def get_failed_dsns(limit: int = 1000) -> list[dict]:
    """Get sites where document scraping previously failed."""
    return query(
        """SELECT brrts_number, detail_seq_no
           FROM sites
           WHERE docs_scraped = -1 AND detail_seq_no IS NOT NULL
           ORDER BY detail_seq_no
           LIMIT ?""",
        (limit,)
    )


def get_docs_scrape_progress() -> dict:
    """Return document scraping progress stats."""
    return {
        'total': scalar("SELECT COUNT(*) FROM sites WHERE detail_seq_no IS NOT NULL") or 0,
        'scraped': scalar("SELECT COUNT(*) FROM sites WHERE docs_scraped = 1") or 0,
        'failed': scalar("SELECT COUNT(*) FROM sites WHERE docs_scraped = -1") or 0,
        'pending': scalar("SELECT COUNT(*) FROM sites WHERE docs_scraped = 0 AND detail_seq_no IS NOT NULL") or 0,
        'total_documents': scalar("SELECT COUNT(*) FROM documents") or 0,
        'sites_with_docs': scalar("SELECT COUNT(DISTINCT brrts_number) FROM documents") or 0,
    }


def get_site_documents(brrts_number: str) -> list[dict]:
    """Get all documents for a site."""
    return query(
        """SELECT id, doc_seq_no, title, document_date, document_type, document_url,
                  document_category, action_code, action_name, comment
           FROM documents WHERE brrts_number = ?
           ORDER BY document_date DESC, id DESC""",
        (brrts_number,)
    )
