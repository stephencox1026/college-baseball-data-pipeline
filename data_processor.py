"""
Data processor for matching players and flagging drafted status.
Matches players between Baseball Reference and Baseball America by name and school.
"""
import logging
from typing import List, Dict, Optional
import re
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and matches player data between sources."""
    
    def __init__(self, db: Database):
        """
        Initialize data processor.
        
        Args:
            db: Database instance
        """
        self.db = db
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize player name for matching.
        Removes extra whitespace, converts to lowercase, handles common variations.
        
        Args:
            name: Player name
            
        Returns:
            Normalized name
        """
        if not name:
            return ""
        # Remove extra whitespace
        name = ' '.join(name.split())
        # Convert to lowercase
        name = name.lower()
        # Remove common suffixes (Jr., Sr., III, etc.)
        name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv|v)$', '', name)
        return name.strip()
    
    def _normalize_school(self, school: str) -> str:
        """
        Normalize school name for matching.
        Handles common variations and abbreviations.
        
        Args:
            school: School name
            
        Returns:
            Normalized school name
        """
        if not school:
            return ""
        
        school = school.strip()
        # Remove common suffixes in parentheses (abbreviations, etc.)
        school = re.sub(r'\s*\([^)]*\)', '', school)
        # Normalize whitespace
        school = ' '.join(school.split())
        # Convert to lowercase
        school = school.lower()
        # Handle common abbreviations
        school = school.replace('univ.', 'university')
        school = school.replace('univ', 'university')
        school = school.replace('u.', 'university')
        school = school.replace('st.', 'state')
        school = school.replace('st', 'state')
        # Remove common words that might differ
        school = school.replace('the ', '')
        return school.strip()
    
    def _fuzzy_match_name(self, name1: str, name2: str) -> bool:
        """
        Check if two names are a fuzzy match.
        Handles middle initial variations and common name differences.
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            True if names match closely
        """
        name1_norm = self._normalize_name(name1)
        name2_norm = self._normalize_name(name2)
        
        # Exact match after normalization
        if name1_norm == name2_norm:
            return True
        
        # Split into parts
        parts1 = name1_norm.split()
        parts2 = name2_norm.split()
        
        # Must have at least first and last name
        if len(parts1) < 2 or len(parts2) < 2:
            return False
        
        # Check if first and last names match
        if parts1[0] == parts2[0] and parts1[-1] == parts2[-1]:
            # Middle name/initial differences are okay
            return True
        
        # Check if one is a nickname variation
        # This is a simple check - could be enhanced
        if parts1[0][0] == parts2[0][0] and parts1[-1] == parts2[-1]:
            # Same first initial and same last name
            if len(parts1[0]) <= 2 or len(parts2[0]) <= 2:  # One might be an initial
                return True
        
        return False
    
    def _fuzzy_match_school(self, school1: str, school2: str) -> bool:
        """
        Check if two school names are a fuzzy match.
        Handles abbreviations and common variations.
        
        Args:
            school1: First school name
            school2: Second school name
            
        Returns:
            True if schools match closely
        """
        if not school1 or not school2:
            return False
            
        school1_norm = self._normalize_school(school1)
        school2_norm = self._normalize_school(school2)
        
        # Exact match after normalization
        if school1_norm == school2_norm:
            return True
        
        # Check if one contains the other (handles partial matches)
        if school1_norm in school2_norm or school2_norm in school1_norm:
            # Make sure it's not too short (avoid false positives)
            if len(school1_norm) >= 5 and len(school2_norm) >= 5:
                return True
        
        # Handle common abbreviations - check if abbreviation matches full name
        # Common abbreviations mapping
        abbrev_map = {
            'bay': 'baylor',
            'baylor': 'bay',
            'tenn': 'tennessee',
            'tennessee': 'tenn',
            'fsu': 'florida state',
            'florida state': 'fsu',
            'lsu': 'louisiana state',
            'louisiana state': 'lsu',
            'msu': 'mississippi state',
            'mississippi state': 'msu',
            'ucsb': 'uc santa barbara',
            'uc santa barbara': 'ucsb',
            'usc': 'southern california',
            'southern california': 'usc',
            'uoa': 'oklahoma',
            'oklahoma': 'uoa',
            'uaz': 'arizona',
            'arizona': 'uaz',
            'uga': 'georgia',
            'georgia': 'uga',
            'azu': 'arizona state',
            'arizona state': 'azu',
            'uks': 'kansas state',
            'kansas state': 'uks',
            'bam': 'alabama',
            'alabama': 'bam',
            'uclv': 'unlv',
            'unlv': 'uclv',
            'ucn': 'north carolina',
            'north carolina': 'ucn',
            'ulv': 'louisville',
            'louisville': 'ulv',
            'uwv': 'west virginia',
            'west virginia': 'uwv',
            'aub': 'auburn',
            'auburn': 'aub',
            'duk': 'duke',
            'duke': 'duk',
            'ksu': 'kansas state',
            'kansas state': 'ksu',
        }
        
        # Check if either school is an abbreviation of the other
        school1_lower = school1_norm.lower()
        school2_lower = school2_norm.lower()
        
        # Direct abbreviation check
        if school1_lower in abbrev_map and abbrev_map[school1_lower] == school2_lower:
            return True
        if school2_lower in abbrev_map and abbrev_map[school2_lower] == school1_lower:
            return True
        
        # Check if one starts with the other (handles "Baylor" vs "Baylor University")
        if school1_lower.startswith(school2_lower) or school2_lower.startswith(school1_lower):
            if len(school1_lower) >= 3 and len(school2_lower) >= 3:
                return True
        
        return False
    
    def match_players_to_draft_results(self) -> Dict:
        """
        Match players in database to draft results and update draft status.
        
        Returns:
            Dictionary with matching statistics
        """
        logger.info("Starting player matching process...")
        
        # Get all draft results
        self.db.cursor.execute("""
            SELECT id, player_name, school, draft_year, round, pick, team, position
            FROM draft_results
        """)
        draft_results = self.db.cursor.fetchall()
        
        logger.info(f"Found {len(draft_results)} draft results to match")
        
        matches_found = 0
        matches_updated = 0
        no_matches = 0
        
        for draft_id, player_name, school, draft_year, round_num, pick, team, position in draft_results:
            if not player_name:
                continue
            
            match_type = 'name_only'
            player_ids = []
            
            # Simplified strategy: Match by name only
            # Find all players with matching names
            self.db.cursor.execute("""
                SELECT id, name FROM players
                WHERE LOWER(name) LIKE LOWER(%s)
            """, (f'%{player_name}%',))
            candidates = self.db.cursor.fetchall()
            
            matched_players = []
            for player_id, db_name in candidates:
                name_match = self._fuzzy_match_name(player_name, db_name)
                if name_match:
                    matched_players.append(player_id)
                    logger.debug(f"Match (name only): '{player_name}' -> '{db_name}'")
            
            if matched_players:
                player_ids = matched_players
            
            if player_ids:
                matches_found += 1
                # Update all matching players (in case of duplicates)
                for player_id in player_ids:
                    try:
                        self.db.update_player_draft_status(
                            player_id, draft_year, round_num, pick, team, position, match_type
                        )
                        matches_updated += 1
                        logger.debug(f"Updated player {player_id} with draft info: {player_name} (match: {match_type})")
                    except Exception as e:
                        logger.error(f"Error updating player {player_id}: {e}")
            else:
                no_matches += 1
                logger.debug(f"No match found for: {player_name} ({school})")
        
        # Get match type statistics
        self.db.cursor.execute("""
            SELECT draft_match_type, COUNT(*) 
            FROM players 
            WHERE drafted = TRUE 
            GROUP BY draft_match_type
        """)
        match_type_stats = dict(self.db.cursor.fetchall())
        
        stats = {
            'total_draft_results': len(draft_results),
            'matches_found': matches_found,
            'players_updated': matches_updated,
            'no_matches': no_matches,
            'match_type_breakdown': {
                'name_only': match_type_stats.get('name_only', 0),
                'name_and_school': match_type_stats.get('name_and_school', 0),
                'name_and_draft_team': match_type_stats.get('name_and_draft_team', 0)
            },
            'no_matches': no_matches
        }
        
        logger.info(f"Matching complete: {stats}")
        return stats
    
    def get_unmatched_draft_results(self) -> List[Dict]:
        """
        Get draft results that couldn't be matched to players.
        
        Returns:
            List of unmatched draft result dictionaries
        """
        self.db.cursor.execute("""
            SELECT player_name, school, draft_year, round, pick, team, position
            FROM draft_results
            WHERE NOT EXISTS (
                SELECT 1 FROM players
                WHERE LOWER(players.name) = LOWER(draft_results.player_name)
                AND LOWER(COALESCE(players.school, '')) = LOWER(COALESCE(draft_results.school, ''))
            )
        """)
        
        unmatched = []
        for row in self.db.cursor.fetchall():
            unmatched.append({
                'player_name': row[0],
                'school': row[1],
                'draft_year': row[2],
                'round': row[3],
                'pick': row[4],
                'team': row[5],
                'position': row[6]
            })
        
        return unmatched
    
    def get_draft_statistics(self) -> Dict:
        """
        Get statistics about drafted players.
        
        Returns:
            Dictionary with draft statistics
        """
        # Total drafted players
        self.db.cursor.execute("SELECT COUNT(*) FROM players WHERE drafted = TRUE")
        total_drafted = self.db.cursor.fetchone()[0]
        
        # Drafted by year
        self.db.cursor.execute("""
            SELECT draft_year, COUNT(*) 
            FROM players 
            WHERE drafted = TRUE AND draft_year IS NOT NULL
            GROUP BY draft_year
            ORDER BY draft_year DESC
        """)
        by_year = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        
        # Drafted by round
        self.db.cursor.execute("""
            SELECT draft_round, COUNT(*) 
            FROM players 
            WHERE drafted = TRUE AND draft_round IS NOT NULL
            GROUP BY draft_round
            ORDER BY draft_round
        """)
        by_round = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        
        # Drafted by team
        self.db.cursor.execute("""
            SELECT draft_team, COUNT(*) 
            FROM players 
            WHERE drafted = TRUE AND draft_team IS NOT NULL
            GROUP BY draft_team
            ORDER BY COUNT(*) DESC
        """)
        by_team = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        
        return {
            'total_drafted': total_drafted,
            'by_year': by_year,
            'by_round': by_round,
            'by_team': by_team
        }

