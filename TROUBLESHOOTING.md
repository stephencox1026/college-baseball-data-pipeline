# Dashboard Troubleshooting Guide

## Port Issues

If you see "Address already in use":

1. **Kill existing processes:**
   ```bash
   lsof -ti:8080 | xargs kill -9
   pkill -f "python3 dashboard.py"
   ```

2. **Use a different port:**
   ```bash
   PORT=3000 python3 dashboard.py
   ```
   Then access: `http://localhost:3000`

## Blank Page / "Error loading data"

### Check 1: Server is Running
```bash
ps aux | grep "python3 dashboard.py"
```

If not running, start it:
```bash
python3 dashboard.py
```

### Check 2: Browser Console
1. Open browser to `http://localhost:8080`
2. Press **F12** (or Cmd+Option+I on Mac)
3. Go to **Console** tab
4. Look for red error messages
5. Go to **Network** tab
6. Refresh the page
7. Check if `/api/pitchers` and `/api/hitters` show status 200

### Check 3: Database Connection
```bash
python3 -c "from database import Database; from config import DB_CONFIG; db = Database(DB_CONFIG); db.connect(); print('✓ Database connected'); db.close()"
```

### Check 4: API Endpoints
Test directly:
```bash
curl http://localhost:8080/api/pitchers?limit=1
curl http://localhost:8080/api/hitters?limit=1
```

## Common Issues

### "No data on page"
- Check browser console for JavaScript errors
- Verify API endpoints return data (use curl commands above)
- Make sure PostgreSQL is running
- Check that database has data: `SELECT COUNT(*) FROM players;`

### Filters not working
- Check browser console for errors
- Verify filter values are valid (conference_id 1-4)
- Try resetting filters and applying again

### Charts not displaying
- Check if Chart.js is loading (Network tab)
- Verify data array is not empty
- Check browser console for Chart.js errors

## Quick Test

Run this to verify everything:
```bash
python3 -c "
from dashboard import get_top_pitchers, get_top_hitters
print('Testing...')
p = get_top_pitchers(1)
h = get_top_hitters(1)
print(f'✓ Pitchers: {len(p)}')
print(f'✓ Hitters: {len(h)}')
print('All systems working!')
"
```

