import asyncio
import os
import httpx
import re
from datetime import datetime, timedelta
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings
from scripts.calculate_points import calculate_all_sessions_for_match

MONGO_URI = settings.MONGO_URI
DB_NAME = settings.DB_NAME
IST = pytz.timezone("Asia/Kolkata")

# ─── API CONFIGURATION ───────────────────────────────────────────────────────
CRICBUZZ_API_BASE = "https://m.cricbuzz.com/api/mcenter/over-by-over"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

def parse_ovr_summary(summary_str: str):
    """
    Parses '0 4 6 Wd 1 ' into ['0', '4', '6', 'Wd', '1']
    """
    if not summary_str: return []
    raw_balls = summary_str.strip().split(' ')
    clean_balls = []
    for b in raw_balls:
        if not b: continue
        # Normalize markers
        if b == 'N': clean_balls.append('Nb')
        elif b == 'Wd': clean_balls.append('Wd')
        elif b == 'W': clean_balls.append('W')
        else: clean_balls.append(b)
    return clean_balls

def is_over_complete(balls):
    """Returns True if there are 6 or more legal balls."""
    legal = [b for b in balls if b not in ['Wd', 'Nb']]
    return len(legal) >= 6

async def fetch_overs_from_api(client, match_id, innings_id, timestamp=None):
    """Fetches a single page of over data from the Cricbuzz API."""
    url = f"{CRICBUZZ_API_BASE}/{match_id}/{innings_id}"
    if timestamp:
        url = f"{url}/{timestamp}"
    
    try:
        response = await client.get(url, headers=HEADERS, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[API-FETCH] Error fetching {url}: {e}")
        return None

async def sync_innings_data(db, match_id, innings_id):
    """
    Recursively fetches and persists all overs for an innings using the API.
    Ensures no gaps exist in the database.
    """
    match_data_collection = db["live_match_overs"]
    
    # 1. Check what we already have for this innings
    existing_overs = await match_data_collection.distinct("over", {"match_id": match_id, "session_id": innings_id})
    existing_overs_set = set(existing_overs)
    
    async with httpx.AsyncClient() as client:
        current_timestamp = None
        has_more = True
        total_recovered = 0
        latest_score_data = None

        # Fetch CID from match_id first to use in API calls
        match_doc = await db.matches.find_one({"match_id": match_id})
        c_id = match_doc.get("cricbuzz_id")
        if not c_id: return None

        while has_more:
            data = await fetch_overs_from_api(client, c_id, innings_id, current_timestamp)
            if not data or 'paginatedData' not in data:
                break
            
            overs_list = data.get('paginatedData', [])
            if not overs_list:
                break

            for ovr_item in overs_list:
                over_num = ovr_item.get('overs')
                if over_num is None: continue
                
                # Capture latest metrics from the most recent over in the feed
                if latest_score_data is None:
                    latest_score_data = {
                        "current_score": ovr_item.get("score", "0/0"),
                        "current_over": float(over_num),
                        "innings": innings_id
                    }

                balls = parse_ovr_summary(ovr_item.get('ovrSummary', ''))
                
                # Logic: if missing or incomplete, update/upsert
                existing_balls = await get_existing_balls(match_data_collection, match_id, innings_id, over_num)
                if over_num not in existing_overs_set or not is_over_complete(existing_balls):
                    over_record = {
                        "match_id": match_id,
                        "session_id": innings_id,
                        "over": over_num,
                        "balls": balls,
                        "total_runs": ovr_item.get("runs", 0),
                        "current_score": ovr_item.get("score", "0/0"),
                        "current_over": float(over_num),
                        "timestamp": ovr_item.get("timestamp")
                    }
                    
                    await match_data_collection.update_one(
                        {"match_id": match_id, "session_id": innings_id, "over": over_num},
                        {"$set": over_record},
                        upsert=True
                    )
                    total_recovered += 1
                    existing_overs_set.add(over_num)

            # Pagination handling
            next_url = data.get('nextPaginationURL')
            if next_url:
                # Extract timestamp from "/api/mcenter/over-by-over/MATCHID/INNID/TIMESTAMP"
                parts = next_url.strip('/').split('/')
                # Filter out empty strings from splitting
                parts = [p for p in parts if p]
                if len(parts) >= 5:
                    current_timestamp = parts[-1]
                else:
                    has_more = False
            else:
                has_more = False

            # Optimization: If we've already seen all overs up to 1, or we've recovered a full innings, stop.
            if 1 in existing_overs_set:
                max_over = max(existing_overs_set)
                gaps = [o for o in range(1, max_over + 1) if o not in existing_overs_set]
                if not gaps:
                    has_more = False

        if total_recovered > 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[92mNEXUS API: Synced {total_recovered} overs for {match_id} (Inn {innings_id})\033[0m")
        
        return latest_score_data

async def get_existing_balls(collection, match_id, session_id, over_num):
    doc = await collection.find_one({"match_id": match_id, "session_id": session_id, "over": over_num})
    return doc.get("balls", []) if doc else []

# ─── CORE AGENT LOGIC ────────────────────────────────────────────────────────

def is_match_in_window(match: dict) -> bool:
    try:
        match_date = match.get("date")
        match_time = match.get("time")
        if not match_date or not match_time: return True

        match_dt_str = f"{match_date} {match_time}"
        match_dt = IST.localize(datetime.strptime(match_dt_str, "%Y-%m-%d %I:%M %p"))
        now_ist = datetime.now(IST)

        window_start = match_dt - timedelta(hours=24) # Relaxed for backfills
        window_end = match_dt + timedelta(hours=72) # Relaxed for backfills

        return window_start <= now_ist <= window_end
    except Exception as e:
        return True

async def run_cricbuzz_pulse():
    raw_uri = settings.MONGO_URI.strip().strip("'").strip('"')
    
    if not raw_uri or not (raw_uri.startswith("mongodb://") or raw_uri.startswith("mongodb+srv://")):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[91mNEXUS ERROR: Invalid MONGO_URI\033[0m")
        return

    try:
        client_db = AsyncIOMotorClient(raw_uri)
        db = client_db[DB_NAME]
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[91mNEXUS ERROR: DB Connection Failed: {e}\033[0m")
        return
    
    ist_date = datetime.now(IST).strftime("%Y-%m-%d")
    # Find LIVE matches or matches starting today
    cursor = db.matches.find({"$or": [{"status": "LIVE"}, {"date": ist_date}]})
    active_matches = await cursor.to_list(10)
    
    if not active_matches:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[90mNEXUS: Standby mode (No active matches for {ist_date})\033[0m")
        client_db.close()
        return

    for match in active_matches:
        c_id = match.get("cricbuzz_id")
        match_id = match["match_id"]
        if not c_id: continue

        if not is_match_in_window(match):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[90mNEXUS: {match_id} ({match.get('team1')} vs {match.get('team2')}) outside sync window. Skipping.\033[0m")
            continue

        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[94mNEXUS: Syncing {match_id} ({match.get('team1')} vs {match.get('team2')}) via API CID {c_id}\033[0m")
        
        # We synchronize both innings (1 and 2) if they exist
        for inn_id in [1, 2]:
            score_update = await sync_innings_data(db, match_id, inn_id)
            
            if score_update:
                # Update main match status with the latest score from the sync
                await db.matches.update_one(
                    {"match_id": match_id},
                    {"$set": {
                        "current_score": score_update["current_score"],
                        "current_over": score_update["current_over"],
                        "innings": score_update["innings"],
                        "status": "LIVE"
                    }}
                )
                
                # Check for 20th over completion to trigger scoring
                current_over_data = await db.live_match_overs.find_one({
                    "match_id": match_id, "session_id": inn_id, "over": 20
                })
                if current_over_data and is_over_complete(current_over_data.get("balls", [])):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[95mNEXUS AUTO-SCORE: Innings {inn_id} complete for {match_id}. Triggering distribution...\033[0m")
                    await calculate_all_sessions_for_match(db, match_id)

    client_db.close()

async def continuously_poll():
    print("\n\033[96m====================================================\033[0m")
    print("\033[96m NEXUS API SURVEILLANCE & RECOVERY ENGINE ACTIVE   \033[0m")
    print("\033[96m [API-Sync] [Recursive-Backfill] [Gap-Correction]  \033[0m")
    print("\033[96m====================================================\033[0m\n")
    while True:
        await run_cricbuzz_pulse()
        await asyncio.sleep(60)

if __name__ == "__main__":
    try: asyncio.run(continuously_poll())
    except KeyboardInterrupt: print("\n\033[91mNEXUS: Terminated.\033[0m")
