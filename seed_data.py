"""
Seed realistic test data for the Wisconsin BRRTS site browser.
Generates ~500 sites with documents, actions, and substances.
"""
import json
import random
import sqlite3
from datetime import datetime, timedelta

from config import DATABASE_PATH, WISCONSIN_COUNTIES, ensure_directories
import db

ensure_directories()

random.seed(42)

ACTIVITY_TYPES = ['ERP', 'LUST', 'Spills', 'NAR']
STATUSES = ['Open', 'Closed']
TYPE_CODES = {'ERP': '02', 'LUST': '03', 'Spills': '04', 'NAR': '05'}
COUNTY_CODES = {c: f"{i+1:02d}" for i, c in enumerate(WISCONSIN_COUNTIES)}

BUSINESS_WORDS = [
    'Gas Station', 'Auto Repair', 'Dry Cleaner', 'Manufacturing', 'Former',
    'Industrial', 'Commercial', 'Residential', 'Municipal', 'Agricultural',
    'Landfill', 'Storage', 'Service', 'Supply', 'Co-op', 'Plant',
    'Facility', 'Property', 'Site', 'Well', 'Tank', 'Shop',
]

NAMES = [
    'Anderson', 'Miller', 'Johnson', 'Smith', 'Williams', 'Brown', 'Jones',
    'Garcia', 'Davis', 'Wilson', 'Nelson', 'Thompson', 'Schultz', 'Mueller',
    'Schmidt', 'Bauer', 'Fischer', 'Wagner', 'Weber', 'Hoffmann',
    'Kwik Trip', 'BP', 'Shell', 'Cenex', "Fleet Farm", 'Menards',
    'Walmart', 'Pick N Save', 'Piggly Wiggly', 'Festival Foods',
    'Lake Shore', 'River View', 'Oak Park', 'Pine Hill', 'Valley',
    'Eagle', 'Badger', 'Northland', 'Heartland', 'Prairie',
]

STREETS = [
    'Main St', 'Oak Ave', 'Elm St', 'Maple Dr', 'Pine St', 'Cedar Rd',
    'Wisconsin Ave', 'State St', 'Lake Shore Dr', 'Highway 51',
    'County Rd A', 'County Rd B', 'River Rd', 'Park Ave', 'Mill St',
    'Church St', 'Water St', 'Spring St', 'College Ave', 'Broadway',
    'Grand Ave', 'Market St', 'Third St', 'Second Ave', 'Division St',
]

MUNICIPALITIES = [
    'Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine', 'Appleton',
    'Waukesha', 'Eau Claire', 'Oshkosh', 'Janesville', 'West Allis',
    'La Crosse', 'Sheboygan', 'Wauwatosa', 'Fond du Lac', 'Brookfield',
    'New Berlin', 'Wausau', 'Greenfield', 'Manitowoc', 'West Bend',
    'Stevens Point', 'Beloit', 'Fitchburg', 'Sun Prairie', 'Muskego',
    'Superior', 'Marshfield', 'Neenah', 'Menomonee Falls', 'Portage',
]

REGIONS = ['Northern', 'Northeast', 'Southeast', 'Southern', 'West Central']

SUBSTANCE_NAMES = [
    'Petroleum', 'Gasoline', 'Diesel Fuel', 'Fuel Oil', 'Motor Oil',
    'Chlorinated Solvents', 'TCE (Trichloroethylene)', 'PCE (Tetrachloroethylene)',
    'Benzene', 'Toluene', 'Ethylbenzene', 'Xylene', 'BTEX',
    'Lead', 'Arsenic', 'Chromium', 'Mercury', 'Cadmium',
    'PAHs (Polycyclic Aromatic Hydrocarbons)', 'PCBs (Polychlorinated Biphenyls)',
    'PFAS', 'PFOA', 'PFOS', 'Asbestos', 'Pesticides', 'Herbicides',
    'Volatile Organic Compounds (VOCs)', 'Semi-Volatile Organic Compounds (SVOCs)',
    'Metals', 'Waste Oil',
]

MEDIUMS = ['Soil', 'Groundwater', 'Soil & Groundwater', 'Sediment', 'Indoor Air', 'Surface Water']

DOCUMENT_TYPES = [
    'Closure Letter', 'Site Investigation Report', 'Remedial Action Plan',
    'Risk Assessment', 'Continuing Obligations', 'Phase I ESA',
    'Phase II ESA', 'Monitoring Report', 'Correspondence', 'Work Plan',
    'Quarterly Report', 'Annual Report', 'Soil Boring Logs',
    'Groundwater Sampling Results', 'Vapor Intrusion Assessment',
    'Corrective Action Plan', 'GIS Registry', 'Case Summary',
    'LUST Closure Summary', 'Notification Letter', 'Spill Report',
]

ACTION_NAMES = [
    'Site Discovery', 'Initial Response', 'Site Investigation',
    'Interim Action', 'Remedial Investigation', 'Feasibility Study',
    'Remedial Action', 'Long-term Monitoring', 'Case Closure',
    'NR 716 Investigation', 'NR 722 Remedial Action',
    'Soil Excavation', 'Groundwater Extraction', 'Soil Vapor Extraction',
    'Monitored Natural Attenuation', 'Risk Assessment',
    'Continuing Obligations Review', 'Five-Year Review',
    'UST Removal', 'Tank Closure', 'Spill Cleanup',
    'Vapor Intrusion Investigation', 'PFAS Sampling',
]

PM_NAMES = [
    'Sarah Johnson', 'Mike Thompson', 'Lisa Anderson', 'John Mueller',
    'Karen Schmidt', 'David Wilson', 'Jennifer Brown', 'Robert Nelson',
    'Amy Fischer', 'Mark Davis', 'Chris Wagner', 'Laura Martinez',
    'Tom Bauer', 'Michelle Lee', 'James Hoffmann',
]


def random_date(start_year=1990, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')


def random_recent_date():
    return random_date(2020, 2025)


def generate_brrts_number(activity_type, county):
    type_code = TYPE_CODES[activity_type]
    county_code = COUNTY_CODES.get(county, '00')
    seq = random.randint(100000, 999999)
    return f"{type_code}-{county_code}-{seq}"


def generate_activity_name():
    parts = []
    if random.random() > 0.3:
        parts.append(random.choice(NAMES))
    parts.append(random.choice(BUSINESS_WORDS))
    if random.random() > 0.5:
        parts.append(random.choice(BUSINESS_WORDS))
    return ' '.join(parts)


def generate_address():
    num = random.randint(100, 9999)
    return f"{num} {random.choice(STREETS)}"


def generate_site(idx):
    activity_type = random.choices(
        ACTIVITY_TYPES,
        weights=[25, 35, 30, 10],  # LUST most common
        k=1
    )[0]
    county = random.choice(WISCONSIN_COUNTIES)
    brrts_number = generate_brrts_number(activity_type, county)

    # Heavier weight toward closed for older sites
    status = random.choices(
        STATUSES,
        weights=[40, 60] if activity_type != 'Spills' else [20, 80],
        k=1
    )[0]

    created_date = random_date(1990, 2024)
    updated_date = random_date(int(created_date[:4]), 2025)

    dsn = 500000 + idx
    rp_name = random.choice(NAMES)
    if random.random() > 0.5:
        rp_name += f" {random.choice(BUSINESS_WORDS)}"

    municipality = random.choice(MUNICIPALITIES) if random.random() > 0.2 else None
    region = random.choice(REGIONS) if random.random() > 0.1 else None

    # Generate detail data for ~70% of sites
    detail_scraped = 1 if random.random() > 0.3 else 0

    detail_data = None
    if detail_scraped == 1:
        detail_data = json.dumps({
            'characteristics': random.sample(
                ['Contaminated Soil', 'Contaminated Groundwater',
                 'Petroleum Contamination', 'VOC Contamination',
                 'Metals Contamination', 'PFAS Contamination',
                 'Sediment Contamination', 'Vapor Intrusion Concern'],
                k=random.randint(1, 4)
            ),
            'scraped_at': datetime.now().isoformat(),
        })

    return {
        'brrts_number': brrts_number,
        'activity_name': generate_activity_name(),
        'activity_type': activity_type,
        'status': status,
        'county': county,
        'address': generate_address(),
        'municipality': municipality,
        'region': region,
        'fid_number': f"{random.randint(100000, 999999)}" if random.random() > 0.3 else None,
        'site_id': str(dsn),
        'responsible_party': rp_name,
        'project_manager': random.choice(PM_NAMES),
        'detail_scraped': detail_scraped,
        'detail_data': detail_data,
        'document_count': 0,  # Will be updated after docs are inserted
        'source_url': f"https://apps.dnr.wi.gov/rrbotw/botw-activity-detail?dsn={dsn}",
        'last_scraped_at': datetime.now().isoformat() if detail_scraped else None,
        'updated_date': updated_date,
    }


def generate_documents(brrts_number, count):
    docs = []
    for _ in range(count):
        doc_type = random.choice(DOCUMENT_TYPES)
        doc_seq = random.randint(10000, 999999)
        docs.append({
            'title': doc_type,
            'date': random_date(2000, 2025),
            'type': doc_type.split()[0],
            'url': f"https://apps.dnr.wi.gov/rrbotw/download-document?docSeqNo={doc_seq}&sender=activity",
            'doc_seq_no': str(doc_seq),
        })
    return docs


def generate_actions(brrts_number, count):
    acts = []
    selected = random.sample(ACTION_NAMES, k=min(count, len(ACTION_NAMES)))
    for name in selected:
        acts.append({
            'name': name,
            'date': random_date(1995, 2025),
            'description': f"{name} completed for this activity.",
        })
    return acts


def generate_substances(brrts_number, activity_type, count):
    if activity_type == 'LUST':
        pool = ['Petroleum', 'Gasoline', 'Diesel Fuel', 'Fuel Oil', 'BTEX',
                'Benzene', 'Toluene', 'Ethylbenzene', 'Xylene']
    elif activity_type == 'ERP':
        pool = SUBSTANCE_NAMES
    else:
        pool = SUBSTANCE_NAMES[:15]

    selected = random.sample(pool, k=min(count, len(pool)))
    subs = []
    for name in selected:
        subs.append({
            'name': name,
            'medium': random.choice(MEDIUMS),
        })
    return subs


def seed():
    print("Initializing database...")
    db.init_db()

    print("Generating 500 sites...")
    sites = [generate_site(i) for i in range(500)]

    # Ensure unique BRRTS numbers
    seen = set()
    unique_sites = []
    for s in sites:
        if s['brrts_number'] not in seen:
            seen.add(s['brrts_number'])
            unique_sites.append(s)
    sites = unique_sites[:500]

    conn = db.get_write_connection()
    try:
        for i, site in enumerate(sites):
            # Insert site
            db.upsert_site(site)

            brrts = site['brrts_number']

            # Generate documents (most sites have some)
            if site['detail_scraped'] == 1:
                doc_count = random.choices(
                    [0, 1, 2, 3, 5, 8, 12, 20],
                    weights=[5, 10, 20, 25, 20, 10, 7, 3],
                    k=1
                )[0]
            else:
                doc_count = random.choices([0, 1, 2], weights=[50, 30, 20], k=1)[0]

            if doc_count > 0:
                docs = generate_documents(brrts, doc_count)
                db.upsert_documents(brrts, docs)

            # Generate actions
            if site['detail_scraped'] == 1:
                action_count = random.randint(1, 6)
                actions = generate_actions(brrts, action_count)
                db.upsert_actions(brrts, actions)

            # Generate substances
            if site['detail_scraped'] == 1 and site['activity_type'] != 'NAR':
                sub_count = random.randint(1, 5)
                subs = generate_substances(brrts, site['activity_type'], sub_count)
                db.upsert_substances(brrts, subs)

            # Update document count
            actual_doc_count = db.scalar(
                "SELECT COUNT(*) FROM documents WHERE brrts_number = ?", (brrts,)
            ) or 0
            conn_w = db.get_write_connection()
            conn_w.execute(
                "UPDATE sites SET document_count = ? WHERE brrts_number = ?",
                (actual_doc_count, brrts)
            )
            conn_w.commit()
            conn_w.close()

            if (i + 1) % 100 == 0:
                print(f"  Generated {i + 1}/{len(sites)} sites")

    finally:
        conn.close()

    # Log the seeding
    db.log_scrape('seed', 'completed', f'Generated {len(sites)} test sites', len(sites))

    # Print summary
    total = db.scalar("SELECT COUNT(*) FROM sites")
    detail = db.scalar("SELECT COUNT(*) FROM sites WHERE detail_scraped = 1")
    docs = db.scalar("SELECT COUNT(*) FROM documents")
    acts = db.scalar("SELECT COUNT(*) FROM actions")
    subs = db.scalar("SELECT COUNT(*) FROM substances")

    print(f"\nSeed complete!")
    print(f"  Sites:      {total}")
    print(f"  Detailed:   {detail}")
    print(f"  Documents:  {docs}")
    print(f"  Actions:    {acts}")
    print(f"  Substances: {subs}")


if __name__ == '__main__':
    seed()
