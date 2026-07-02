# Dashboard Filters Guide

## Available Filters

The dashboard now includes comprehensive filtering options for both pitchers and hitters:

### Pitcher Filters
- **Conference**: Filter by specific conference (Conference 1-4)
- **Draft Status**: 
  - All Players
  - Drafted Only
  - Not Drafted
- **Season**: Filter by specific year (e.g., 2025)
- **Minimum Innings**: Set minimum innings pitched threshold (default: 20)

### Hitter Filters
- **Conference**: Filter by specific conference (Conference 1-4)
- **Draft Status**: 
  - All Players
  - Drafted Only
  - Not Drafted
- **Season**: Filter by specific year (e.g., 2025)
- **Minimum At-Bats**: Set minimum at-bats threshold (default: 100)

## How to Use Filters

1. **Select your filters** from the dropdown menus and input fields
2. **Click "Apply Filters"** to update the results
3. **Click "Reset"** to clear all filters and return to default view

## Filter Combinations

You can combine multiple filters:
- Example: "Drafted pitchers from Conference 1 with 30+ innings"
- Example: "Undrafted hitters from Conference 2 with 150+ at-bats in 2025"

## API Usage

Filters are available via API endpoints:

### Pitchers API
```
GET /api/pitchers?conference_id=1&drafted=true&season=2025&min_ip=30&limit=50
```

### Hitters API
```
GET /api/hitters?conference_id=2&drafted=false&season=2025&min_ab=150&limit=50
```

### Parameters
- `conference_id`: Integer (1-4)
- `drafted`: "true" or "false"
- `season`: Integer year (e.g., 2025)
- `min_ip`: Minimum innings pitched (default: 20)
- `min_ab`: Minimum at-bats (default: 100)
- `limit`: Number of results (default: 50)

## Troubleshooting

If you encounter errors:
1. Make sure PostgreSQL is running
2. Check that the database has data
3. Verify filter values are valid (conference_id 1-4, etc.)
4. Check server logs for detailed error messages

