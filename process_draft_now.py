#!/usr/bin/env python3
"""
Process the full draft text directly.
This script will accept the draft text and process it immediately.
"""
import sys
from parse_draft_text import import_draft_text_to_db
from database import Database
from config import DB_CONFIG

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
    print("=" * 70)
    print("PROCESSING FULL DRAFT TEXT (615 PICKS)")
    print("=" * 70)
    print("")
    
    # Read from file if provided, otherwise from stdin
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        print(f"Reading from file: {filename}")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)
    else:
        print("Reading from stdin...")
        print("(Paste the full draft text and press Ctrl+D when done)")
        print("")
        text = sys.stdin.read()
    
    if not text or len(text) < 100:
        print("Error: No text provided or text too short.")
        sys.exit(1)
    
    print(f"Text length: {len(text):,} characters")
    print("Processing...")
    print("")
    
    try:
        # Import and match
        import_draft_text_to_db(text)
        
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
        sys.exit(1)

