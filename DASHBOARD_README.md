# College Baseball Analysis Dashboard

## Overview
Interactive web dashboard showing the top 50 pitchers and hitters based on custom criteria.

## Ranking Criteria

### Pitchers
Ranked by (in priority order):
1. **Strike Throwing (BB/9)** - Lower is better (fewer walks per 9 innings)
2. **K/BB Ratio** - Higher is better (more strikeouts per walk)
3. **K/9** - Strikeouts per 9 innings (secondary importance)

### Hitters
Ranked by (in priority order):
1. **Walk/Strikeout Differential** - More walks than strikeouts (higher is better)
2. **BB/K Ratio** - Walks divided by strikeouts (higher is better)
3. **OPS** - On-base plus slugging percentage
4. **Doubles** - Total doubles hit
5. **Slugging Percentage** - Secondary tiebreaker

## Running the Dashboard

1. **Start the server:**
   ```bash
   python3 dashboard.py
   ```

2. **Open in browser:**
   Navigate to: `http://localhost:8080`
   
   Note: If port 8080 is in use, you can set a custom port:
   ```bash
   PORT=3000 python3 dashboard.py
   ```

3. **Use the dashboard:**
   - Click "Top 50 Pitchers" or "Top 50 Hitters" tabs to switch views
   - View interactive charts showing top 20 players
   - Scroll through the full table of all 50 players
   - See explanations for why each player is ranked

## Features

- **Two Views:** Separate tabs for pitchers and hitters
- **Interactive Charts:** Visual comparison of top 20 players
- **Detailed Stats:** Complete statistics for each player
- **Ranking Explanations:** Why each player made the list
- **Draft Status:** See which players have been drafted
- **Summary Statistics:** Overview cards at the top of each view

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/pitchers` - JSON data for top 50 pitchers
- `GET /api/hitters` - JSON data for top 50 hitters

## Notes

- Minimum thresholds: Pitchers need 20+ innings, Hitters need 100+ at-bats
- Players with multiple seasons may appear multiple times
- Draft information is displayed when available

