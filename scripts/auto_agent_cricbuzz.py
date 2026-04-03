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
CRICBUZZ_COMM_API = "https://m.cricbuzz.com/api/mcenter/comm"
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
        if not response.text:
            return None
        return response.json()
    except ValueError as e:
        # Match likely not started, over-by-over returns non-JSON empty string or HTML 404
        return None
    except Exception as e:
        print(f"[API-FETCH] Error fetching {url}: {e}")
        return None

async def get_match_data_from_api(client, match_id):
    """Fetches full match data (header and miniscore) from the Commentary API."""
    url = f"{CRICBUZZ_COMM_API}/{match_id}"
    try:
        response = await client.get(url, headers=HEADERS, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[API-DATA] Error fetching data for {match_id}: {e}")
        return {}

async def sync_innings_data(db, match_id, innings_id, client):
    """
    Recursively fetches and persists all overs for an innings using the API.
    Ensures no gaps exist in the database.
    """
    match_data_collection = db["live_match_overs"]
    history_collection = db["match_over_history"]
    
    # Check CID from match_id first to use in API calls
    match_doc = await db.matches.find_one({"match_id": match_id})
    c_id = match_doc.get("cricbuzz_id")
    if not c_id: return None

    current_timestamp = None
    has_more = True
    total_recovered = 0
    latest_score_data = None

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
            
            if latest_score_data is None:
                current_runs = ovr_item.get("score", 0)
                current_wickets = ovr_item.get("wickets", 0)
                latest_score_data = {
                    "current_score": f"{current_runs}/{current_wickets}",
                    "current_over": float(over_num),
                    "innings": innings_id,
                    "live_stats": {
                        "bat_striker": {
                            "name": ovr_item.get("batStrikerNames", [""])[-1] if ovr_item.get("batStrikerNames") else "",
                            "runs": ovr_item.get("batStrikerRuns", 0),
                            "balls": ovr_item.get("batStrikerBalls", 0)
                        },
                        "bat_non_striker": {
                            "name": ovr_item.get("batNonStrikerNames", [""])[-1] if ovr_item.get("batNonStrikerNames") else "",
                            "runs": ovr_item.get("batNonStrikerRuns", 0),
                            "balls": ovr_item.get("batNonStrikerBalls", 0)
                        },
                        "bowler": {
                            "name": ovr_item.get("bowlNames", [""])[-1] if ovr_item.get("bowlNames") else "",
                            "overs": ovr_item.get("bowlOvers", 0),
                            "maidens": ovr_item.get("bowlMaidens", 0),
                            "runs": ovr_item.get("bowlRuns", 0),
                            "wickets": ovr_item.get("bowlWickets", 0)
                        },
                        "last_over_summary": ovr_item.get("ovrSummary", "")
                    }
                }

            balls = parse_ovr_summary(ovr_item.get('ovrSummary', ''))
            
            existing_balls = await get_existing_balls(match_data_collection, match_id, innings_id, over_num)
            if over_num not in set(await match_data_collection.distinct("over", {"match_id": match_id, "session_id": innings_id})) or not is_over_complete(existing_balls):
                current_runs = ovr_item.get("score", 0)
                current_wickets = ovr_item.get("wickets", 0)
                over_record = {
                    "match_id": match_id,
                    "session_id": innings_id,
                    "over": over_num,
                    "balls": balls,
                    "total_runs": ovr_item.get("runs", 0),
                    "current_score": f"{current_runs}/{current_wickets}",
                    "current_over": float(over_num),
                    "timestamp": ovr_item.get("timestamp"),
                    "bat_striker": ovr_item.get("batStrikerNames"),
                    "bat_striker_runs": ovr_item.get("batStrikerRuns"),
                    "bat_striker_balls": ovr_item.get("batStrikerBalls"),
                    "bowl_name": ovr_item.get("bowlNames"),
                    "bowl_wickets": ovr_item.get("bowlWickets"),
                    "bowl_runs": ovr_item.get("bowlRuns")
                }
                
                await match_data_collection.update_one(
                    {"match_id": match_id, "session_id": innings_id, "over": over_num},
                    {"$set": over_record},
                    upsert=True
                )

                # Store full raw detail in history collection as requested
                history_record = {
                    "match_id": match_id,
                    "cricbuzz_id": c_id,
                    "session_id": innings_id,
                    "over": over_num,
                    "raw_data": ovr_item,
                    "synced_at": datetime.now(IST)
                }
                await history_collection.update_one(
                    {"match_id": match_id, "session_id": innings_id, "over": over_num},
                    {"$set": history_record},
                    upsert=True
                )
                total_recovered += 1

        next_url = data.get('nextPaginationURL')
        if next_url:
            parts = [p for p in next_url.strip('/').split('/') if p]
            if len(parts) >= 5:
                current_timestamp = parts[-1]
            else:
                has_more = False
        else:
            has_more = False

        if 1 in set(await match_data_collection.distinct("over", {"match_id": match_id, "session_id": innings_id})):
            max_over = max(await match_data_collection.distinct("over", {"match_id": match_id, "session_id": innings_id}))
            gaps = [o for o in range(1, max_over + 1) if o not in set(await match_data_collection.distinct("over", {"match_id": match_id, "session_id": innings_id}))]
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
    """Always return True to allow syncing today's matches."""
    return True

async def run_cricbuzz_pulse():
    raw_uri = settings.MONGO_URI.strip().strip("'").strip('"')
    
    if not raw_uri or not (raw_uri.startswith("mongodb://") or raw_uri.startswith("mongodb+srv://")):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[91mNEXUS ERROR: Invalid MONGO_URI\033[0m")
        return

    try:
        client_db = AsyncIOMotorClient(raw_uri)
        db = client_db[DB_NAME]
        # Ensure indexes for the history collection
        await db.match_over_history.create_index(
            [("match_id", 1), ("session_id", 1), ("over", 1)],
            unique=True
        )
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
        
        async with httpx.AsyncClient() as client:
            # ─── DYNAMIC STATUS CHECK ───
            data = await get_match_data_from_api(client, c_id)
            header = data.get("matchHeader") or {}
            miniscore = data.get("miniscore") or {}
            
            match_state = header.get("state")
            official_status = header.get("status")
            winning_team = header.get("result", {}).get("winningTeam")
            
            # Extract Individual Innings Scores
            # FIX: Use batTeamName to assign scores correctly — NOT inningsId.
            # inningsId is batting ORDER (determined by toss), NOT the DB team order.
            # If team2 bats first, their score was wrongly stored in team1_final_score.
            score_details = miniscore.get("matchScoreDetails") or {}
            inn_list = score_details.get("inningsScoreList") or []
            
            # Build a name-indexed score map from the API
            innings_score_by_team = {}  # { "KKR": "220/4 (20)", "MI": "224/4 (19.1)" }
            for inn in inn_list:
                bat_team_name = (inn.get('batTeamName') or "").strip().upper()
                if bat_team_name:
                    s = f"{inn.get('score')}/{inn.get('wickets')} ({inn.get('overs')})"
                    innings_score_by_team[bat_team_name] = s
            
            # Now look up team1/team2 from the DB record and match to their score
            db_t1 = (match.get('team1') or "").strip().upper()
            db_t2 = (match.get('team2') or "").strip().upper()
            db_t1_full = (match.get('team1_full') or "").strip().upper()
            db_t2_full = (match.get('team2_full') or "").strip().upper()
            
            def find_score_for_team(short_name, full_name, opponent_short, opponent_full):
                # 1. Exact matches (highest priority)
                if short_name in innings_score_by_team: return innings_score_by_team[short_name]
                if full_name in innings_score_by_team: return innings_score_by_team[full_name]
                
                # 2. Heuristic: Find a key in innings_score_by_team that BEST matches this team
                # and DOES NOT match the opponent better.
                best_match = None
                for api_name, score in innings_score_by_team.items():
                    # If api_name matches our short_name or full_name
                    if api_name == short_name or api_name == full_name or short_name in api_name or api_name in full_name:
                        # Double check it doesn't match opponent's full name better
                        if api_name == opponent_short or api_name == opponent_full:
                            continue
                        best_match = score
                        break
                return best_match or ""

            t1_score_str = find_score_for_team(db_t1, db_t1_full, db_t2, db_t2_full)
            t2_score_str = find_score_for_team(db_t2, db_t2_full, db_t1, db_t1_full)
            
            # CRITICAL LOGGING: To debut interchanged scores
            print(f"[{datetime.now().strftime('%H:%M:%S')}] NEXUS MAP: DB({db_t1}/{db_t1_full}) -> {t1_score_str} | DB({db_t2}/{db_t2_full}) -> {t2_score_str}")

            if match_state == "Complete":
                # Normalize winner_team to short name for frontend highlighting
                db_winner = None
                if winning_team:
                    wt_upper = winning_team.strip().upper()
                    if wt_upper == db_t1 or (db_t1_full and wt_upper == db_t1_full) or (db_t1_full and db_t1_full in wt_upper) or (wt_upper in db_t1_full):
                        db_winner = match.get('team1')
                    elif wt_upper == db_t2 or (db_t2_full and wt_upper == db_t2_full) or (db_t2_full and db_t2_full in wt_upper) or (wt_upper in db_t2_full):
                        db_winner = match.get('team2')
                    else:
                        db_winner = winning_team # Fallback (draws, unknown results)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[92mNEXUS: Match {match_id} officially COMPLETE. Winner: {db_winner}. Recording scores & closing.\033[0m")
                await db.matches.update_one(
                    {"match_id": match_id},
                    {"$set": {
                        "status": "COMPLETED",
                        "api_status": official_status,
                        "team1_final_score": t1_score_str,
                        "team2_final_score": t2_score_str,
                        "winner_team": db_winner
                    }}
                )
                # Final backfill for both innings
                await sync_innings_data(db, match_id, 1, client)
                await sync_innings_data(db, match_id, 2, client)
                
                # Trigger point distribution for completed match
                print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[95mNEXUS AUTO-SCORE: Match {match_id} completed. Triggering final distribution...\033[0m")
                await calculate_all_sessions_for_match(db, match_id)
                continue

            # Extract state and only sync if relevant
            match_state = header.get("state")
            if match_state not in ["Live", "Complete", "In Progress"]:
                 print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[90mNEXUS: Match {match_id} state is '{match_state}'. Skipping over-by-over sync.\033[0m")
                 continue

            # We synchronize both innings (1 and 2) if they exist
            latest_score_data = None
            for inn_id in [1, 2]:
                score_update = await sync_innings_data(db, match_id, inn_id, client)
                if score_update:
                    latest_score_data = score_update
            
            if latest_score_data:
                # Update main match status with the latest score from the sync
                await db.matches.update_one(
                    {"match_id": match_id},
                    {"$set": {
                        "current_score": latest_score_data["current_score"],
                        "current_over": latest_score_data["current_over"],
                        "innings": latest_score_data["innings"],
                        "live_stats": latest_score_data.get("live_stats"),
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
