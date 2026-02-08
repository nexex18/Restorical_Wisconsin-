"""
Wisconsin DNR BRRTS Scraper - Configuration
"""
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "wisconsin_brrts.db"

# Logs
LOG_DIR = BASE_DIR / "logs"

# Wisconsin DNR URLs
BRRTS_BASE_URL = "https://apps.dnr.wi.gov"
BRRTS_SEARCH_URL = f"{BRRTS_BASE_URL}/rrbotw/botw-search"
BRRTS_RESULTS_URL = f"{BRRTS_BASE_URL}/rrbotw/botw-results"
BRRTS_DETAIL_URL = f"{BRRTS_BASE_URL}/rrbotw/botw-activity-detail"

# BRRTS activity type codes (first 2 digits of BRRTS number)
ACTIVITY_TYPES = {
    "02": "ERP",
    "03": "LUST",
    "04": "Spills",
    "05": "NAR",
}

# Wisconsin counties (72 total)
WISCONSIN_COUNTIES = [
    "Adams", "Ashland", "Barron", "Bayfield", "Brown", "Buffalo", "Burnett",
    "Calumet", "Chippewa", "Clark", "Columbia", "Crawford", "Dane", "Dodge",
    "Door", "Douglas", "Dunn", "Eau Claire", "Florence", "Fond du Lac",
    "Forest", "Grant", "Green", "Green Lake", "Iowa", "Iron", "Jackson",
    "Jefferson", "Juneau", "Kenosha", "Kewaunee", "La Crosse", "Lafayette",
    "Langlade", "Lincoln", "Manitowoc", "Marathon", "Marinette", "Marquette",
    "Menominee", "Milwaukee", "Monroe", "Oconto", "Oneida", "Outagamie",
    "Ozaukee", "Pepin", "Pierce", "Polk", "Portage", "Price", "Racine",
    "Richland", "Rock", "Rusk", "Sauk", "Sawyer", "Shawano", "Sheboygan",
    "St. Croix", "Taylor", "Trempealeau", "Vernon", "Vilas", "Walworth",
    "Washburn", "Washington", "Waukesha", "Waupaca", "Waushara", "Winnebago",
    "Wood",
]

# Timeouts (milliseconds)
TIMEOUTS = {
    "page_load": 60000,
    "selector_wait": 15000,
    "networkidle": 15000,
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

# Scrape settings
DEFAULT_HEADLESS = True
MAX_SITES = 500  # Proof-of-concept limit

# Cloudflare Worker proxy (for scraping from blocked IPs)
WORKER_URL = "https://browser-scraper.darrenwsilver.workers.dev/"

# Site browser
BROWSER_PORT = 5010


def ensure_directories():
    """Create required directories if they don't exist."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
