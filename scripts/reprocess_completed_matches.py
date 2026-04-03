import asyncio
import os
import sys
import httpx
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
    'Accept': 'application/json'
}
CRICBUZZ_COMM_API = "https://m.cricbuzz.com/api/mcenter/comm"

def find_score_for_team(innings_score_by_team, short_name, full_name, opponent_short, opponent_full):
    if short_name in innings_score_by_team: return innings_score_by_team[short_name]
    if full_name in innings_score_by_team: return innings_score_by_team[full_name]
    
    best_match = None
    for api_name, score in innings_score_by_team.items():
        if api_name == short_name or api_name == full_name or short_name in api_name or api_name in full_name:
            if api_name == opponent_short or api_name == opponent_full:
                continue
            best_match = score
            break
    return best_match or ""

async def reprocess():
    raw_uri = settings.MONGO_URI.strip().strip("'").strip('"')
    client_db = AsyncIOMotorClient(raw_uri)
    db = client_db[settings.DB_NAME]
    
    cursor = db.matches.find({"status": "COMPLETED"})
    completed_matches = await cursor.to_list(100)
    
    if not completed_matches:
        print("[REPROCESS] No COMPLETED matches found.")
        client_db.close()
        return

    print(f"[REPROCESS] Found {len(completed_matches)} COMPLETED matches. Verifying scores...")

    async with httpx.AsyncClient() as http:
        for match in completed_matches:
            match_id = match.get("match_id")
            c_id = match.get("cricbuzz_id")
            db_t1 = (match.get('team1') or "").strip().upper()
            db_t2 = (match.get('team2') or "").strip().upper()
            db_t1_f = (match.get('team1_full') or "").strip().upper()
            db_t2_f = (match.get('team2_full') or "").strip().upper()

            if not c_id: continue

            try:
                resp = await http.get(f"{CRICBUZZ_COMM_API}/{c_id}", headers=HEADERS, timeout=10)
                data = resp.json()
                miniscore = data.get("miniscore") or {}
                inn_list = miniscore.get("matchScoreDetails", {}).get("inningsScoreList") or []
                header = data.get("matchHeader") or {}
                winning_team = header.get("result", {}).get("winningTeam")
                official_status = header.get("status")

                innings_score_by_team = {}
                for inn in inn_list:
                    bat_team_name = (inn.get('batTeamName') or "").strip().upper()
                    if bat_team_name:
                        innings_score_by_team[bat_team_name] = f"{inn.get('score')}/{inn.get('wickets')} ({inn.get('overs')})"

                new_t1_score = find_score_for_team(innings_score_by_team, db_t1, db_t1_f, db_t2, db_t2_f)
                new_t2_score = find_score_for_team(innings_score_by_team, db_t2, db_t2_f, db_t1, db_t1_f)

                # Normalize winner
                db_winner = None
                if winning_team:
                    wt_upper = winning_team.strip().upper()
                    if wt_upper == db_t1 or wt_upper == db_t1_f or db_t1_f in wt_upper or wt_upper in db_t1_f:
                        db_winner = match.get('team1')
                    elif wt_upper == db_t2 or wt_upper == db_t2_f or db_t2_f in wt_upper or wt_upper in db_t2_f:
                        db_winner = match.get('team2')
                    else:
                        db_winner = winning_team

                old_t1_score = match.get("team1_final_score")
                old_t2_score = match.get("team2_final_score")
                old_winner = match.get("winner_team")

                if new_t1_score != old_t1_score or new_t2_score != old_t2_score or db_winner != old_winner:
                    print(f"  [FIXING] {match_id}:")
                    print(f"    T1: {old_t1_score} -> {new_t1_score}")
                    print(f"    T2: {old_t2_score} -> {new_t2_score}")
                    print(f"    Winner: {old_winner} -> {db_winner}")
                    
                    await db.matches.update_one(
                        {"match_id": match_id},
                        {"$set": {
                            "team1_final_score": new_t1_score,
                            "team2_final_score": new_t2_score,
                            "winner_team": db_winner,
                            "api_status": official_status
                        }}
                    )
                else:
                    print(f"  [OK] {match_id} scores are correct.")

            except Exception as e:
                print(f"  [ERROR] {match_id}: {e}")

    print("[REPROCESS] Finished.")
    client_db.close()

if __name__ == "__main__":
    asyncio.run(reprocess())
