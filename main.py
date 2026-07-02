"""
Main script to orchestrate college baseball data collection.
Scrapes data from Baseball Reference and Baseball America, stores in PostgreSQL,
and flags drafted players.
"""
import logging
import sys
from database import Database
from config import DB_CONFIG, CONFERENCES
from scraper_baseball_reference import BaseballReferenceScraper
from scraper_draft import DraftScraper
from data_processor import DataProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    logger.info("Starting college baseball data collection...")
    
    # Initialize database
    logger.info("Initializing database connection...")
    db = Database(DB_CONFIG)
    
    try:
        # Create database if it doesn't exist
        db.create_database(DB_CONFIG['database'])
        
        # Connect to database
        db.connect()
        
        # Create schema
        logger.info("Creating database schema...")
        db.create_schema()
        
        # Insert conferences
        logger.info("Setting up conferences...")
        conference_ids = {}
        for conf_key, conf_data in CONFERENCES.items():
            conf_id = db.insert_conference(conf_data['name'], conf_data['reference_id'])
            conference_ids[conf_data['reference_id']] = conf_id
            logger.info(f"Added conference: {conf_data['name']} (ID: {conf_id})")
        
        # Scrape Baseball Reference data
        logger.info("Starting Baseball Reference scraping...")
        br_scraper = BaseballReferenceScraper()
        
        for conf_key, conf_data in CONFERENCES.items():
            conf_ref_id = conf_data['reference_id']
            conf_db_id = conference_ids[conf_ref_id]
            
            logger.info(f"Scraping conference: {conf_data['name']} ({conf_ref_id})")
            
            # Scrape hitting and pitching stats
            stats = br_scraper.scrape_conference(conf_ref_id)
            
            # Process hitting stats
            logger.info(f"Processing {len(stats['hitting'])} hitting stat records...")
            for hitting_stat in stats['hitting']:
                try:
                    player_id = db.get_or_create_player(
                        name=hitting_stat.get('name'),
                        school=hitting_stat.get('school'),
                        conference_id=conf_db_id,
                        position=None,  # Position might be in stats, but not always available
                        age=hitting_stat.get('age')
                    )
                    
                    if player_id:
                        # Prepare stats dictionary (remove non-stat fields)
                        stats_dict = {k: v for k, v in hitting_stat.items() 
                                    if k not in ['name', 'school', 'season', 'age', 'team']}
                        
                        db.insert_hitting_stats(
                            player_id=player_id,
                            season=hitting_stat.get('season'),
                            stats_dict=stats_dict
                        )
                except Exception as e:
                    logger.error(f"Error processing hitting stat: {e}")
                    continue
            
            # Process pitching stats
            logger.info(f"Processing {len(stats['pitching'])} pitching stat records...")
            for pitching_stat in stats['pitching']:
                try:
                    player_id = db.get_or_create_player(
                        name=pitching_stat.get('name'),
                        school=pitching_stat.get('school'),
                        conference_id=conf_db_id,
                        position=None,
                        age=pitching_stat.get('age')
                    )
                    
                    if player_id:
                        # Prepare stats dictionary (remove non-stat fields)
                        stats_dict = {k: v for k, v in pitching_stat.items() 
                                    if k not in ['name', 'school', 'season', 'age', 'team']}
                        
                        db.insert_pitching_stats(
                            player_id=player_id,
                            season=pitching_stat.get('season'),
                            stats_dict=stats_dict
                        )
                except Exception as e:
                    logger.error(f"Error processing pitching stat: {e}")
                    continue
        
        # Scrape draft results from ESPN
        logger.info("Starting draft results scraping from ESPN...")
        draft_scraper = DraftScraper()
        draft_results = draft_scraper.get_draft_results()
        
        logger.info(f"Processing {len(draft_results)} draft results...")
        for draft_result in draft_results:
            try:
                db.insert_draft_result(
                    player_name=draft_result.get('player_name'),
                    school=draft_result.get('school'),
                    draft_year=draft_result.get('draft_year'),
                    round_num=draft_result.get('round'),
                    pick=draft_result.get('pick'),
                    team=draft_result.get('team'),
                    position=draft_result.get('position')
                )
            except Exception as e:
                logger.error(f"Error inserting draft result: {e}")
                continue
        
        # Match players to draft results
        logger.info("Matching players to draft results...")
        processor = DataProcessor(db)
        match_stats = processor.match_players_to_draft_results()
        
        logger.info("=" * 60)
        logger.info("Data collection complete!")
        logger.info("=" * 60)
        logger.info(f"Total draft results processed: {match_stats['total_draft_results']}")
        logger.info(f"Matches found: {match_stats['matches_found']}")
        logger.info(f"Players updated: {match_stats['players_updated']}")
        logger.info(f"No matches: {match_stats['no_matches']}")
        
        # Get draft statistics
        draft_stats = processor.get_draft_statistics()
        logger.info(f"\nDraft Statistics:")
        logger.info(f"Total drafted players: {draft_stats['total_drafted']}")
        if draft_stats['by_year']:
            logger.info(f"Drafted by year: {draft_stats['by_year']}")
        
        # Show unmatched draft results
        unmatched = processor.get_unmatched_draft_results()
        if unmatched:
            logger.warning(f"\n{len(unmatched)} draft results could not be matched to players:")
            for result in unmatched[:10]:  # Show first 10
                logger.warning(f"  - {result['player_name']} ({result['school']})")
            if len(unmatched) > 10:
                logger.warning(f"  ... and {len(unmatched) - 10} more")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()

