import asyncio
import os
import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# The "Over by Over" URL for ball-by-ball details
URL_OVER_BY_OVER = "https://m.cricbuzz.com/live-cricket-over-by-over/149618/rcb-vs-srh-1st-match-indian-premier-league-2026"
# The "Summary" URL for final scores/status
URL_SUMMARY = "https://m.cricbuzz.com/live-cricket-scores/149618/rcb-vs-srh-1st-match-indian-premier-league-2026"

# Counter for sequential failures to find over data
over_data_failure_count = 0

def detect_innings(html_content):
    """Detects current innings from Cricbuzz page. Returns 1 or 2."""
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    if '2nd Inn' in text or '2nd innings' in text.lower():
        return 2
    return 1

def parse_over_block(block):
    """Parse a single over block div into structured data. Returns dict or None."""
    cols = block.find_all('div', class_=lambda c: c and 'p-4' in c and 'border-r' in c, recursive=False)
    if len(cols) < 3:
        return None
    
    col1_text = cols[0].get_text(separator=' ', strip=True)
    over_match = re.search(r'Ov\s*(\d+)', col1_text)
    score_match = re.search(r'(\d+)-(\d+)', col1_text)
    if not over_match or not score_match:
        return None
    
    over_num = int(over_match.group(1))
    cumulative_runs = score_match.group(1)
    cumulative_wickets = score_match.group(2)
    
    balls_container = cols[1].find('div', class_=lambda c: c and 'flex' in c and 'gap-2' in c and 'flex-wrap' in c)
    if not balls_container:
        return None
    
    ball_divs = balls_container.find_all('div', recursive=False)
    balls = []
    total_runs_from_balls = 0
    
    for bd in ball_divs:
        val = bd.get_text(strip=True)
        if val == '\u2022' or val == '':
            balls.append('0')
        elif val == 'W':
            balls.append('W')
        elif val in ['Wd', 'Nb']:
            balls.append(val)
            total_runs_from_balls += 1
        elif val.isdigit():
            balls.append(val)
            total_runs_from_balls += int(val)
    
    if not balls:
        return None
    
    col3_text = cols[2].get_text(strip=True)
    try:
        over_total_runs = int(col3_text)
    except ValueError:
        over_total_runs = total_runs_from_balls
    
    return {
        "over": over_num,
        "balls": balls,
        "total_runs": over_total_runs,
        "current_score": f"{cumulative_runs}/{cumulative_wickets}",
        "current_over": float(over_num)
    }

def extract_all_overs(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    over_blocks = soup.find_all(
        'div',
        class_=lambda c: c and 'grid-cols-[1.2fr_7.3fr_1.5fr]' in c
    )
    
    results = []
    for block in over_blocks:
        parsed = parse_over_block(block)
        if parsed:
            results.append(parsed)
    
    return results

async def handle_summary_fallback(db, match_id):
    """Fallback logic to parse summary page if ball-by-ball is unavailable."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[93mNEXUS FALLBACK: Polling summary page for match status...\033[0m")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(URL_SUMMARY, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Logic to extract score/status from summary page
            # Look for score patterns like "SRH 201/9 (20)" or result strings
            page_text = soup.get_text(separator=' ', strip=True)
            
            # Update match status if result is found
            # Typical Cricbuzz result strings: "Team won by X runs/wickets" or "Match tied"
            result_match = re.search(r'([A-Za-z ]+ won by \d+ [A-Za-z]+)', page_text)
            status_update = {}
            
            if result_match:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[92mNEXUS FALLBACK: Final result detected: {result_match.group(1)}\033[0m")
                status_update["status"] = "COMPLETED"
                status_update["api_status"] = result_match.group(1)
            
            # Extract scores (e.g. SRH 201/9 (20))
            # Pattern: TEAM_NAME SCORE (OVERS)
            scores = re.findall(r'([A-Z]{2,4})\s+(\d+/\d+)\s*\((\d+\.?\d*)\)', page_text)
            if scores:
                # We prioritize the latest score found
                latest_team, latest_score, latest_over = scores[-1]
                status_update["current_score"] = latest_score
                status_update["current_over"] = float(latest_over)
                status_update["innings"] = len(scores)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[92mNEXUS FALLBACK: Latest Score: {latest_team} {latest_score} ({latest_over} ov)\033[0m")

            if status_update:
                await db.matches.update_one({"match_id": match_id}, {"$set": status_update})
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[91mNexus Fallback failed: {e}\033[0m")

async def run_cricbuzz_agent():
    global over_data_failure_count
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[94mNEXUS AGENT: Executing extraction pulse on {URL_OVER_BY_OVER}\033[0m")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(URL_OVER_BY_OVER, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[91mAgent failed to reach source: {e}\033[0m")
            return
    
    client_db = AsyncIOMotorClient(MONGO_URI)
    db = client_db.ipl_game
    match_data_collection = db["live_match_overs"]
    
    cursor = db.matches.find({"$or": [{"team1": "RCB", "team2": "SRH"}, {"team1": "SRH", "team2": "RCB"}]})
    match_record = await cursor.to_list(1)
    
    if not match_record:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[91mNEXUS DB: Match anchor not found.\033[0m")
        client_db.close()
        return
        
    match_id = match_record[0]["match_id"]
    all_overs = extract_all_overs(response.text)
    
    if not all_overs:
        over_data_failure_count += 1
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[93mNEXUS AGENT: No over data found (Seq failure: {over_data_failure_count}/20)\033[0m")
        
        # Fallback Trigger
        if over_data_failure_count >= 20:
            await handle_summary_fallback(db, match_id)
            # Reset counter after fallback attempt to avoid spamming fallback every tick
            over_data_failure_count = 0
            
        client_db.close()
        return
    
    # Success: Reset failure count
    over_data_failure_count = 0
    
    db_innings = match_record[0].get("innings", 1)
    detected_session = detect_innings(response.text)
    session_id = max(detected_session, db_innings)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] \033[95mNEXUS AGENT: Detected Session {detected_session} -> Fixed to Session {session_id} | Found {len(all_overs)} over blocks\033[0m")
    
    inserted = 0
    skipped = 0
    for over_data in all_overs:
        over_data["match_id"] = match_id
        over_data["session_id"] = session_id
        
        existing = await match_data_collection.find_one(
            {"match_id": match_id, "session_id": session_id, "over": over_data["over"]}
        )
        legal_new = [b for b in over_data["balls"] if b not in ['Wd', 'Nb']]
        legal_existing = [b for b in existing.get("balls", []) if b not in ['Wd', 'Nb']] if existing else []
        
        if existing and len(legal_existing) >= 6:
            skipped += 1
        else:
            await match_data_collection.update_one(
                {"match_id": match_id, "session_id": session_id, "over": over_data["over"]},
                {"$set": over_data},
                upsert=True
            )
            inserted += 1
    
    # Update latest score from ball-by-ball
    most_recent = all_overs[0]
    await db.matches.update_one(
        {"match_id": match_id},
        {"$set": {
            "current_score": most_recent["current_score"],
            "current_over": most_recent["current_over"],
            "innings": session_id,
            "status": "LIVE" # Ensure status is live during active collection
        }}
    )
    
    client_db.close()

async def continuously_poll():
    print("\n\033[96m====================================================\033[0m")
    print("\033[96m NEXUS AUTONOMOUS SURVEILLANCE AGENT V2 (FALLBACK) \033[0m")
    print("\033[96m====================================================\033[0m\n")
    while True:
        await run_cricbuzz_agent()
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(continuously_poll())
    except KeyboardInterrupt:
        print("\n\033[91mNEXUS AGENT: Terminated.\033[0m")
