#!/usr/bin/env python3
"""
Import draft data from Google Sheets and process it.
"""
import requests
import csv
import io
import re
import logging
from database import Database
from data_processor import DataProcessor
from config import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_google_sheets_data(sheet_id, gid='0'):
    """
    Download data from Google Sheets as CSV.
    
    Args:
        sheet_id: Google Sheets document ID
        gid: Sheet tab ID (default '0' for first sheet)
        
    Returns:
        List of dictionaries with draft data
    """
    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
    
    logger.info(f"Downloading data from Google Sheets: {sheet_id}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV
        csv_data = response.text
        reader = csv.DictReader(io.StringIO(csv_data))
        
        draft_results = []
        for row in reader:
            if not row.get('Player') or not row.get('Round'):
                continue
            
            # Parse round (handle special rounds like '1C', 'CB-A', etc.)
            round_str = str(row['Round']).strip()
            round_num = None
            if round_str.isdigit():
                round_num = int(round_str)
            else:
                # Extract first number
                match = re.search(r'^(\d+)', round_str)
                if match:
                    round_num = int(match.group(1))
            
            # Get pick number
            pick_str = str(row.get('Pick', '')).strip()
            pick_num = None
            if pick_str.isdigit():
                pick_num = int(pick_str)
            
            if not pick_num:
                continue
            
            draft_result = {
                'player_name': row['Player'].strip(),
                'school': row.get('School', '').strip(),
                'draft_year': 2025,
                'round': round_num,
                'pick': pick_num,
                'team': row.get('MLB Team', '').strip(),
                'position': row.get('Position', '').strip()
            }
            
            if draft_result['player_name']:
                draft_results.append(draft_result)
        
        logger.info(f"Downloaded {len(draft_results)} draft picks from Google Sheets")
        return draft_results
        
    except Exception as e:
        logger.error(f"Error downloading from Google Sheets: {e}")
        raise

def import_draft_from_sheets(sheet_id, gid='0'):
    """
    Import draft data from Google Sheets and process it.
    
    Args:
        sheet_id: Google Sheets document ID
        gid: Sheet tab ID
    """
    # Download data
    draft_results = download_google_sheets_data(sheet_id, gid)
    
    if not draft_results:
        logger.error("No draft results found in Google Sheets")
        return
    
    # Connect to database
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        # Clear existing draft results
        db.cursor.execute('DELETE FROM draft_results')
        db.cursor.execute('UPDATE players SET drafted = FALSE, draft_match_type = NULL, draft_year = NULL, draft_round = NULL, draft_pick = NULL, draft_team = NULL')
        logger.info("Cleared existing draft results")
        
        # Insert new draft results
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
        
        # Match players
        logger.info("Matching players to draft results...")
        processor = DataProcessor(db)
        match_stats = processor.match_players_to_draft_results()
        
        logger.info(f"Matching complete: {match_stats}")
        
        return match_stats
        
    finally:
        db.close()

def get_match_statistics():
    """Get detailed match statistics."""
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        # Get total draft results
        db.cursor.execute('SELECT COUNT(*) FROM draft_results')
        total_draft = db.cursor.fetchone()[0]
        
        # Get match type breakdown
        db.cursor.execute("""
            SELECT 
                draft_match_type,
                COUNT(*) as count
            FROM players 
            WHERE drafted = TRUE 
            GROUP BY draft_match_type
            ORDER BY count DESC
        """)
        match_types = dict(db.cursor.fetchall())
        
        # Get total drafted players
        db.cursor.execute('SELECT COUNT(*) FROM players WHERE drafted = TRUE')
        total_drafted = db.cursor.fetchone()[0]
        
        # Get unmatched draft results
        db.cursor.execute("""
            SELECT COUNT(*) 
            FROM draft_results dr
            WHERE NOT EXISTS (
                SELECT 1 FROM players p 
                WHERE p.drafted = TRUE 
                AND (p.name = dr.player_name OR LOWER(p.name) LIKE LOWER('%' || dr.player_name || '%'))
            )
        """)
        unmatched = db.cursor.fetchone()[0]
        
        return {
            'total_draft_results': total_draft,
            'total_drafted_players': total_drafted,
            'unmatched': unmatched,
            'match_types': match_types
        }
    finally:
        db.close()

if __name__ == "__main__":
    sheet_id = '1bktfWBtoS5bU_8nHXbb9fKUtqxYzKam98NNzjeNthEg'
    gid = '0'
    
    print("=" * 70)
    print("IMPORTING DRAFT DATA FROM GOOGLE SHEETS")
    print("=" * 70)
    print("")
    
    try:
        # Import and match
        match_stats = import_draft_from_sheets(sheet_id, gid)
        
        print("")
        print("=" * 70)
        print("MATCH STATISTICS")
        print("=" * 70)
        print("")
        
        # Get statistics
        stats = get_match_statistics()
        
        print(f"Total Draft Results: {stats['total_draft_results']}")
        print(f"Total Players Matched: {stats['total_drafted_players']}")
        print(f"Unmatched Draft Results: {stats['unmatched']}")
        print("")
        print("Match Type Breakdown:")
        print("-" * 70)
        
        match_types = stats['match_types']
        # Handle both old and new naming
        name_only = match_types.get('name_only', 0)
        name_and_school = match_types.get('name_and_school', 0) or match_types.get('name_and_team', 0)
        name_and_draft_team = match_types.get('name_and_draft_team', 0)
        
        print(f"1. Name Only:                    {name_only:4d}")
        print(f"2. Name + School (College Team): {name_and_school:4d}")
        print(f"3. Name + MLB Drafting Team:     {name_and_draft_team:4d}")
        print("")
        total_matched = name_only + name_and_school + name_and_draft_team
        print(f"Total Matched:                   {total_matched:4d}")
        if stats['total_drafted_players'] != total_matched:
            other = stats['total_drafted_players'] - total_matched
            print(f"  (Note: {other} players with unknown/other match type)")
        print("")
        print("=" * 70)
        print("PROCESSING COMPLETE!")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

