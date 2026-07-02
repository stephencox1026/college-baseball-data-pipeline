"""
PostgreSQL database connection and schema setup for college baseball data.
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Handles PostgreSQL database connection and schema operations."""
    
    def __init__(self, db_config):
        """
        Initialize database connection.
        
        Args:
            db_config: Dictionary with database connection parameters
        """
        self.config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.conn.cursor()
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def create_database(self, db_name):
        """
        Create database if it doesn't exist.
        
        Args:
            db_name: Name of the database to create
        """
        try:
            # Connect to default postgres database to create new database
            temp_conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database='postgres',
                user=self.config['user'],
                password=self.config['password']
            )
            temp_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            temp_cursor = temp_conn.cursor()
            
            # Check if database exists
            temp_cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            exists = temp_cursor.fetchone()
            
            if not exists:
                temp_cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                ))
                logger.info(f"Created database: {db_name}")
            else:
                logger.info(f"Database {db_name} already exists")
            
            temp_cursor.close()
            temp_conn.close()
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def create_schema(self):
        """Create all necessary tables for the college baseball data."""
        try:
            # Create conferences table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conferences (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    reference_id VARCHAR(50) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create players table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    school VARCHAR(200),
                    conference_id INTEGER REFERENCES conferences(id),
                    position VARCHAR(50),
                    age INTEGER,
                    year_started INTEGER,
                    years_played INTEGER,
                    years_enrolled INTEGER,
                    drafted BOOLEAN DEFAULT FALSE,
                    draft_year INTEGER,
                    draft_round INTEGER,
                    draft_pick INTEGER,
                    draft_team VARCHAR(100),
                    draft_match_type VARCHAR(20),  -- 'name_only' or 'name_and_team'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, school, conference_id)
                )
            """)
            
            # Create hitting_stats table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS hitting_stats (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    season INTEGER,
                    games INTEGER,
                    at_bats INTEGER,
                    runs INTEGER,
                    hits INTEGER,
                    doubles INTEGER,
                    triples INTEGER,
                    home_runs INTEGER,
                    rbi INTEGER,
                    walks INTEGER,
                    strikeouts INTEGER,
                    avg NUMERIC(5, 3),
                    obp NUMERIC(5, 3),
                    slg NUMERIC(5, 3),
                    ops NUMERIC(5, 3),
                    stolen_bases INTEGER,
                    caught_stealing INTEGER,
                    hit_by_pitch INTEGER,
                    sacrifice_flys INTEGER,
                    sacrifice_hits INTEGER,
                    intentional_walks INTEGER,
                    ground_into_double_play INTEGER,
                    plate_appearances INTEGER,
                    total_bases INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_id, season)
                )
            """)
            
            # Create pitching_stats table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pitching_stats (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    season INTEGER,
                    games INTEGER,
                    games_started INTEGER,
                    complete_games INTEGER,
                    shutouts INTEGER,
                    wins INTEGER,
                    losses INTEGER,
                    saves INTEGER,
                    innings_pitched NUMERIC(6, 2),
                    hits_allowed INTEGER,
                    runs_allowed INTEGER,
                    earned_runs INTEGER,
                    home_runs_allowed INTEGER,
                    walks INTEGER,
                    strikeouts INTEGER,
                    era NUMERIC(5, 2),
                    whip NUMERIC(5, 3),
                    batters_faced INTEGER,
                    wild_pitches INTEGER,
                    hit_batters INTEGER,
                    balks INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_id, season)
                )
            """)
            
            # Create draft_results table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS draft_results (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(200) NOT NULL,
                    school VARCHAR(200),
                    draft_year INTEGER,
                    round INTEGER,
                    pick INTEGER,
                    team VARCHAR(100),
                    position VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_players_name_school 
                ON players(name, school)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_players_drafted 
                ON players(drafted)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hitting_stats_player 
                ON hitting_stats(player_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pitching_stats_player 
                ON pitching_stats(player_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_draft_results_name_school 
                ON draft_results(player_name, school)
            """)
            
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            raise
    
    def insert_conference(self, name, reference_id):
        """
        Insert or update conference information.
        
        Args:
            name: Conference name
            reference_id: Baseball Reference ID for the conference
            
        Returns:
            Conference ID
        """
        try:
            self.cursor.execute("""
                INSERT INTO conferences (name, reference_id)
                VALUES (%s, %s)
                ON CONFLICT (reference_id) 
                DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (name, reference_id))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error inserting conference: {e}")
            raise
    
    def get_or_create_player(self, name, school, conference_id, position=None, age=None, year_started=None, years_played=None, years_enrolled=None):
        """
        Get existing player or create new one.
        
        Args:
            name: Player name
            school: School name
            conference_id: Conference ID
            position: Player position
            age: Player age
            year_started: Year player started college (deprecated, not used)
            years_played: Number of years played (deprecated, not used)
            years_enrolled: Number of years enrolled (deprecated, not used)
            
        Returns:
            Player ID
        """
        try:
            # Check if year_started column exists
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='players' AND column_name='year_started'
            """)
            has_year_fields = self.cursor.fetchone() is not None
            
            if has_year_fields:
                # Use full schema with year fields
                self.cursor.execute("""
                    INSERT INTO players (name, school, conference_id, position, age, year_started, years_played, years_enrolled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name, school, conference_id)
                    DO UPDATE SET 
                        school = COALESCE(EXCLUDED.school, players.school),
                        position = COALESCE(EXCLUDED.position, players.position),
                        age = COALESCE(EXCLUDED.age, players.age),
                        year_started = COALESCE(EXCLUDED.year_started, players.year_started),
                        years_played = COALESCE(EXCLUDED.years_played, players.years_played),
                        years_enrolled = COALESCE(EXCLUDED.years_enrolled, players.years_enrolled),
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (name, school, conference_id, position, age, year_started, years_played, years_enrolled))
            else:
                # Use schema without year fields
                self.cursor.execute("""
                    INSERT INTO players (name, school, conference_id, position, age)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name, school, conference_id)
                    DO UPDATE SET 
                        school = COALESCE(EXCLUDED.school, players.school),
                        position = COALESCE(EXCLUDED.position, players.position),
                        age = COALESCE(EXCLUDED.age, players.age),
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (name, school, conference_id, position, age))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting/creating player: {e}")
            raise
    
    def insert_hitting_stats(self, player_id, season, stats_dict):
        """
        Insert hitting statistics for a player.
        
        Args:
            player_id: Player ID
            season: Season year
            stats_dict: Dictionary of hitting statistics
        """
        try:
            self.cursor.execute("""
                INSERT INTO hitting_stats (
                    player_id, season, games, at_bats, runs, hits, doubles,
                    triples, home_runs, rbi, walks, strikeouts, avg, obp, slg, ops,
                    stolen_bases, caught_stealing, hit_by_pitch, sacrifice_flys,
                    sacrifice_hits, intentional_walks, ground_into_double_play,
                    plate_appearances, total_bases
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (player_id, season)
                DO UPDATE SET
                    games = EXCLUDED.games,
                    at_bats = EXCLUDED.at_bats,
                    runs = EXCLUDED.runs,
                    hits = EXCLUDED.hits,
                    doubles = EXCLUDED.doubles,
                    triples = EXCLUDED.triples,
                    home_runs = EXCLUDED.home_runs,
                    rbi = EXCLUDED.rbi,
                    walks = EXCLUDED.walks,
                    strikeouts = EXCLUDED.strikeouts,
                    avg = EXCLUDED.avg,
                    obp = EXCLUDED.obp,
                    slg = EXCLUDED.slg,
                    ops = EXCLUDED.ops,
                    stolen_bases = EXCLUDED.stolen_bases,
                    caught_stealing = EXCLUDED.caught_stealing,
                    hit_by_pitch = EXCLUDED.hit_by_pitch,
                    sacrifice_flys = EXCLUDED.sacrifice_flys,
                    sacrifice_hits = EXCLUDED.sacrifice_hits,
                    intentional_walks = EXCLUDED.intentional_walks,
                    ground_into_double_play = EXCLUDED.ground_into_double_play,
                    plate_appearances = EXCLUDED.plate_appearances,
                    total_bases = EXCLUDED.total_bases
            """, (
                player_id, season,
                stats_dict.get('games'),
                stats_dict.get('at_bats'),
                stats_dict.get('runs'),
                stats_dict.get('hits'),
                stats_dict.get('doubles'),
                stats_dict.get('triples'),
                stats_dict.get('home_runs'),
                stats_dict.get('rbi'),
                stats_dict.get('walks'),
                stats_dict.get('strikeouts'),
                stats_dict.get('avg'),
                stats_dict.get('obp'),
                stats_dict.get('slg'),
                stats_dict.get('ops'),
                stats_dict.get('stolen_bases'),
                stats_dict.get('caught_stealing'),
                stats_dict.get('hit_by_pitch'),
                stats_dict.get('sacrifice_flys'),
                stats_dict.get('sacrifice_hits'),
                stats_dict.get('intentional_walks'),
                stats_dict.get('ground_into_double_play'),
                stats_dict.get('plate_appearances'),
                stats_dict.get('total_bases')
            ))
        except Exception as e:
            logger.error(f"Error inserting hitting stats: {e}")
            raise
    
    def insert_pitching_stats(self, player_id, season, stats_dict):
        """
        Insert pitching statistics for a player.
        
        Args:
            player_id: Player ID
            season: Season year
            stats_dict: Dictionary of pitching statistics
        """
        try:
            self.cursor.execute("""
                INSERT INTO pitching_stats (
                    player_id, season, games, games_started, complete_games,
                    shutouts, wins, losses, saves, innings_pitched, hits_allowed,
                    runs_allowed, earned_runs, home_runs_allowed, walks, strikeouts,
                    era, whip, batters_faced, wild_pitches, hit_batters, balks
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (player_id, season)
                DO UPDATE SET
                    games = EXCLUDED.games,
                    games_started = EXCLUDED.games_started,
                    complete_games = EXCLUDED.complete_games,
                    shutouts = EXCLUDED.shutouts,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    saves = EXCLUDED.saves,
                    innings_pitched = EXCLUDED.innings_pitched,
                    hits_allowed = EXCLUDED.hits_allowed,
                    runs_allowed = EXCLUDED.runs_allowed,
                    earned_runs = EXCLUDED.earned_runs,
                    home_runs_allowed = EXCLUDED.home_runs_allowed,
                    walks = EXCLUDED.walks,
                    strikeouts = EXCLUDED.strikeouts,
                    era = EXCLUDED.era,
                    whip = EXCLUDED.whip,
                    batters_faced = EXCLUDED.batters_faced,
                    wild_pitches = EXCLUDED.wild_pitches,
                    hit_batters = EXCLUDED.hit_batters,
                    balks = EXCLUDED.balks
            """, (
                player_id, season,
                stats_dict.get('games'),
                stats_dict.get('games_started'),
                stats_dict.get('complete_games'),
                stats_dict.get('shutouts'),
                stats_dict.get('wins'),
                stats_dict.get('losses'),
                stats_dict.get('saves'),
                stats_dict.get('innings_pitched'),
                stats_dict.get('hits_allowed'),
                stats_dict.get('runs_allowed'),
                stats_dict.get('earned_runs'),
                stats_dict.get('home_runs_allowed'),
                stats_dict.get('walks'),
                stats_dict.get('strikeouts'),
                stats_dict.get('era'),
                stats_dict.get('whip'),
                stats_dict.get('batters_faced'),
                stats_dict.get('wild_pitches'),
                stats_dict.get('hit_batters'),
                stats_dict.get('balks')
            ))
        except Exception as e:
            logger.error(f"Error inserting pitching stats: {e}")
            raise
    
    def insert_draft_result(self, player_name, school, draft_year, round_num, pick, team, position):
        """
        Insert draft result information.
        
        Args:
            player_name: Player name
            school: School name
            draft_year: Year of draft
            round_num: Draft round
            pick: Draft pick number
            team: Drafting team
            position: Player position
        """
        try:
            self.cursor.execute("""
                INSERT INTO draft_results (
                    player_name, school, draft_year, round, pick, team, position
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (player_name, school, draft_year, round_num, pick, team, position))
        except Exception as e:
            logger.error(f"Error inserting draft result: {e}")
            raise
    
    def update_player_draft_status(self, player_id, draft_year, draft_round, draft_pick, draft_team, position=None, match_type=None):
        """
        Update player's draft status.
        
        Args:
            player_id: Player ID
            draft_year: Year of draft
            draft_round: Draft round
            draft_pick: Draft pick number
            draft_team: Drafting team
            position: Player position (optional)
            match_type: How the match was made ('name_only' or 'name_and_team')
        """
        try:
            if position:
                self.cursor.execute("""
                    UPDATE players
                    SET drafted = TRUE,
                        draft_year = %s,
                        draft_round = %s,
                        draft_pick = %s,
                        draft_team = %s,
                        position = COALESCE(%s, position),
                        draft_match_type = COALESCE(%s, draft_match_type),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (draft_year, draft_round, draft_pick, draft_team, position, match_type, player_id))
            else:
                self.cursor.execute("""
                    UPDATE players
                    SET drafted = TRUE,
                        draft_year = %s,
                        draft_round = %s,
                        draft_pick = %s,
                        draft_team = %s,
                        draft_match_type = COALESCE(%s, draft_match_type),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (draft_year, draft_round, draft_pick, draft_team, match_type, player_id))
        except Exception as e:
            logger.error(f"Error updating player draft status: {e}")
            raise
    
    def find_player_by_name_school(self, name, school):
        """
        Find player ID by name and school.
        
        Args:
            name: Player name
            school: School name
            
        Returns:
            List of matching player IDs
        """
        try:
            self.cursor.execute("""
                SELECT id FROM players
                WHERE LOWER(name) = LOWER(%s)
                AND LOWER(school) = LOWER(%s)
            """, (name, school))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error finding player: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
