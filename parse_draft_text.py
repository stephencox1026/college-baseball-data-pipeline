"""
Parser for Baseball America draft results from copied text.
Parses the structured draft order text format.
"""
import re
import logging
from typing import List, Dict
from database import Database
from config import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_draft_text(text: str) -> List[Dict]:
    """
    Parse draft results from copied Baseball America text.
    
    Format example (multi-line):
    2025	1	1	Washington NationalsTeam Logo of Washington Nationals	
    Headshot of Eli Willits
    Eli Willits
    	SS	Fort Cobb-Broxton HS	HS	OK	Y	$8,200,000
    
    Args:
        text: Copied draft text
        
    Returns:
        List of draft result dictionaries
    """
    draft_results = []
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # Skip header lines and navigation
        if any(skip in line.lower() for skip in ['cookieyes', 'skip to content', 'newsletter', 
                                                  'subscribe', 'quick hits', 'categories', 
                                                  'competition levels', 'follow us', 'copyright',
                                                  'download our app', 'stay connected']):
            i += 1
            continue
        
        # Check if this line starts with a year (first line of a draft entry)
        if not re.match(r'^\d{4}\s+', line):
            i += 1
            continue
        
        # Parse the first line: Year, Round, Pick, Team
        parts = line.split('\t')
        if len(parts) < 4:
            i += 1
            continue
        
        try:
            year = int(parts[0].strip()) if parts[0].strip().isdigit() else None
            round_str = parts[1].strip()
            pick = int(parts[2].strip()) if parts[2].strip().isdigit() else None
            
            # Extract team name (remove "Team Logo of..." part)
            team_raw = parts[3].strip()
            team = re.sub(r'Team Logo of.*$', '', team_raw).strip()
            
            # Get player name - check next 2 lines for "Headshot of" or name
            player_name = None
            name_line_idx = i
            
            # Check if "Headshot of" is on current line
            if 'Headshot of' in line:
                player_name = re.sub(r'^.*Headshot of\s+', '', line).strip()
                name_line_idx = i
            # Check next line
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if 'Headshot of' in next_line:
                    player_name = re.sub(r'^.*Headshot of\s+', '', next_line).strip()
                    name_line_idx = i + 1
                # Or next line might be just the name
                elif next_line and not next_line.startswith('\t') and len(next_line.split('\t')) == 1:
                    player_name = next_line.strip()
                    name_line_idx = i + 1
            
            # If still no name, try parts after team
            if not player_name:
                for part in parts[4:]:
                    part = part.strip()
                    if part and 'Headshot' not in part and len(part) > 2:
                        player_name = part
                        break
            
            if not player_name:
                i += 1
                continue
            
            # Now find position and school - look at line after name (usually starts with tab)
            position = ''
            school = ''
            data_line_idx = name_line_idx + 1
            
            # Look for the data line (starts with tab, has position/school)
            for check_idx in range(data_line_idx, min(len(lines), data_line_idx + 2)):
                check_line = lines[check_idx]
                if check_line.startswith('\t') or '\t' in check_line:
                    data_parts = [p.strip() for p in check_line.split('\t')]
                    # Remove empty parts at start
                    data_parts = [p for p in data_parts if p]
                    
                    # Position is usually first non-empty part (short code)
                    if len(data_parts) > 0:
                        pos_candidate = data_parts[0]
                        if len(pos_candidate) <= 5 and re.match(r'^[A-Z0-9/]+$', pos_candidate) and pos_candidate not in ['HS', '4YR', 'JC', 'N/A', 'CAN']:
                            position = pos_candidate
                            
                            # School is next, before type (HS/4YR/JC)
                            if len(data_parts) > 1:
                                school_candidate = data_parts[1]
                                if school_candidate not in ['HS', '4YR', 'JC', 'N/A', 'CAN'] and len(school_candidate) > 2:
                                    school = school_candidate
                    
                    if position:
                        break
            
            # Parse round number
            round_num = None
            match = re.search(r'^(\d+)', round_str)
            if match:
                round_num = int(match.group(1))
            elif round_str.isdigit():
                round_num = int(round_str)
            
            if year and pick and player_name and team:
                draft_result = {
                    'player_name': player_name,
                    'school': school,
                    'draft_year': year,
                    'round': round_num,
                    'pick': pick,
                    'team': team,
                    'position': position
                }
                draft_results.append(draft_result)
                
        except (ValueError, IndexError) as e:
            logger.debug(f"Error parsing line {i}: {line[:100]} - {e}")
        
        i += 1
    
    logger.info(f"Parsed {len(draft_results)} draft results from text")
    return draft_results


def import_draft_text_to_db(text: str):
    """
    Parse draft text and import into database.
    
    Args:
        text: Copied draft text from Baseball America
    """
    draft_results = parse_draft_text(text)
    
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        # Clear existing draft results
        db.cursor.execute('DELETE FROM draft_results')
        db.cursor.execute('UPDATE players SET drafted = FALSE, draft_match_type = NULL, draft_year = NULL, draft_round = NULL, draft_pick = NULL, draft_team = NULL')
        logger.info("Cleared existing draft results")
        
        imported = 0
        for result in draft_results:
            try:
                db.insert_draft_result(
                    player_name=result['player_name'],
                    school=result['school'],
                    draft_year=result['draft_year'],
                    round_num=result['round'],
                    pick=result['pick'],
                    team=result['team'],
                    position=result['position']
                )
                imported += 1
            except Exception as e:
                logger.error(f"Error inserting draft result for {result['player_name']}: {e}")
        
        logger.info(f"Imported {imported} draft results to database")
        
        # Now match players
        from data_processor import DataProcessor
        processor = DataProcessor(db)
        match_stats = processor.match_players_to_draft_results()
        
        logger.info(f"Matching complete: {match_stats}")
        
    finally:
        db.close()


if __name__ == "__main__":
    # Read from file or stdin
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        print("Paste draft text (end with Ctrl+D or empty line):")
        text = sys.stdin.read()
    
    import_draft_text_to_db(text)
