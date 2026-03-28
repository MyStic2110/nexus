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

# Global counter for sequential failures
over_data_failure_count = 0

def detect_innings(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    if '2nd Inn' in text or '2nd innings' in text.lower():
        return 2
    return 1

def parse_over_block(block):
    cols = block.find_all('div', class_=lambda c: c and 'p-4' in c and 'border-r' in c, recursive=False)
    if len(cols) < 3: return None
    
    col1_text = cols[0].get_text(separator=' ', strip=True)
    over_match = re.search(r'Ov\s*(\d+)', col1_text)
    score_match = re.search(r'(\d+)-(\d+)', col1_text)
    if not over_match or not score_match: return None
    
    over_num = int(over_match.group(1))
    cumulative_runs = score_match.group(1)
    cumulative_wickets = score_match.group(2)
    
    balls_container = cols[1].find('div', class_=lambda c: c and 'flex' in c and 'gap-2' in c and 'flex-wrap' in c)
    if not balls_container: return None
    
    ball_divs = balls_container.find_all('div', recursive=False)
    balls = []
    total_runs_from_balls = 0
    for bd in ball_divs:
        val = bd.get_text(strip=True)
        if val == '\u2022' or val == '': balls.append('0')
        elif val == 'W': balls.append('W')
        elif val in ['Wd', 'Nb']:
            balls.append(val)
            total_runs_from_balls += 1
        elif val.isdigit():
            balls.append(val)
            total_runs_from_balls += int(val)
    
    if not balls: return None
    
    col3_text = cols[2].get_text(strip=True)
    try: over_total_runs = int(col3_text)
    except: over_total_runs = total_runs_from_balls
    
    return {
        "over": over_num, "balls": balls, "total_runs": over_total_runs,
        "current_score": f"{cumulative_runs}/{cumulative_wickets}",
        "current_over": float(over_num)
    }

def extract_all_overs(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    over_blocks = soup.find_all('div', class_=lambda c: c and 'grid-cols-[1.2fr_7.3fr_1.5fr]' in c)
    results = []
    for block in over_blocks:
        parsed = parse_over_block(block)
        if parsed: results.append(parsed)
    return results

async def handle_summary_fallback(db, match_id, summary_url):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[93mNEXUS FALLBACK: Polling {summary_url}...\033[0m")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(summary_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            page_text = BeautifulSoup(response.text, 'html.parser').get_text(separator=' ', strip=True)
            
            status_update = {}
            result_match = re.search(r'([A-Za-z ]+ won by \d+ [A-Za-z]+)', page_text)
            if result_match:
                status_update["status"] = "COMPLETED"
                status_update["api_status"] = result_match.group(1).strip()
            
            scores = re.findall(r'([A-Z]{2,4})\s+(\d+/\d+)\s*\((\d+\.?\d*)\)', page_text)
            if scores:
                latest_team, latest_score, latest_over = scores[-1]
                status_update["current_score"] = latest_score
                status_update["current_over"] = float(latest_over)
                status_update["innings"] = len(scores)

            if status_update:
                await db.matches.update_one({"match_id": match_id}, {"$set": status_update})
                print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[92mNEXUS FALLBACK: Updated {match_id} status/score.\033[0m")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[91mNexus Fallback failed: {e}\033[0m")

async def run_cricbuzz_pulse():
    global over_data_failure_count
    client_db = AsyncIOMotorClient(MONGO_URI)
    db = client_db.ipl_game
    match_data_collection = db["live_match_overs"]
    
    # Dynamic Match Discovery: Find matches that are LIVE or UPCOMING today
    ist_date = datetime.now().strftime("%Y-%m-%d")
    cursor = db.matches.find({"$or": [{"status": "LIVE"}, {"date": ist_date}]})
    active_matches = await cursor.to_list(10)
    
    if not active_matches:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[90mNEXUS: No active matches found for {ist_date}\033[0m")
        client_db.close()
        return

    async with httpx.AsyncClient() as client:
        for match in active_matches:
            c_id = match.get("cricbuzz_id")
            if not c_id: continue
            
            over_url = f"https://m.cricbuzz.com/live-cricket-over-by-over/{c_id}/match-slug"
            summary_url = f"https://m.cricbuzz.com/live-cricket-scores/{c_id}/match-slug"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[94mNEXUS: Syncing {match['match_id']} ({match['team1']} vs {match['team2']}) via CID {c_id}\033[0m")
            
            try:
                response = await client.get(over_url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()
                all_overs = extract_all_overs(response.text)
                
                if not all_overs:
                    over_data_failure_count += 1
                    if over_data_failure_count >= 20:
                        await handle_summary_fallback(db, match["match_id"], summary_url)
                        over_data_failure_count = 0
                    continue

                over_data_failure_count = 0
                db_innings = match.get("innings", 1)
                session_id = max(detect_innings(response.text), db_innings)
                
                for over_data in all_overs:
                    over_data["match_id"] = match["match_id"]
                    over_data["session_id"] = session_id
                    existing = await match_data_collection.find_one({"match_id": match["match_id"], "session_id": session_id, "over": over_data["over"]})
                    if not (existing and len([b for b in existing.get("balls", []) if b not in ['Wd', 'Nb']]) >= 6):
                        await match_data_collection.update_one({"match_id": match["match_id"], "session_id": session_id, "over": over_data["over"]}, {"$set": over_data}, upsert=True)
                
                await db.matches.update_one({"match_id": match["match_id"]}, {"$set": {"current_score": all_overs[0]["current_score"], "current_over": all_overs[0]["current_over"], "innings": session_id, "status": "LIVE"}})
                
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] \033[91mPulse failed for {match['match_id']}: {e}\033[0m")

    client_db.close()

async def continuously_poll():
    print("\n\033[96m====================================================\033[0m")
    print("\033[96m NEXUS MULTI-MATCH SURVEILLANCE ENGINE V3 ACTIVE    \033[0m")
    print("\033[96m====================================================\033[0m\n")
    while True:
        await run_cricbuzz_pulse()
        await asyncio.sleep(60)

if __name__ == "__main__":
    try: asyncio.run(continuously_poll())
    except KeyboardInterrupt: print("\n\033[91mNEXUS: Terminated.\033[0m")
