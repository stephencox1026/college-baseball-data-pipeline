"""
Scraper for MLB draft results from ESPN and other sources.
Extracts player names, schools, and draft information.
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
import re
import json
from config import ESPN_DRAFT_URL, ESPN_DRAFT_STORY_URL, REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DraftScraper:
    """Scrapes draft results from ESPN and other sources."""
    
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
    
    def _parse_draft_year(self, text: str) -> Optional[int]:
        """
        Extract draft year from text.
        
        Args:
            text: Text that may contain a year
            
        Returns:
            Year as integer or None
        """
        # Look for 4-digit year (2000-2099)
        match = re.search(r'\b(20\d{2})\b', text)
        if match:
            year = int(match.group(1))
            # Sanity check - draft years should be recent
            if 2020 <= year <= 2030:
                return year
        return None
    
    def _parse_draft_round(self, text: str) -> Optional[int]:
        """
        Extract draft round from text.
        
        Args:
            text: Text that may contain round information
            
        Returns:
            Round as integer or None
        """
        # Look for "Round X" or "Rd X" or just a number
        patterns = [
            r'round\s+(\d+)',
            r'rd\.?\s*(\d+)',
            r'^(\d+)(?:st|nd|rd|th)?\s+round',
            r'^round\s*(\d+)',
        ]
        
        text_lower = text.lower().strip()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # If text is just a number, might be the round
        if text.strip().isdigit():
            return int(text.strip())
        
        return None
    
    def _parse_draft_pick(self, text: str) -> Optional[int]:
        """
        Extract draft pick number from text.
        
        Args:
            text: Text that may contain pick number
            
        Returns:
            Pick number as integer or None
        """
        # Look for "Pick X" or "Overall X" or just a number
        patterns = [
            r'pick\s+#?\s*(\d+)',
            r'overall\s+#?\s*(\d+)',
            r'#(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s+pick',
            r'pick\s+(\d+)',
        ]
        
        text_lower = text.lower().strip()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # If text is just a number, might be the pick
        if text.strip().isdigit():
            return int(text.strip())
        
        return None
    
    def _extract_player_name(self, text: str) -> Optional[str]:
        """
        Extract player name from text.
        
        Args:
            text: Text that may contain a player name
            
        Returns:
            Player name or None
        """
        # Look for capitalized name patterns (First Last or First Middle Last)
        # Common patterns: "John Smith", "Mike P. Johnson", etc.
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)',  # First Last or First M. Last
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',  # First Middle Last
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Filter out common false positives
                if name not in ['Round', 'Pick', 'Overall', 'Team', 'School']:
                    return name
        
        return None
    
    def _extract_school(self, text: str) -> Optional[str]:
        """
        Extract school name from text.
        
        Args:
            text: Text that may contain a school name
            
        Returns:
            School name or None
        """
        # Look for school patterns
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:University|College|State|Tech|Tech\.|St\.?)))',
            r'\(([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:University|College|State|Tech|Tech\.|St\.?)))\)',
            r'from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:University|College|State|Tech|Tech\.|St\.?)))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                school = match.group(1).strip()
                return school
        
        return None
    
    def scrape_espn_draft(self) -> List[Dict]:
        """
        Scrape draft results from ESPN.
        Note: ESPN pages are JavaScript-rendered, so extraction may be limited.
        For better results, consider using a headless browser (Selenium/Playwright).
        
        Returns:
            List of dictionaries containing draft information for each player
        """
        # Try main draft results page first
        soup = self._make_request(ESPN_DRAFT_URL)
        
        # If main page fails, use story page
        if not soup:
            soup = self._make_request(ESPN_DRAFT_STORY_URL)
        
        if not soup:
            logger.error("Failed to fetch draft results from ESPN")
            return []
        
        draft_results = []
        
        # Try to find embedded JSON data first (ESPN often uses this)
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Look for draft data in JSON structure
                # This depends on ESPN's structure - may need adjustment
                if isinstance(data, dict):
                    # Recursively search for draft-related data
                    draft_data = self._extract_draft_from_json(data)
                    if draft_data:
                        draft_results.extend(draft_data)
            except:
                pass
        
        # If no JSON data found, parse HTML content
        if not draft_results:
            # Get all page text (ESPN pages may be JS-rendered, but try to get what's available)
            page_text = soup.get_text(separator='\n')
            draft_year = self._parse_draft_year(ESPN_DRAFT_URL) or self._parse_draft_year(page_text) or 2025
            
            # Look for structured patterns in the text
            # Pattern 1: "Round X, Pick Y: Player Name"
            pattern1 = re.compile(r'(?:Round|Rd\.?)\s*(\d+)[,\s]+(?:Pick|#)?\s*(\d+)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.I)
            matches1 = pattern1.findall(page_text)
            for match in matches1:
                round_num, pick_num, name = match
                # Look for school and team in surrounding text
                # This is a simplified extraction - may need refinement
                draft_result = {
                    'player_name': name.strip(),
                    'school': '',
                    'draft_year': draft_year,
                    'round': int(round_num),
                    'pick': int(pick_num),
                    'team': '',
                    'position': ''
                }
                draft_results.append(draft_result)
            
            # Pattern 2: "Pick X: Player Name"
            if not draft_results:
                pattern2 = re.compile(r'Pick\s*#?\s*(\d+)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.I)
                matches2 = pattern2.findall(page_text)
                for match in matches2:
                    pick_num, name = match
                    draft_result = {
                        'player_name': name.strip(),
                        'school': '',
                        'draft_year': draft_year,
                        'round': None,
                        'pick': int(pick_num),
                        'team': '',
                        'position': ''
                    }
                    draft_results.append(draft_result)
            
            # Pattern 3: Numbered list "1. Player Name"
            if not draft_results:
                pattern3 = re.compile(r'^(\d+)\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.MULTILINE)
                matches3 = pattern3.findall(page_text)
                for match in matches3[:50]:  # Limit to first 50 (likely first round)
                    pick_num, name = match
                    if int(pick_num) <= 50:  # Reasonable pick number
                        draft_result = {
                            'player_name': name.strip(),
                            'school': '',
                            'draft_year': draft_year,
                            'round': 1 if int(pick_num) <= 30 else None,
                            'pick': int(pick_num),
                            'team': '',
                            'position': ''
                        }
                        draft_results.append(draft_result)
            
            # Try to extract from article content if available
            article = soup.find('article')
            if not article:
                article = soup.find('div', class_=re.compile(r'article|content|story', re.I))
            
            if article and not draft_results:
                text_content = article.get_text(separator='\n')
                lines = text_content.split('\n')
                current_pick = None
                current_round = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for round information
                    round_match = re.search(r'(?:round|rd\.?)\s*(\d+)', line, re.I)
                    if round_match:
                        current_round = int(round_match.group(1))
                    
                    # Look for pick information
                    pick_match = self._parse_draft_pick(line)
                    if pick_match:
                        current_pick = pick_match
                    
                    # Look for player name
                    player_name = self._extract_player_name(line)
                    if player_name and current_pick:
                        # Look for school in the same line or nearby
                        school = self._extract_school(line)
                        
                        # Look for team
                        team_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:selects?|picks?|drafts?)', line, re.I)
                        team = team_match.group(1) if team_match else None
                        
                        # Look for position
                        position_match = re.search(r'\b(?:P|C|1B|2B|3B|SS|OF|LF|CF|RF|DH|RHP|LHP)\b', line, re.I)
                        position = position_match.group(0) if position_match else None
                        
                        draft_result = {
                            'player_name': player_name,
                            'school': school or '',
                            'draft_year': draft_year,
                            'round': current_round,
                            'pick': current_pick,
                            'team': team or '',
                            'position': position or ''
                        }
                        # Avoid duplicates
                        if not any(dr['player_name'] == player_name and dr.get('pick') == current_pick 
                                  for dr in draft_results):
                            draft_results.append(draft_result)
                            logger.debug(f"Found draft pick: {player_name} - {school} - Round {current_round}, Pick {current_pick}")
        
        # Also look for tables (ESPN sometimes uses tables)
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Try to identify column headers
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            name_idx = None
            school_idx = None
            round_idx = None
            pick_idx = None
            team_idx = None
            position_idx = None
            
            for i, header in enumerate(headers):
                if 'name' in header or 'player' in header:
                    name_idx = i
                elif 'school' in header or 'college' in header:
                    school_idx = i
                elif 'round' in header:
                    round_idx = i
                elif 'pick' in header:
                    pick_idx = i
                elif 'team' in header:
                    team_idx = i
                elif 'position' in header or 'pos' in header:
                    position_idx = i
            
            # Process data rows
            draft_year = self._parse_draft_year(ESPN_DRAFT_URL) or 2025
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                player_name = None
                school = None
                draft_round = None
                draft_pick = None
                team = None
                position = None
                
                if name_idx is not None and name_idx < len(cells):
                    player_name = cells[name_idx].get_text(strip=True)
                
                if school_idx is not None and school_idx < len(cells):
                    school = cells[school_idx].get_text(strip=True)
                
                if round_idx is not None and round_idx < len(cells):
                    round_text = cells[round_idx].get_text(strip=True)
                    draft_round = self._parse_draft_round(round_text)
                
                if pick_idx is not None and pick_idx < len(cells):
                    pick_text = cells[pick_idx].get_text(strip=True)
                    draft_pick = self._parse_draft_pick(pick_text)
                
                if team_idx is not None and team_idx < len(cells):
                    team = cells[team_idx].get_text(strip=True)
                
                if position_idx is not None and position_idx < len(cells):
                    position = cells[position_idx].get_text(strip=True)
                
                if player_name:
                    draft_result = {
                        'player_name': player_name,
                        'school': school or '',
                        'draft_year': draft_year,
                        'round': draft_round,
                        'pick': draft_pick,
                        'team': team or '',
                        'position': position or ''
                    }
                    # Avoid duplicates
                    if not any(dr['player_name'] == player_name and dr.get('pick') == draft_pick 
                              for dr in draft_results):
                        draft_results.append(draft_result)
        
        # If still no results and we have soup, try parsing text content
        if not draft_results and soup:
            page_text = soup.get_text(separator='\n')
            draft_year = self._parse_draft_year(ESPN_DRAFT_STORY_URL) or self._parse_draft_year(page_text) or 2025
            
            # Look for structured patterns in the text
            pattern1 = re.compile(r'(?:Round|Rd\.?)\s*(\d+)[,\s]+(?:Pick|#)?\s*(\d+)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.I)
            matches1 = pattern1.findall(page_text)
            for match in matches1:
                round_num, pick_num, name = match
                # Filter out team names (common MLB team names)
                team_names = ['Nationals', 'Angels', 'Mariners', 'Rockies', 'Pirates', 'Marlins', 
                             'Blue Jays', 'Reds', 'White Sox', 'Rangers', 'Dodgers', 'Yankees',
                             'Red Sox', 'Cubs', 'Giants', 'Cardinals', 'Astros', 'Braves']
                if not any(team in name for team in team_names):
                    draft_result = {
                        'player_name': name.strip(),
                        'school': '',
                        'draft_year': draft_year,
                        'round': int(round_num),
                        'pick': int(pick_num),
                        'team': '',
                        'position': ''
                    }
                    draft_results.append(draft_result)
        
        logger.info(f"Scraped {len(draft_results)} draft results from ESPN")
        return draft_results
    
    def _extract_draft_from_json(self, data: Dict, path: str = '') -> List[Dict]:
        """
        Recursively extract draft data from JSON structure.
        
        Args:
            data: JSON data structure
            path: Current path in JSON (for debugging)
            
        Returns:
            List of draft result dictionaries
        """
        results = []
        
        if isinstance(data, dict):
            # Look for draft-related keys
            if 'draft' in str(data.keys()).lower() or 'pick' in str(data.keys()).lower():
                # Try to extract draft information
                pass
            
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    results.extend(self._extract_draft_from_json(value, f"{path}.{key}"))
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    results.extend(self._extract_draft_from_json(item, path))
        
        return results
    
    def get_draft_results(self) -> List[Dict]:
        """
        Public method to get draft results from ESPN.
        
        Returns:
            List of draft result dictionaries
        """
        return self.scrape_espn_draft()

