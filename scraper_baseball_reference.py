"""
Scraper for Baseball Reference college baseball statistics.
Handles both hitting and pitching stats for multiple conferences.
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
import re
from config import BASEBALL_REFERENCE_BASE_URL, REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseballReferenceScraper:
    """Scrapes hitting and pitching statistics from Baseball Reference."""
    
    def __init__(self):
        """Initialize the scraper with session and headers."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """
        Make HTTP request and return BeautifulSoup object.
        
        Args:
            url: URL to scrape
            
        Returns:
            BeautifulSoup object or None if request fails
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            time.sleep(REQUEST_DELAY)  # Be respectful with delays
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _parse_stat_value(self, value: str) -> Optional[float]:
        """
        Parse a stat value from string to number.
        Handles empty strings, dashes, and various number formats.
        
        Args:
            value: String value to parse
            
        Returns:
            Numeric value or None
        """
        if not value or value == '' or value == '-' or value.strip() == '':
            return None
        
        # Remove commas and whitespace
        value = value.replace(',', '').strip()
        
        try:
            # Try to parse as float first (for decimals like ERA, AVG)
            return float(value)
        except ValueError:
            try:
                # Try as integer
                return int(value)
            except ValueError:
                return None
    
    def _extract_season_from_url(self, url: str) -> Optional[int]:
        """
        Extract season year from URL if available.
        
        Args:
            url: URL to extract season from
            
        Returns:
            Season year or None
        """
        # Look for year pattern in URL
        match = re.search(r'year=(\d{4})', url)
        if match:
            return int(match.group(1))
        return None
    
    def _parse_player_name(self, cell) -> tuple:
        """
        Parse player name and school from table cell.
        
        Args:
            cell: BeautifulSoup table cell element
            
        Returns:
            Tuple of (name, school)
        """
        name = None
        school = None
        
        # Try to find anchor tag with player name
        anchor = cell.find('a')
        if anchor:
            name = anchor.get_text(strip=True)
            # School might be in title or data attribute
            title = anchor.get('title', '')
            if title:
                # Extract school from title if available
                school_match = re.search(r'\(([^)]+)\)', title)
                if school_match:
                    school = school_match.group(1)
        
        # If no anchor, just get text
        if not name:
            text = cell.get_text(strip=True)
            # Try to split by common delimiters
            if '|' in text:
                parts = text.split('|')
                name = parts[0].strip()
                if len(parts) > 1:
                    school = parts[1].strip()
            else:
                name = text
        
        return (name, school)
    
    def scrape_hitting_stats(self, conference_id: str) -> List[Dict]:
        """
        Scrape hitting statistics for a conference.
        
        Args:
            conference_id: Baseball Reference conference ID
            
        Returns:
            List of dictionaries containing hitting stats for each player
        """
        url = f"{BASEBALL_REFERENCE_BASE_URL}?type=bat&id={conference_id}"
        soup = self._make_request(url)
        
        if not soup:
            logger.error(f"Failed to fetch hitting stats for conference {conference_id}")
            return []
        
        stats_list = []
        
        # Find the main stats table
        table = soup.find('table', {'id': 'leaderboard'})
        if not table:
            # Try alternative table IDs/classes
            table = soup.find('table', class_=re.compile(r'table|stats'))
            if not table:
                logger.warning(f"No stats table found for hitting stats (conference {conference_id})")
                return []
        
        # Extract season from page if available
        season = self._extract_season_from_url(url)
        if not season:
            # Try to find season in page content
            season_text = soup.find(string=re.compile(r'\b(20\d{2})\b'))
            if season_text:
                match = re.search(r'\b(20\d{2})\b', season_text)
                if match:
                    season = int(match.group(1))
        
        # Get table headers
        headers = []
        header_row = table.find('thead')
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
            headers = [cell.get_text(strip=True).lower().replace(' ', '_') for cell in header_cells]
        else:
            # Try first row as headers
            first_row = table.find('tr')
            if first_row:
                header_cells = first_row.find_all(['th', 'td'])
                headers = [cell.get_text(strip=True).lower().replace(' ', '_') for cell in header_cells]
        
        # Find column indices (same as pitching stats)
        # Try multiple variations of header names
        name_col_idx = None
        school_col_idx = None
        age_col_idx = None
        team_col_idx = None
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            if ('name' in header_lower or 'player' in header_lower) and name_col_idx is None:
                name_col_idx = i
            if 'school' in header_lower or 'college' in header_lower:
                school_col_idx = i
            if header_lower == 'age' or header_lower.startswith('age'):
                age_col_idx = i
            if header_lower == 'tm' or header_lower == 'team' or header_lower.startswith('tm'):
                team_col_idx = i
        
        # Default to column 1 if name header not found (skip rank column)
        if name_col_idx is None:
            name_col_idx = 1
        
        # Log column indices for debugging
        logger.debug(f"Hitting stats column indices - name: {name_col_idx}, age: {age_col_idx}, team: {team_col_idx}, school: {school_col_idx}")
        
        # Find data rows
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]  # Skip header row
        
        # Debug: Print first few headers to understand structure
        if len(rows) > 0:
            first_data_row = rows[0]
            first_cells = first_data_row.find_all(['td', 'th'])
            logger.debug(f"First row has {len(first_cells)} cells, headers: {headers[:min(10, len(headers))]}")
        
        for row in rows:
            # Skip header rows
            if row.find('th') and not row.find('td'):
                continue
            
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # Parse player name from the name column
            if name_col_idx < len(cells):
                name, school = self._parse_player_name(cells[name_col_idx])
            else:
                continue
            
            # Extract age if available (same as pitching stats)
            # Try multiple column positions if age_col_idx not found
            age = None
            if age_col_idx is not None and age_col_idx < len(cells):
                age_text = cells[age_col_idx].get_text(strip=True)
                age = self._parse_stat_value(age_text)
            
            # If still no age, try to find it by scanning all cells
            if age is None:
                for idx, cell in enumerate(cells):
                    if idx == name_col_idx:  # Skip name column
                        continue
                    cell_text = cell.get_text(strip=True)
                    # Check if it looks like an age (single or double digit number)
                    if cell_text.isdigit():
                        age_val = int(cell_text)
                        if 15 <= age_val <= 30:  # Reasonable age range
                            age = age_val
                            break
            
            # Extract team (Tm) - this is the school abbreviation (same as pitching stats)
            # Try multiple column positions if team_col_idx not found
            team_abbrev = None
            if team_col_idx is not None and team_col_idx < len(cells):
                team_abbrev = cells[team_col_idx].get_text(strip=True)
            
            # If still no team, try to find it by scanning all cells
            if not team_abbrev:
                for idx, cell in enumerate(cells):
                    if idx == name_col_idx:  # Skip name column
                        continue
                    cell_text = cell.get_text(strip=True).upper()
                    # Check if it looks like a team abbreviation (2-4 uppercase letters, no numbers)
                    if (len(cell_text) >= 2 and len(cell_text) <= 4 and 
                        cell_text.isalpha() and 
                        cell_text not in ['G', 'GS', 'CG', 'SHO', 'W', 'L', 'SV', 'IP', 'H', 'R', 'ER', 'HR', 'BB', 'SO', 'ERA', 'WHIP']):
                        # Make sure it's not a stat abbreviation
                        team_abbrev = cell_text
                        break
            
            # If school column exists separately, use it
            if school_col_idx is not None and school_col_idx < len(cells):
                school_text = cells[school_col_idx].get_text(strip=True)
                if school_text and not school:
                    school = school_text
            
            # If no school found but we have team abbreviation, use it (same as pitching stats)
            if not school and team_abbrev:
                school = team_abbrev
            
            # If still no school, try to extract from name cell or other cells
            if not school:
                # Check if school might be in parentheses in the name
                if '(' in name and ')' in name:
                    match = re.search(r'\(([^)]+)\)', name)
                    if match:
                        school = match.group(1).strip()
                        # Clean up name
                        name = re.sub(r'\s*\([^)]+\)\s*', '', name).strip()
            
            if not name:
                continue
            
            # Build stats dictionary (include age and team like pitching stats)
            stats = {
                'name': name,
                'school': school,
                'age': age,
                'team': team_abbrev,
                'season': season
            }
            
            # Map common stat column names
            stat_mapping = {
                'rk': 'rank',
                'name': 'name',
                'school': 'school',
                'age': 'age',
                'tm': 'team',
                'team': 'team',
                'g': 'games',
                'ab': 'at_bats',
                'r': 'runs',
                'h': 'hits',
                '2b': 'doubles',
                '3b': 'triples',
                'hr': 'home_runs',
                'rbi': 'rbi',
                'bb': 'walks',
                'so': 'strikeouts',
                'avg': 'avg',
                'obp': 'obp',
                'slg': 'slg',
                'ops': 'ops',
                'sb': 'stolen_bases',
                'cs': 'caught_stealing',
                'hbp': 'hit_by_pitch',
                'sf': 'sacrifice_flys',
                'sh': 'sacrifice_hits',
                'ibb': 'intentional_walks',
                'gidp': 'ground_into_double_play',
                'pa': 'plate_appearances',
                'tb': 'total_bases'
            }
            
            # Extract stats from each column
            for i, cell in enumerate(cells):
                if i >= len(headers):
                    break
                
                header = headers[i]
                value = cell.get_text(strip=True)
                
                # Map header to stat name
                stat_name = stat_mapping.get(header, header)
                
                # Skip name/school/age/team columns (already extracted)
                if stat_name in ['name', 'school', 'rank', 'age', 'team']:
                    continue
                
                # Parse numeric value
                parsed_value = self._parse_stat_value(value)
                if parsed_value is not None:
                    stats[stat_name] = parsed_value
                elif stat_name not in stats:  # Keep None for missing stats
                    stats[stat_name] = None
            
            if stats.get('name'):
                stats_list.append(stats)
        
        logger.info(f"Scraped {len(stats_list)} hitting stat records for conference {conference_id}")
        return stats_list
    
    def scrape_pitching_stats(self, conference_id: str) -> List[Dict]:
        """
        Scrape pitching statistics for a conference.
        
        Args:
            conference_id: Baseball Reference conference ID
            
        Returns:
            List of dictionaries containing pitching stats for each player
        """
        url = f"{BASEBALL_REFERENCE_BASE_URL}?type=pitch&id={conference_id}"
        soup = self._make_request(url)
        
        if not soup:
            logger.error(f"Failed to fetch pitching stats for conference {conference_id}")
            return []
        
        stats_list = []
        
        # Find the main stats table
        table = soup.find('table', {'id': 'leaderboard'})
        if not table:
            # Try alternative table IDs/classes
            table = soup.find('table', class_=re.compile(r'table|stats'))
            if not table:
                logger.warning(f"No stats table found for pitching stats (conference {conference_id})")
                return []
        
        # Extract season from page if available
        season = self._extract_season_from_url(url)
        if not season:
            # Try to find season in page content
            season_text = soup.find(string=re.compile(r'\b(20\d{2})\b'))
            if season_text:
                match = re.search(r'\b(20\d{2})\b', season_text)
                if match:
                    season = int(match.group(1))
        
        # Get table headers
        headers = []
        header_row = table.find('thead')
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
            headers = [cell.get_text(strip=True).lower().replace(' ', '_') for cell in header_cells]
        else:
            # Try first row as headers
            first_row = table.find('tr')
            if first_row:
                header_cells = first_row.find_all(['th', 'td'])
                headers = [cell.get_text(strip=True).lower().replace(' ', '_') for cell in header_cells]
        
        # Find data rows
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]  # Skip header row
        
        # Find column indices
        name_col_idx = None
        school_col_idx = None
        age_col_idx = None
        team_col_idx = None
        for i, header in enumerate(headers):
            if 'name' in header and name_col_idx is None:
                name_col_idx = i
            if 'school' in header:
                school_col_idx = i
            if header == 'age':
                age_col_idx = i
            if header == 'tm' or header == 'team':
                team_col_idx = i
        
        # Default to column 1 if name header not found (skip rank column)
        if name_col_idx is None:
            name_col_idx = 1
        
        for row in rows:
            # Skip header rows
            if row.find('th') and not row.find('td'):
                continue
            
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # Parse player name from the name column
            if name_col_idx < len(cells):
                name, school = self._parse_player_name(cells[name_col_idx])
            else:
                continue
            
            # Extract age if available
            age = None
            if age_col_idx is not None and age_col_idx < len(cells):
                age_text = cells[age_col_idx].get_text(strip=True)
                age = self._parse_stat_value(age_text)
            
            # Extract team (Tm) - this is the school abbreviation
            team_abbrev = None
            if team_col_idx is not None and team_col_idx < len(cells):
                team_abbrev = cells[team_col_idx].get_text(strip=True)
            
            # If school column exists separately, use it
            if school_col_idx is not None and school_col_idx < len(cells):
                school_text = cells[school_col_idx].get_text(strip=True)
                if school_text and not school:
                    school = school_text
            
            # If no school found but we have team abbreviation, use it
            if not school and team_abbrev:
                school = team_abbrev
            
            if not name:
                continue
            
            # Build stats dictionary
            stats = {
                'name': name,
                'school': school,
                'age': age,
                'team': team_abbrev,
                'season': season
            }
            
            # Map common stat column names
            stat_mapping = {
                'rk': 'rank',
                'name': 'name',
                'school': 'school',
                'age': 'age',
                'tm': 'team',
                'team': 'team',
                'g': 'games',
                'gs': 'games_started',
                'cg': 'complete_games',
                'sho': 'shutouts',
                'w': 'wins',
                'l': 'losses',
                'sv': 'saves',
                'ip': 'innings_pitched',
                'h': 'hits_allowed',
                'r': 'runs_allowed',
                'er': 'earned_runs',
                'hr': 'home_runs_allowed',
                'bb': 'walks',
                'so': 'strikeouts',
                'era': 'era',
                'whip': 'whip',
                'bf': 'batters_faced',
                'wp': 'wild_pitches',
                'hbp': 'hit_batters',
                'bk': 'balks'
            }
            
            # Extract stats from each column
            for i, cell in enumerate(cells):
                if i >= len(headers):
                    break
                
                header = headers[i]
                value = cell.get_text(strip=True)
                
                # Map header to stat name
                stat_name = stat_mapping.get(header, header)
                
                # Skip name/school/age/team columns (already extracted)
                if stat_name in ['name', 'school', 'rank', 'age', 'team']:
                    continue
                
                # Parse numeric value
                parsed_value = self._parse_stat_value(value)
                if parsed_value is not None:
                    stats[stat_name] = parsed_value
                elif stat_name not in stats:  # Keep None for missing stats
                    stats[stat_name] = None
            
            if stats.get('name'):
                stats_list.append(stats)
        
        logger.info(f"Scraped {len(stats_list)} pitching stat records for conference {conference_id}")
        return stats_list
    
    def scrape_conference(self, conference_id: str) -> Dict:
        """
        Scrape both hitting and pitching stats for a conference.
        
        Args:
            conference_id: Baseball Reference conference ID
            
        Returns:
            Dictionary with 'hitting' and 'pitching' keys containing stat lists
        """
        logger.info(f"Scraping conference {conference_id}")
        hitting_stats = self.scrape_hitting_stats(conference_id)
        pitching_stats = self.scrape_pitching_stats(conference_id)
        
        return {
            'hitting': hitting_stats,
            'pitching': pitching_stats
        }

