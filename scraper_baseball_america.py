"""
Scraper for Baseball America draft results.
Extracts player names, schools, and draft information.
"""
import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Dict, List, Optional
import re
from config import BASEBALL_AMERICA_DRAFT_URL, REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseballAmericaScraper:
    """Scrapes draft results from Baseball America."""
    
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
            return int(match.group(1))
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
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player name for matching.
        
        Args:
            name: Player name
            
        Returns:
            Normalized name
        """
        if not name:
            return ""
        # Remove extra whitespace, convert to lowercase
        return ' '.join(name.split()).lower()
    
    def _normalize_school(self, school: str) -> str:
        """
        Normalize school name for matching.
        
        Args:
            school: School name
            
        Returns:
            Normalized school name
        """
        if not school:
            return ""
        # Remove common suffixes and normalize
        school = school.strip()
        # Remove common abbreviations in parentheses
        school = re.sub(r'\s*\([^)]*\)', '', school)
        # Normalize whitespace
        return ' '.join(school.split()).lower()
    
    def scrape_draft_results(self) -> List[Dict]:
        """
        Scrape draft results from Baseball America.
        
        Returns:
            List of dictionaries containing draft information for each player
        """
        soup = self._make_request(BASEBALL_AMERICA_DRAFT_URL)
        
        if not soup:
            logger.error("Failed to fetch draft results from Baseball America")
            return []
        
        draft_results = []
        
        # Baseball America draft results page structure can vary
        # Try multiple approaches to find the draft data
        
        # Approach 1: Look for tables with draft data
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Need at least header + data
                continue
            
            # Try to identify if this is a draft table
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
            
            # Look for draft-related headers
            draft_keywords = ['player', 'name', 'school', 'round', 'pick', 'team', 'position', 'year']
            if not any(keyword in ' '.join(headers) for keyword in draft_keywords):
                continue
            
            # Map header indices
            name_idx = None
            school_idx = None
            round_idx = None
            pick_idx = None
            team_idx = None
            position_idx = None
            year_idx = None
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'name' in header_lower or 'player' in header_lower:
                    name_idx = i
                elif 'school' in header_lower or 'college' in header_lower or 'university' in header_lower:
                    school_idx = i
                elif 'round' in header_lower:
                    round_idx = i
                elif 'pick' in header_lower or 'overall' in header_lower:
                    pick_idx = i
                elif 'team' in header_lower:
                    team_idx = i
                elif 'position' in header_lower or 'pos' in header_lower:
                    position_idx = i
                elif 'year' in header_lower:
                    year_idx = i
            
            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # Extract data based on column indices
                player_name = None
                school = None
                draft_year = None
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
                
                if year_idx is not None and year_idx < len(cells):
                    year_text = cells[year_idx].get_text(strip=True)
                    draft_year = self._parse_draft_year(year_text)
                
                # If we don't have a year, try to extract from page title or URL
                if not draft_year:
                    page_title = soup.find('title')
                    if page_title:
                        draft_year = self._parse_draft_year(page_title.get_text())
                
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
                    draft_results.append(draft_result)
        
        # Approach 2: Look for structured data in divs or lists
        if not draft_results:
            # Try to find draft entries in other formats
            draft_sections = soup.find_all(['div', 'section'], class_=re.compile(r'draft|result|player', re.I))
            for section in draft_sections:
                # Look for player information
                player_elements = section.find_all(['div', 'li', 'p'], class_=re.compile(r'player|draft', re.I))
                for element in player_elements:
                    text = element.get_text(separator=' ', strip=True)
                    # Try to extract player name (usually first part)
                    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
                    if name_match:
                        player_name = name_match.group(1)
                        # Try to extract other info
                        school_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+University|College|State))', text)
                        school = school_match.group(1) if school_match else None
                        
                        draft_year = self._parse_draft_year(text)
                        draft_round = self._parse_draft_round(text)
                        draft_pick = self._parse_draft_pick(text)
                        
                        draft_result = {
                            'player_name': player_name,
                            'school': school or '',
                            'draft_year': draft_year,
                            'round': draft_round,
                            'pick': draft_pick,
                            'team': '',
                            'position': ''
                        }
                        draft_results.append(draft_result)
        
        # Approach 3: Look for JSON-LD or script tags with structured data
        if not draft_results:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    # Process structured data if found
                    # This would depend on Baseball America's specific structure
                except:
                    pass
        
        logger.info(f"Scraped {len(draft_results)} draft results from Baseball America")
        return draft_results
    
    def get_draft_results(self) -> List[Dict]:
        """
        Public method to get draft results.
        
        Returns:
            List of draft result dictionaries
        """
        return self.scrape_draft_results()

