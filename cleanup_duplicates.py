"""
Script to clean up duplicate players in the database.
Merges duplicate player records, keeping the one with the most complete data.
"""
from database import Database
from config import DB_CONFIG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def merge_duplicate_players():
    """Find and merge duplicate players."""
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        # Find duplicates by name (regardless of school/conference)
        db.cursor.execute("""
            SELECT name, COUNT(*) as count
            FROM players
            GROUP BY name
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        duplicates = db.cursor.fetchall()
        
        logger.info(f"Found {len(duplicates)} players with duplicate records")
        
        merged_count = 0
        deleted_count = 0
        
        for name, count in duplicates:
            # Get all records for this name
            db.cursor.execute("""
                SELECT id, name, school, conference_id, position, drafted, 
                       draft_year, draft_round, draft_pick, draft_team, draft_match_type,
                       age
                FROM players
                WHERE name = %s
                ORDER BY 
                    -- Prefer records with school
                    CASE WHEN school IS NOT NULL AND school != '' THEN 0 ELSE 1 END,
                    -- Prefer records with age
                    CASE WHEN age IS NOT NULL THEN 0 ELSE 1 END,
                    -- Prefer drafted records
                    CASE WHEN drafted = TRUE THEN 0 ELSE 1 END,
                    -- Prefer records with position
                    CASE WHEN position IS NOT NULL AND position != '' THEN 0 ELSE 1 END,
                    id ASC
            """, (name,))
            records = db.cursor.fetchall()
            
            if len(records) <= 1:
                continue
            
            # Keep the first (best) record, merge others into it
            keep_id = records[0][0]
            keep_record = records[0]
            
            logger.info(f"\nMerging {count} records for '{name}':")
            logger.info(f"  Keeping ID {keep_id} (school: {keep_record[2]}, drafted: {keep_record[5]})")
            
            for record in records[1:]:
                duplicate_id = record[0]
                logger.info(f"  Merging ID {duplicate_id} into {keep_id}")
                
                # Merge data: update keep record with data from duplicate if keep is missing it
                updates = []
                params = []
                
                if not keep_record[2] and record[2]:  # school
                    updates.append("school = %s")
                    params.append(record[2])
                
                if not keep_record[4] and record[4]:  # position
                    updates.append("position = %s")
                    params.append(record[4])
                
                if not keep_record[5] and record[5]:  # drafted
                    updates.append("drafted = %s")
                    params.append(record[5])
                
                if not keep_record[6] and record[6]:  # draft_year
                    updates.append("draft_year = %s")
                    params.append(record[6])
                
                if not keep_record[7] and record[7]:  # draft_round
                    updates.append("draft_round = %s")
                    params.append(record[7])
                
                if not keep_record[8] and record[8]:  # draft_pick
                    updates.append("draft_pick = %s")
                    params.append(record[8])
                
                if not keep_record[9] and record[9]:  # draft_team
                    updates.append("draft_team = %s")
                    params.append(record[9])
                
                if not keep_record[10] and record[10]:  # draft_match_type
                    updates.append("draft_match_type = %s")
                    params.append(record[10])
                
                if not keep_record[11] and record[11]:  # age
                    updates.append("age = %s")
                    params.append(record[11])
                
                # Update keep record if there are any fields to merge
                if updates:
                    update_sql = f"UPDATE players SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                    params.append(keep_id)
                    db.cursor.execute(update_sql, params)
                    logger.info(f"    Merged {len(updates)} fields into keep record")
                
                # Update all foreign key references from duplicate to keep record
                # Update hitting_stats - only move if season doesn't already exist for keep_id
                db.cursor.execute("""
                    UPDATE hitting_stats
                    SET player_id = %s
                    WHERE player_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM hitting_stats h2
                        WHERE h2.player_id = %s 
                        AND h2.season = hitting_stats.season
                    )
                """, (keep_id, duplicate_id, keep_id))
                hitting_moved = db.cursor.rowcount
                
                # Delete hitting stats that couldn't be moved (duplicate seasons)
                db.cursor.execute("""
                    DELETE FROM hitting_stats
                    WHERE player_id = %s
                    AND EXISTS (
                        SELECT 1 FROM hitting_stats h2
                        WHERE h2.player_id = %s 
                        AND h2.season = hitting_stats.season
                    )
                """, (duplicate_id, keep_id))
                hitting_deleted = db.cursor.rowcount
                
                # Update pitching_stats - only move if season doesn't already exist for keep_id
                db.cursor.execute("""
                    UPDATE pitching_stats
                    SET player_id = %s
                    WHERE player_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM pitching_stats p2
                        WHERE p2.player_id = %s 
                        AND p2.season = pitching_stats.season
                    )
                """, (keep_id, duplicate_id, keep_id))
                pitching_moved = db.cursor.rowcount
                
                # Delete pitching stats that couldn't be moved (duplicate seasons)
                db.cursor.execute("""
                    DELETE FROM pitching_stats
                    WHERE player_id = %s
                    AND EXISTS (
                        SELECT 1 FROM pitching_stats p2
                        WHERE p2.player_id = %s 
                        AND p2.season = pitching_stats.season
                    )
                """, (duplicate_id, keep_id))
                pitching_deleted = db.cursor.rowcount
                
                logger.info(f"    Moved {hitting_moved} hitting stats ({hitting_deleted} duplicates deleted), {pitching_moved} pitching stats ({pitching_deleted} duplicates deleted)")
                
                # Delete the duplicate record
                db.cursor.execute("DELETE FROM players WHERE id = %s", (duplicate_id,))
                deleted_count += 1
                merged_count += 1
            
            db.conn.commit()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Merge complete!")
        logger.info(f"  Players processed: {len(duplicates)}")
        logger.info(f"  Duplicate records merged: {merged_count}")
        logger.info(f"  Duplicate records deleted: {deleted_count}")
        logger.info(f"{'='*70}")
        
    except Exception as e:
        logger.error(f"Error merging duplicates: {e}")
        db.conn.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    merge_duplicate_players()
