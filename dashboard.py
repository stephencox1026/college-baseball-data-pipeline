"""
Flask web dashboard for college baseball player analysis.
Shows top 50 hitters and pitchers based on custom criteria.
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import Database
from config import DB_CONFIG
import logging
import json
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


app.json_encoder = DecimalEncoder


def grade_pitcher(bb_per_9, k_per_bb, k_per_9, era, whip, innings_pitched, age):
    """
    Grade a pitcher from F to A+ based on their stats.
    Considers: BB/9, K/BB, K/9, ERA, WHIP, sample size (innings), and age.
    """
    if not all([bb_per_9 is not None, k_per_bb is not None, k_per_9 is not None]):
        return 'N/A', 'Insufficient data'
    
    score = 0.0
    max_score = 0.0
    
    # BB/9 scoring (lower is better) - 25% weight
    if bb_per_9 is not None:
        if bb_per_9 <= 1.5:
            score += 25
        elif bb_per_9 <= 2.5:
            score += 20
        elif bb_per_9 <= 3.5:
            score += 15
        elif bb_per_9 <= 4.5:
            score += 10
        else:
            score += 5
        max_score += 25
    
    # K/BB scoring (higher is better) - 25% weight
    if k_per_bb is not None:
        if k_per_bb >= 5.0:
            score += 25
        elif k_per_bb >= 3.5:
            score += 20
        elif k_per_bb >= 2.5:
            score += 15
        elif k_per_bb >= 1.5:
            score += 10
        else:
            score += 5
        max_score += 25
    
    # K/9 scoring (higher is better) - 20% weight
    if k_per_9 is not None:
        if k_per_9 >= 12.0:
            score += 20
        elif k_per_9 >= 10.0:
            score += 16
        elif k_per_9 >= 8.0:
            score += 12
        elif k_per_9 >= 6.0:
            score += 8
        else:
            score += 4
        max_score += 20
    
    # ERA scoring (lower is better) - 15% weight
    if era is not None:
        if era <= 2.0:
            score += 15
        elif era <= 3.0:
            score += 12
        elif era <= 4.0:
            score += 9
        elif era <= 5.0:
            score += 6
        else:
            score += 3
        max_score += 15
    
    # WHIP scoring (lower is better) - 15% weight
    if whip is not None:
        if whip <= 1.0:
            score += 15
        elif whip <= 1.2:
            score += 12
        elif whip <= 1.4:
            score += 9
        elif whip <= 1.6:
            score += 6
        else:
            score += 3
        max_score += 15
    
    # Sample size adjustment (more innings = more reliable) - bonus up to 5%
    if innings_pitched is not None:
        if innings_pitched >= 80:
            score += 5
        elif innings_pitched >= 50:
            score += 3
        elif innings_pitched >= 30:
            score += 1
        max_score += 5
    
    # Age adjustment (younger = more upside) - bonus up to 5%
    if age is not None:
        if age <= 19:
            score += 5
        elif age <= 20:
            score += 3
        elif age <= 21:
            score += 1
        max_score += 5
    
    # Convert score to grade
    percentage = (score / max_score) * 100 if max_score > 0 else 0
    
    if percentage >= 95:
        grade = 'A+'
    elif percentage >= 90:
        grade = 'A'
    elif percentage >= 85:
        grade = 'A-'
    elif percentage >= 80:
        grade = 'B+'
    elif percentage >= 75:
        grade = 'B'
    elif percentage >= 70:
        grade = 'B-'
    elif percentage >= 65:
        grade = 'C+'
    elif percentage >= 60:
        grade = 'C'
    elif percentage >= 55:
        grade = 'C-'
    elif percentage >= 50:
        grade = 'D+'
    elif percentage >= 45:
        grade = 'D'
    elif percentage >= 40:
        grade = 'D-'
    else:
        grade = 'F'
    
    return grade, percentage


def analyze_pitcher_upside_downside(bb_per_9, k_per_bb, k_per_9, era, whip, innings_pitched, age):
    """Analyze upside and downside for a pitcher based on grading criteria."""
    upside_parts = []
    downside_parts = []
    
    # Upside analysis
    if k_per_9 is not None and k_per_9 >= 10:
        upside_parts.append("High strikeout rate")
    if k_per_bb is not None and k_per_bb >= 3.5:
        upside_parts.append("Excellent command")
    if bb_per_9 is not None and bb_per_9 <= 2.5:
        upside_parts.append("Strong control")
    if age is not None and age <= 20:
        upside_parts.append("Young age with development potential")
    if innings_pitched is not None and innings_pitched >= 50:
        upside_parts.append("Proven workload")
    
    # Downside analysis - based on grading criteria (what hurts the grade)
    # BB/9 scoring (lower is better) - 25% weight
    if bb_per_9 is not None:
        if bb_per_9 > 4.5:
            downside_parts.append("Very high walk rate (hurts grade significantly)")
        elif bb_per_9 > 3.5:
            downside_parts.append("High walk rate")
        elif bb_per_9 > 2.5:
            downside_parts.append("Above-average walk rate")
    
    # K/BB ratio scoring (higher is better) - 25% weight
    if k_per_bb is not None:
        if k_per_bb < 1.8:
            downside_parts.append("Poor strikeout-to-walk ratio (major concern)")
        elif k_per_bb < 2.5:
            downside_parts.append("Below-average strikeout-to-walk ratio")
        elif k_per_bb < 3.5:
            downside_parts.append("Moderate strikeout-to-walk ratio")
    
    # K/9 scoring (higher is better) - 20% weight
    if k_per_9 is not None:
        if k_per_9 < 6.0:
            downside_parts.append("Low strikeout rate (limits upside)")
        elif k_per_9 < 8.0:
            downside_parts.append("Below-average strikeout rate")
        elif k_per_9 < 10.0:
            downside_parts.append("Moderate strikeout rate")
    
    # ERA scoring (lower is better) - 15% weight
    if era is not None:
        if era > 5.5:
            downside_parts.append("Very high ERA")
        elif era > 4.5:
            downside_parts.append("High ERA")
        elif era > 3.5:
            downside_parts.append("Above-average ERA")
    
    # WHIP scoring (lower is better) - 15% weight
    if whip is not None:
        if whip > 1.6:
            downside_parts.append("Very high WHIP")
        elif whip > 1.4:
            downside_parts.append("High WHIP")
        elif whip > 1.2:
            downside_parts.append("Above-average WHIP")
    
    # Sample size adjustment
    if innings_pitched is not None:
        if innings_pitched < 10:
            downside_parts.append("Very limited sample size (unreliable stats)")
        elif innings_pitched < 20:
            downside_parts.append("Limited sample size")
        elif innings_pitched < 30:
            downside_parts.append("Small sample size")
        elif innings_pitched < 50:
            downside_parts.append("Moderate sample size")
    
    # Age adjustment (younger is better)
    if age is not None:
        if age >= 24:
            downside_parts.append("Older prospect (less development time)")
        elif age >= 23:
            downside_parts.append("Older age for prospect")
    
    upside = ", ".join(upside_parts) if upside_parts else "Limited upside indicators"
    # Always provide downside - if no specific concerns, say what's average/neutral
    if not downside_parts:
        downside = "Average across all metrics (no major weaknesses)"
    else:
        downside = ". ".join(downside_parts)
    
    return upside, downside


def grade_hitter(bb_per_k, walk_strikeout_diff, obp, slg, ops, doubles, at_bats, age):
    """
    Grade a hitter from F to A+ based on their stats.
    Considers: BB/K, BB-K diff, OBP, SLG, OPS, doubles, sample size (AB), and age.
    """
    if not all([bb_per_k is not None, obp is not None, slg is not None, ops is not None]):
        return 'N/A', 'Insufficient data'
    
    score = 0.0
    max_score = 0.0
    
    # BB/K scoring (higher is better) - 20% weight
    if bb_per_k is not None:
        if bb_per_k >= 1.5:
            score += 20
        elif bb_per_k >= 1.2:
            score += 16
        elif bb_per_k >= 1.0:
            score += 12
        elif bb_per_k >= 0.8:
            score += 8
        else:
            score += 4
        max_score += 20
    
    # BB-K differential (positive is better) - 15% weight
    if walk_strikeout_diff is not None:
        if walk_strikeout_diff >= 30:
            score += 15
        elif walk_strikeout_diff >= 20:
            score += 12
        elif walk_strikeout_diff >= 10:
            score += 9
        elif walk_strikeout_diff >= 0:
            score += 6
        else:
            score += 3
        max_score += 15
    
    # OBP scoring (higher is better) - 20% weight
    if obp is not None:
        if obp >= 0.450:
            score += 20
        elif obp >= 0.400:
            score += 16
        elif obp >= 0.370:
            score += 12
        elif obp >= 0.340:
            score += 8
        else:
            score += 4
        max_score += 20
    
    # SLG scoring (higher is better) - 20% weight
    if slg is not None:
        if slg >= 0.600:
            score += 20
        elif slg >= 0.550:
            score += 16
        elif slg >= 0.500:
            score += 12
        elif slg >= 0.450:
            score += 8
        else:
            score += 4
        max_score += 20
    
    # OPS scoring (higher is better) - 15% weight
    if ops is not None:
        if ops >= 1.000:
            score += 15
        elif ops >= 0.900:
            score += 12
        elif ops >= 0.800:
            score += 9
        elif ops >= 0.700:
            score += 6
        else:
            score += 3
        max_score += 15
    
    # Doubles (power indicator) - 5% weight
    if doubles is not None and at_bats is not None and at_bats > 0:
        doubles_per_ab = doubles / at_bats
        if doubles_per_ab >= 0.10:
            score += 5
        elif doubles_per_ab >= 0.08:
            score += 4
        elif doubles_per_ab >= 0.06:
            score += 3
        else:
            score += 1
        max_score += 5
    
    # Sample size adjustment (more AB = more reliable) - bonus up to 3%
    if at_bats is not None:
        if at_bats >= 200:
            score += 3
        elif at_bats >= 150:
            score += 2
        elif at_bats >= 100:
            score += 1
        max_score += 3
    
    # Age adjustment (younger = more upside) - bonus up to 2%
    if age is not None:
        if age <= 19:
            score += 2
        elif age <= 20:
            score += 1
        max_score += 2
    
    # Convert score to grade
    percentage = (score / max_score) * 100 if max_score > 0 else 0
    
    if percentage >= 95:
        grade = 'A+'
    elif percentage >= 90:
        grade = 'A'
    elif percentage >= 85:
        grade = 'A-'
    elif percentage >= 80:
        grade = 'B+'
    elif percentage >= 75:
        grade = 'B'
    elif percentage >= 70:
        grade = 'B-'
    elif percentage >= 65:
        grade = 'C+'
    elif percentage >= 60:
        grade = 'C'
    elif percentage >= 55:
        grade = 'C-'
    elif percentage >= 50:
        grade = 'D+'
    elif percentage >= 45:
        grade = 'D'
    elif percentage >= 40:
        grade = 'D-'
    else:
        grade = 'F'
    
    return grade, percentage


def analyze_hitter_upside_downside(bb_per_k, walk_strikeout_diff, obp, slg, ops, doubles, at_bats, age):
    """Analyze upside and downside for a hitter based on grading criteria."""
    upside_parts = []
    downside_parts = []
    
    # Upside analysis
    if walk_strikeout_diff is not None and walk_strikeout_diff > 20:
        upside_parts.append("Excellent plate discipline")
    if bb_per_k is not None and bb_per_k >= 1.2:
        upside_parts.append("Strong walk-to-strikeout ratio")
    if ops is not None and ops >= 0.900:
        upside_parts.append("High OPS")
    if slg is not None and slg >= 0.550:
        upside_parts.append("Good power")
    if obp is not None and obp >= 0.400:
        upside_parts.append("High on-base ability")
    if age is not None and age <= 20:
        upside_parts.append("Young age with development potential")
    
    # Downside analysis - based on grading criteria (what hurts the grade)
    # BB/K scoring (higher is better) - 20% weight
    if bb_per_k is not None:
        if bb_per_k < 0.8:
            downside_parts.append("Poor walk-to-strikeout ratio (major concern)")
        elif bb_per_k < 1.0:
            downside_parts.append("Below-average walk-to-strikeout ratio")
        elif bb_per_k < 1.2:
            downside_parts.append("Moderate walk-to-strikeout ratio")
    
    # BB-K differential (positive is better) - 15% weight
    if walk_strikeout_diff is not None:
        if walk_strikeout_diff < -10:
            downside_parts.append("Many more strikeouts than walks (hurts grade)")
        elif walk_strikeout_diff < 0:
            downside_parts.append("More strikeouts than walks")
        elif walk_strikeout_diff < 10:
            downside_parts.append("Minimal walk advantage")
    
    # OBP scoring (higher is better) - 20% weight
    if obp is not None:
        if obp < 0.320:
            downside_parts.append("Very low on-base percentage")
        elif obp < 0.340:
            downside_parts.append("Low on-base percentage")
        elif obp < 0.370:
            downside_parts.append("Below-average on-base percentage")
    
    # SLG scoring (higher is better) - 20% weight
    if slg is not None:
        if slg < 0.400:
            downside_parts.append("Very limited power")
        elif slg < 0.450:
            downside_parts.append("Limited power")
        elif slg < 0.500:
            downside_parts.append("Below-average power")
    
    # OPS scoring (higher is better) - 15% weight
    if ops is not None:
        if ops < 0.700:
            downside_parts.append("Very low OPS")
        elif ops < 0.800:
            downside_parts.append("Low OPS")
        elif ops < 0.900:
            downside_parts.append("Below-average OPS")
    
    # Doubles (power indicator) - 5% weight
    if doubles is not None and at_bats is not None and at_bats > 0:
        doubles_per_ab = doubles / at_bats
        if doubles_per_ab < 0.06:
            downside_parts.append("Low doubles rate (limited extra-base power)")
    
    # Sample size adjustment
    if at_bats is not None:
        if at_bats < 100:
            downside_parts.append("Very limited sample size (unreliable stats)")
        elif at_bats < 150:
            downside_parts.append("Limited sample size")
        elif at_bats < 200:
            downside_parts.append("Moderate sample size")
    
    # Age adjustment (younger is better)
    if age is not None:
        if age >= 24:
            downside_parts.append("Older prospect (less development time)")
        elif age >= 23:
            downside_parts.append("Older age for prospect")
    
    upside = ", ".join(upside_parts) if upside_parts else "Limited upside indicators"
    # Always provide downside - if no specific concerns, say what's average/neutral
    if not downside_parts:
        downside = "Average across all metrics (no major weaknesses)"
    else:
        downside = ". ".join(downside_parts)
    
    return upside, downside


def get_conferences():
    """Get list of all conferences."""
    db = Database(DB_CONFIG)
    db.connect()
    try:
        db.cursor.execute("SELECT id, name FROM conferences ORDER BY name")
        return [{'id': row[0], 'name': row[1]} for row in db.cursor.fetchall()]
    finally:
        db.close()


def get_top_pitchers(limit=50, conference_id=None, drafted=None, min_ip=20, season=None, age=None):
    """
    Get top pitchers based on:
    - Strike throwing (low walks, high strikeout to walk ratio)
    - Strikeouts (secondary importance)
    - Control (walks per 9 innings)
    
    Returns:
        List of pitcher dictionaries with rankings and explanations
    """
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        logger.info(f"get_top_pitchers called with min_ip={min_ip}")
        
        # Handle IP range filter
        ip_filter_condition = ""
        
        if min_ip == '0-10':
            ip_filter_condition = "pi.innings_pitched >= 0 AND pi.innings_pitched <= 10"
        elif min_ip == '11-20':
            ip_filter_condition = "pi.innings_pitched >= 11 AND pi.innings_pitched <= 20"
        elif min_ip == '20+':
            ip_filter_condition = "pi.innings_pitched >= 20"
        else:
            # Default to 20+ if invalid
            ip_filter_condition = "pi.innings_pitched >= 20"
        
        # Calculate pitcher scores
        # Priority: Low BB/9, High K/BB ratio, High K/9
        query = f"""
            SELECT 
                p.id,
                p.name,
                p.school,
                p.age,
                c.name as conference_name,
                p.drafted,
                p.draft_team,
                p.draft_round,
                p.draft_pick,
                pi.season,
                pi.games,
                pi.games_started,
                pi.wins,
                pi.losses,
                pi.strikeouts,
                pi.walks,
                pi.innings_pitched,
                pi.era,
                pi.whip,
                pi.hits_allowed,
                pi.runs_allowed,
                pi.earned_runs,
                CASE 
                    WHEN pi.innings_pitched > 0 THEN (pi.walks::numeric / NULLIF(pi.innings_pitched, 0)) * 9
                    ELSE NULL
                END as bb_per_9,
                CASE 
                    WHEN pi.walks > 0 THEN pi.strikeouts::numeric / NULLIF(pi.walks, 0)
                    WHEN pi.strikeouts > 0 THEN 999  -- High score if no walks
                    ELSE NULL
                END as k_per_bb,
                CASE 
                    WHEN pi.innings_pitched > 0 THEN (pi.strikeouts::numeric / NULLIF(pi.innings_pitched, 0)) * 9
                    ELSE NULL
                END as k_per_9
            FROM pitching_stats pi
            JOIN players p ON pi.player_id = p.id
            LEFT JOIN conferences c ON p.conference_id = c.id
            WHERE {ip_filter_condition}  -- IP range filter
                AND pi.walks IS NOT NULL
                AND pi.strikeouts IS NOT NULL
        """
        
        # Add filters (no min_ip in filters since it's in the WHERE clause)
        filters = []
        logger.info(f"Query filters initialized with min_ip={min_ip}, ip_filter_condition={ip_filter_condition}")
        filter_conditions = []
        
        if conference_id:
            if isinstance(conference_id, list) and len(conference_id) > 0:
                placeholders = ','.join(['%s'] * len(conference_id))
                filter_conditions.append(f"p.conference_id IN ({placeholders})")
                filters.extend(conference_id)
            elif conference_id:
                filter_conditions.append("p.conference_id = %s")
                filters.append(conference_id)
        
        if drafted is not None:
            if isinstance(drafted, list) and len(drafted) > 0:
                # Handle multiple draft statuses
                conditions = []
                for d in drafted:
                    if d == 'drafted':
                        conditions.append("p.drafted = TRUE")
                    elif d == 'not_drafted':
                        conditions.append("p.drafted = FALSE")
                if conditions:
                    filter_conditions.append("(" + " OR ".join(conditions) + ")")
            elif drafted == 'drafted':
                filter_conditions.append("p.drafted = TRUE")
            elif drafted == 'not_drafted':
                filter_conditions.append("p.drafted = FALSE")
            else:
                # Legacy: 'true' or 'false'
                filter_conditions.append("p.drafted = %s")
                filters.append(drafted == 'true')
        
        if season:
            if isinstance(season, list) and len(season) > 0:
                placeholders = ','.join(['%s'] * len(season))
                filter_conditions.append(f"pi.season IN ({placeholders})")
                filters.extend(season)
            elif season:
                filter_conditions.append("pi.season = %s")
                filters.append(season)
        
        if age:
            if isinstance(age, list) and len(age) > 0:
                placeholders = ','.join(['%s'] * len(age))
                filter_conditions.append(f"p.age IN ({placeholders})")
                filters.extend(age)
            elif age:
                filter_conditions.append("p.age = %s")
                filters.append(age)
        
        if filter_conditions:
            query = query.rstrip() + " AND " + " AND ".join(filter_conditions) + "\n"
        
        query += """
            ORDER BY 
                -- Primary: Low BB/9 (ascending)
                bb_per_9 ASC NULLS LAST,
                -- Secondary: High K/BB ratio (descending)
                k_per_bb DESC NULLS LAST,
                -- Tertiary: High K/9 (descending)
                k_per_9 DESC NULLS LAST
            LIMIT %s
        """
        
        filters.append(limit)
        db.cursor.execute(query, tuple(filters))
        results = db.cursor.fetchall()
        
        pitchers = []
        for rank, row in enumerate(results, 1):
            innings = row[16] or 0  # pi.innings_pitched
            walks = row[15] or 0    # pi.walks
            strikeouts = row[14] or 0  # pi.strikeouts
            
            # Calculate metrics (convert to float)
            bb_per_9 = float(walks / innings * 9) if innings > 0 else None
            k_per_bb = float(strikeouts / walks) if walks > 0 else (999.0 if strikeouts > 0 else None)
            k_per_9 = float(strikeouts / innings * 9) if innings > 0 else None
            
            # Calculate composite score (lower is better for BB/9, higher is better for others)
            # Normalize: BB/9 weight = 40%, K/BB weight = 40%, K/9 weight = 20%
            score = None
            if bb_per_9 is not None and k_per_bb is not None and k_per_9 is not None:
                # Invert BB/9 for scoring (lower is better, so we subtract from a high number)
                bb_score = max(0, 10 - bb_per_9) * 0.4  # Max score when BB/9 = 0
                k_bb_score = min(k_per_bb / 10, 1) * 0.4  # Cap at 10:1 ratio
                k_9_score = min(k_per_9 / 15, 1) * 0.2  # Cap at 15 K/9
                score = bb_score + k_bb_score + k_9_score
            
            # Generate explanation
            explanation_parts = []
            if bb_per_9 is not None:
                if bb_per_9 < 2.0:
                    explanation_parts.append(f"Excellent control with {bb_per_9:.2f} BB/9")
                elif bb_per_9 < 3.0:
                    explanation_parts.append(f"Good control with {bb_per_9:.2f} BB/9")
                else:
                    explanation_parts.append(f"BB/9 of {bb_per_9:.2f}")
            
            if k_per_bb is not None:
                if k_per_bb > 5.0:
                    explanation_parts.append(f"outstanding {k_per_bb:.1f}:1 K/BB ratio")
                elif k_per_bb > 3.0:
                    explanation_parts.append(f"strong {k_per_bb:.1f}:1 K/BB ratio")
                else:
                    explanation_parts.append(f"{k_per_bb:.1f}:1 K/BB ratio")
            
            if k_per_9 is not None:
                if k_per_9 > 10:
                    explanation_parts.append(f"{k_per_9:.1f} K/9")
                else:
                    explanation_parts.append(f"{k_per_9:.1f} K/9")
            
            explanation = ". ".join(explanation_parts) + "."
            
            # Calculate grade and analysis with error handling
            try:
                grade, grade_pct = grade_pitcher(bb_per_9, k_per_bb, k_per_9, float(row[17]) if row[17] is not None else None, 
                                                float(row[18]) if row[18] is not None else None, 
                                                float(innings) if innings else None, row[3])
                upside, downside = analyze_pitcher_upside_downside(bb_per_9, k_per_bb, k_per_9, 
                                                                   float(row[17]) if row[17] is not None else None,
                                                                   float(row[18]) if row[18] is not None else None,
                                                                   float(innings) if innings else None, row[3])
            except Exception as e:
                logger.error(f"Error calculating grade/analysis for pitcher {row[1]}: {e}")
                grade = 'N/A'
                upside = 'Error calculating'
                downside = 'Error calculating'
            
            pitcher = {
                'rank': rank,
                'name': row[1],
                'school': row[2] or 'Unknown',
                'age': row[3],
                'conference_name': row[4] or 'Unknown',
                'drafted': row[5],
                'draft_team': row[6] or '',
                'draft_round': row[7],
                'draft_pick': row[8],
                'season': row[9],
                'games': row[10],
                'games_started': row[11],
                'wins': row[12],
                'losses': row[13],
                'strikeouts': strikeouts,
                'walks': walks,
                'innings_pitched': float(innings) if innings else None,
                'era': float(row[17]) if row[17] is not None else None,
                'whip': float(row[18]) if row[18] is not None else None,
                'bb_per_9': round(bb_per_9, 2) if bb_per_9 is not None else None,
                'k_per_bb': round(k_per_bb, 2) if k_per_bb is not None else None,
                'k_per_9': round(k_per_9, 2) if k_per_9 is not None else None,
                'score': round(score, 3) if score is not None else None,
                'explanation': explanation,
                'grade': grade,
                'upside': upside,
                'downside': downside
            }
            pitchers.append(pitcher)
        
        return pitchers
    
    finally:
        db.close()


def get_top_hitters(limit=50, conference_id=None, drafted=None, min_ab=100, season=None, age=None):
    """
    Get top hitters based on:
    - Strikeout to walk ratio (more walks than strikeouts)
    - Slugging percentage
    - On-base percentage
    - OPS (OBP + SLG)
    - Doubles
    
    Returns:
        List of hitter dictionaries with rankings and explanations
    """
    db = Database(DB_CONFIG)
    db.connect()
    
    try:
        # Calculate hitter scores
        query = """
            SELECT 
                p.id,
                p.name,
                p.school,
                p.age,
                c.name as conference_name,
                p.drafted,
                p.draft_team,
                p.draft_round,
                p.draft_pick,
                h.season,
                h.games,
                h.at_bats,
                h.hits,
                h.doubles,
                h.triples,
                h.home_runs,
                h.rbi,
                h.walks,
                h.strikeouts,
                h.avg,
                h.obp,
                h.slg,
                h.ops,
                h.stolen_bases,
                CASE 
                    WHEN h.strikeouts > 0 THEN h.walks::numeric / NULLIF(h.strikeouts, 0)
                    WHEN h.walks > 0 THEN 999  -- High score if no strikeouts
                    ELSE NULL
                END as bb_per_k,
                CASE 
                    WHEN h.strikeouts > 0 THEN h.walks::numeric - h.strikeouts
                    ELSE h.walks
                END as walk_strikeout_diff
            FROM hitting_stats h
            JOIN players p ON h.player_id = p.id
            LEFT JOIN conferences c ON p.conference_id = c.id
            WHERE h.at_bats >= %s  -- Minimum AB threshold
                AND h.walks IS NOT NULL
                AND h.strikeouts IS NOT NULL
                AND h.obp IS NOT NULL
                AND h.slg IS NOT NULL
        """
        
        # Add filters
        filters = [min_ab]
        filter_conditions = []
        
        if conference_id:
            if isinstance(conference_id, list) and len(conference_id) > 0:
                placeholders = ','.join(['%s'] * len(conference_id))
                filter_conditions.append(f"p.conference_id IN ({placeholders})")
                filters.extend(conference_id)
            elif conference_id:
                filter_conditions.append("p.conference_id = %s")
                filters.append(conference_id)
        
        if drafted is not None:
            if isinstance(drafted, list) and len(drafted) > 0:
                # Handle multiple draft statuses
                conditions = []
                for d in drafted:
                    if d == 'drafted':
                        conditions.append("p.drafted = TRUE")
                    elif d == 'not_drafted':
                        # Include both FALSE and NULL for not drafted
                        conditions.append("(p.drafted = FALSE OR p.drafted IS NULL)")
                if conditions:
                    filter_conditions.append("(" + " OR ".join(conditions) + ")")
            elif isinstance(drafted, str):
                if drafted == 'drafted':
                    filter_conditions.append("p.drafted = TRUE")
                elif drafted == 'not_drafted':
                    # Include both FALSE and NULL for not drafted
                    filter_conditions.append("(p.drafted = FALSE OR p.drafted IS NULL)")
            else:
                # Legacy: 'true' or 'false'
                filter_conditions.append("p.drafted = %s")
                filters.append(drafted == 'true')
        
        if season:
            if isinstance(season, list) and len(season) > 0:
                placeholders = ','.join(['%s'] * len(season))
                filter_conditions.append(f"h.season IN ({placeholders})")
                filters.extend(season)
            elif season:
                filter_conditions.append("h.season = %s")
                filters.append(season)
        
        if age:
            if isinstance(age, list) and len(age) > 0:
                placeholders = ','.join(['%s'] * len(age))
                filter_conditions.append(f"p.age IN ({placeholders})")
                filters.extend(age)
            elif age:
                filter_conditions.append("p.age = %s")
                filters.append(age)
        
        if filter_conditions:
            query = query.rstrip() + " AND " + " AND ".join(filter_conditions) + "\n"
        
        query += """
            ORDER BY 
                -- Primary: More walks than strikeouts (walk_strikeout_diff descending)
                walk_strikeout_diff DESC NULLS LAST,
                -- Secondary: High BB/K ratio
                bb_per_k DESC NULLS LAST,
                -- Tertiary: High OPS
                h.ops DESC NULLS LAST,
                -- Quaternary: High doubles
                h.doubles DESC NULLS LAST,
                -- Quinary: High slugging
                h.slg DESC NULLS LAST
            LIMIT %s
        """
        
        filters.append(limit)
        logger.info(f"Executing hitter query with {len(filters)} filters: {filters}")
        logger.info(f"Full hitter query: {query}")
        try:
            db.cursor.execute(query, tuple(filters))
            results = db.cursor.fetchall()
            logger.info(f"Hitter query returned {len(results)} results")
        except Exception as e:
            logger.error(f"Error executing hitter query: {e}")
            logger.error(f"Query was: {query}")
            logger.error(f"Filters were: {filters}")
            raise
        
        hitters = []
        for rank, row in enumerate(results, 1):
            walks = row[17] or 0  # h.walks
            strikeouts = row[18] or 0  # h.strikeouts
            doubles = row[13] or 0  # h.doubles
            
            # Calculate metrics
            bb_per_k = float(walks / strikeouts) if strikeouts > 0 else (999.0 if walks > 0 else None)
            walk_strikeout_diff = int(walks - strikeouts)
            
            # Generate explanation
            explanation_parts = []
            
            if walk_strikeout_diff is not None:
                if walk_strikeout_diff > 20:
                    explanation_parts.append(f"Excellent plate discipline with {walk_strikeout_diff:+d} walk/strikeout differential")
                elif walk_strikeout_diff > 0:
                    explanation_parts.append(f"More walks ({walks}) than strikeouts ({strikeouts})")
                elif walk_strikeout_diff > -10:
                    explanation_parts.append(f"Good plate discipline with {walk_strikeout_diff:+d} differential")
                else:
                    explanation_parts.append(f"{walk_strikeout_diff:+d} walk/strikeout differential")
            
            if row[20] is not None:  # OBP
                if row[20] > 0.450:
                    explanation_parts.append(f"elite {row[20]:.3f} OBP")
                elif row[20] > 0.400:
                    explanation_parts.append(f"strong {row[20]:.3f} OBP")
                else:
                    explanation_parts.append(f"{row[20]:.3f} OBP")
            
            if row[21] is not None:  # SLG
                if row[21] > 0.600:
                    explanation_parts.append(f"elite {row[21]:.3f} slugging")
                elif row[21] > 0.500:
                    explanation_parts.append(f"strong {row[21]:.3f} slugging")
                else:
                    explanation_parts.append(f"{row[21]:.3f} slugging")
            
            # Calculate OPS - use stored if valid, otherwise calculate from OBP + SLG
            stored_ops = float(row[22]) if row[22] is not None else None  # h.ops
            obp_val = float(row[20]) if row[20] is not None else 0  # h.obp
            slg_val = float(row[21]) if row[21] is not None else 0  # h.slg
            calculated_ops = obp_val + slg_val if (obp_val > 0 or slg_val > 0) else None
            
            # Use calculated OPS if stored seems wrong (OPS should be between 0 and ~2.0 typically)
            if stored_ops is not None and 0 <= stored_ops <= 2.5:
                ops_value = stored_ops
            elif calculated_ops is not None:
                ops_value = calculated_ops
            else:
                ops_value = None
            
            # Add OPS to explanation using corrected value
            if ops_value is not None:
                if ops_value > 1.000:
                    explanation_parts.append(f"{ops_value:.3f} OPS")
                elif ops_value > 0.900:
                    explanation_parts.append(f"{ops_value:.3f} OPS")
            
            if doubles > 15:
                explanation_parts.append(f"{doubles} doubles")
            
            explanation = ". ".join(explanation_parts) + "."
            
            # Calculate grade and analysis with error handling
            try:
                grade, grade_pct = grade_hitter(bb_per_k, walk_strikeout_diff, 
                                               round(float(row[20]), 3) if row[20] is not None else None,
                                               round(float(row[21]), 3) if row[21] is not None else None,
                                               round(ops_value, 3) if ops_value is not None else None,
                                               doubles, row[11], row[3])
                upside, downside = analyze_hitter_upside_downside(bb_per_k, walk_strikeout_diff,
                                                                 round(float(row[20]), 3) if row[20] is not None else None,
                                                                 round(float(row[21]), 3) if row[21] is not None else None,
                                                                 round(ops_value, 3) if ops_value is not None else None,
                                                                 doubles, row[11], row[3])
            except Exception as e:
                logger.error(f"Error calculating grade/analysis for hitter {row[1]}: {e}")
                grade = 'N/A'
                upside = 'Error calculating'
                downside = 'Error calculating'
            
            hitter = {
                'rank': rank,
                'name': row[1],
                'school': row[2] if row[2] else None,  # Don't use 'Unknown', use None
                'age': row[3],
                'conference_name': row[4] if row[4] else None,  # Don't use 'Unknown', use None
                'drafted': row[5],
                'draft_team': row[6] or '',
                'draft_round': row[7],
                'draft_pick': row[8],
                'season': row[9],
                'games': row[10],
                'at_bats': row[11],
                'hits': row[12],
                'doubles': doubles,
                'triples': row[14] or 0,
                'home_runs': row[15] or 0,
                'rbi': row[16] or 0,
                'walks': walks,
                'strikeouts': strikeouts,
                'avg': round(row[19], 3) if row[19] is not None else None,
                'obp': round(float(row[20]), 3) if row[20] is not None else None,
                'slg': round(float(row[21]), 3) if row[21] is not None else None,
                'ops': round(ops_value, 3) if ops_value is not None else None,
                'stolen_bases': int(row[23]) if row[23] is not None else 0,
                'bb_per_k': round(bb_per_k, 2) if bb_per_k is not None else None,
                'walk_strikeout_diff': walk_strikeout_diff,
                'explanation': explanation,
                'grade': grade,
                'upside': upside,
                'downside': downside
            }
            hitters.append(hitter)
        
        return hitters
    
    finally:
        db.close()


@app.route('/')
def index():
    """Main dashboard page."""
    conferences = get_conferences()
    return render_template('dashboard.html', conferences=conferences)


@app.route('/api/conferences')
def api_conferences():
    """API endpoint for conferences."""
    conferences = get_conferences()
    return jsonify(conferences)


@app.route('/api/seasons')
def api_seasons():
    """API endpoint for available seasons."""
    db = Database(DB_CONFIG)
    db.connect()
    try:
        # Get unique seasons from both hitting and pitching stats
        db.cursor.execute("""
            SELECT DISTINCT season FROM hitting_stats 
            WHERE season IS NOT NULL
            UNION
            SELECT DISTINCT season FROM pitching_stats 
            WHERE season IS NOT NULL
            ORDER BY season DESC
        """)
        seasons = [row[0] for row in db.cursor.fetchall()]
        return jsonify(seasons)
    finally:
        db.close()


@app.route('/api/pitchers')
def api_pitchers():
    """API endpoint for top pitchers with filters."""
    try:
        limit = int(request.args.get('limit', 50))
        # Handle multiple selections
        conference_id = request.args.getlist('conference_id', type=int) or request.args.get('conference_id', type=int)
        drafted = request.args.getlist('drafted') or request.args.get('drafted')
        # Handle min_ip range filter
        min_ip = request.args.get('min_ip', '20+')
        if min_ip not in ['0-10', '11-20', '20+']:
            min_ip = '20+'  # Default to 20+ if invalid
        logger.info(f"API request - min_ip: {min_ip}, all args: {dict(request.args)}")
        season = request.args.getlist('season', type=int) or request.args.get('season', type=int)
        age = request.args.getlist('age', type=int) or request.args.get('age', type=int)
        
        pitchers = get_top_pitchers(
            limit=limit,
            conference_id=conference_id,
            drafted=drafted,
            min_ip=min_ip,
            season=season,
            age=age
        )
        return jsonify(pitchers)
    except Exception as e:
        logger.error(f"Error in api_pitchers: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/hitters')
def api_hitters():
    """API endpoint for top hitters with filters."""
    try:
        limit = int(request.args.get('limit', 50))
        # Handle multiple selections
        conference_id = request.args.getlist('conference_id', type=int) or request.args.get('conference_id', type=int)
        drafted = request.args.getlist('drafted') or request.args.get('drafted')
        min_ab = int(request.args.get('min_ab', 100))
        season = request.args.getlist('season', type=int) or request.args.get('season', type=int)
        age = request.args.getlist('age', type=int) or request.args.get('age', type=int)
        
        logger.info(f"API hitters request - drafted: {drafted}, all args: {dict(request.args)}")
        
        hitters = get_top_hitters(
            limit=limit,
            conference_id=conference_id,
            drafted=drafted,
            min_ab=min_ab,
            season=season,
            age=age
        )
        
        logger.info(f"API hitters returned {len(hitters)} results")
        return jsonify(hitters)
    except Exception as e:
        logger.error(f"Error in api_hitters: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 8080))  # Use 8080 as default, or PORT env variable
    app.run(debug=True, host='0.0.0.0', port=port)

