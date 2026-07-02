"""
Configuration file for database connection and conference IDs.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'college_baseball'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# Conference configuration with Baseball Reference IDs
# Big 4 Conferences in College Baseball
CONFERENCES = {
    'sec': {
        'name': 'SEC',
        'reference_id': '00e321b3'
    },
    'acc': {
        'name': 'ACC',
        'reference_id': '7beb4f46'
    },
    'big12': {
        'name': 'Big 12',
        'reference_id': '82d1384a'
    },
    'pac12': {
        'name': 'Pac-12',
        'reference_id': 'eff09df9'
    }
}

# Draft results URLs
ESPN_DRAFT_URL = 'https://www.espn.com/mlb/draft/results'  # Main draft results page
ESPN_DRAFT_STORY_URL = 'https://www.espn.com/mlb/story/_/id/45694406/2025-mlb-draft-tracker-live-updates-order-results-analysis-every-first-round-pick'  # Story page (JS-rendered)
BASEBALL_AMERICA_DRAFT_URL = 'https://www.baseballamerica.com/draft-results/'  # Fallback

# Baseball Reference base URL
BASEBALL_REFERENCE_BASE_URL = 'https://www.baseball-reference.com/register/leader.cgi'

# Scraping configuration
REQUEST_DELAY = 2  # Seconds to wait between requests
REQUEST_TIMEOUT = 30  # Request timeout in seconds
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

