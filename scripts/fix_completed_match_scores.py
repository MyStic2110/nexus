"""
fix_completed_match_scores.py
─────────────────────────────
ONE-TIME BACKFILL: Re-fetches the final scorecard for every COMPLETED match
from the Cricbuzz API and re-assigns team1_final_score / team2_final_score
using batTeamName (not inningsId).

Root Cause Fixed:
    The auto_agent_cricbuzz.py was mapping inningsId==1 → team1_final_score
    and inningsId==2 → team2_final_score.  inningsId reflects BATTING ORDER
    (decided by toss), NOT the team1/team2 ordering in the database.
    If team2 batted first, their score was stored in team1_final_score, and
    both scores were displayed against the wrong team on the UI.

Run once:
    python -m scripts.fix_completed_match_scores
"""

import asyncio
import os
import sys
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
    'Accept': 'application/json'
}
CRICBUZZ_COMM_API = "https://m.cricbuzz.com/api/mcenter/comm"


def find_score_for_team(team_name: str, innings_score_by_team: dict) -> str:
    """
    Lookup team score by name. Falls back to substring matching for
    short-name (e.g. 'RCB') vs full-name ('ROYAL CHALLENGERS BENGALURU').
    """
    if not team_name:
        return ""
    key = team_name.strip().upper()
    if key in innings_score_by_team:
        return innings_score_by_team[key]
    for api_name, score in innings_score_by_team.items():
        if api_name in key or key in api_name:
            return score
    return ""


async def fix_all_completed_matches():
    raw_uri = settings.MONGO_URI.strip().strip("'").strip('"')
    client_db = AsyncIOMotorClient(raw_uri)
    db = client_db[settings.DB_NAME]

    cursor = db.matches.find({"status": "COMPLETED"})
    completed = await cursor.to_list(100)

    if not completed:
        print("[FIX] No COMPLETED matches found — nothing to do.")
        client_db.close()
        return

    print(f"[FIX] Found {len(completed)} COMPLETED matches to verify/repair.\n")

    async with httpx.AsyncClient() as http:
        for match in completed:
            match_id = match.get("match_id")
            c_id = match.get("cricbuzz_id")
            db_t1 = (match.get("team1") or "").strip().upper()
            db_t2 = (match.get("team2") or "").strip().upper()
            db_t1_full = (match.get("team1_full") or "").strip().upper()
            db_t2_full = (match.get("team2_full") or "").strip().upper()

            if not c_id:
                print(f"  [SKIP] {match_id} — no cricbuzz_id, skipping.")
                continue

            print(f"  [PROCESSING] {match_id}  ({match.get('team1')} vs {match.get('team2')})")

            try:
                resp = await http.get(
                    f"{CRICBUZZ_COMM_API}/{c_id}",
                    headers=HEADERS,
                    timeout=12.0
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"    [ERROR] Could not fetch from API: {e}")
                continue

            header    = data.get("matchHeader") or {}
            miniscore = data.get("miniscore") or {}

            official_status = header.get("status", "")
            winning_team    = header.get("result", {}).get("winningTeam", "")

            score_details = miniscore.get("matchScoreDetails") or {}
            inn_list      = score_details.get("inningsScoreList") or []

            if not inn_list:
                print(f"    [WARN] No inningsScoreList returned — skipping.")
                continue

            # Build name-keyed score map
            innings_score_by_team = {}
            for inn in inn_list:
                bat_team_name = (inn.get("batTeamName") or "").strip().upper()
                if bat_team_name:
                    s = f"{inn.get('score')}/{inn.get('wickets')} ({inn.get('overs')})"
                    innings_score_by_team[bat_team_name] = s

            # Improved score matching logic
            def find_score_for_team_improved(short_name, full_name):
                if not short_name and not full_name: return ""
                if short_name in innings_score_by_team: return innings_score_by_team[short_name]
                if full_name in innings_score_by_team: return innings_score_by_team[full_name]
                for api_name, score in innings_score_by_team.items():
                    if api_name in full_name or full_name in api_name or (short_name and short_name in api_name):
                        return score
                return ""

            t1_score_str = find_score_for_team_improved(db_t1, db_t1_full)
            t2_score_str = find_score_for_team_improved(db_t2, db_t2_full)

            # Normalize winner_team
            db_winner = None
            if winning_team:
                wt_upper = winning_team.strip().upper()
                if wt_upper == db_t1 or (db_t1_full and wt_upper == db_t1_full) or (db_t1_full and db_t1_full in wt_upper) or (wt_upper in db_t1_full):
                    db_winner = match.get('team1')
                elif wt_upper == db_t2 or (db_t2_full and wt_upper == db_t2_full) or (db_t2_full and db_t2_full in wt_upper) or (wt_upper in db_t2_full):
                    db_winner = match.get('team2')
                else:
                    db_winner = winning_team

            # Compare with what is currently stored
            old_t1 = match.get("team1_final_score", "")
            old_t2 = match.get("team2_final_score", "")
            old_winner = match.get("winner_team", "")

            if old_t1 == t1_score_str and old_t2 == t2_score_str and old_winner == db_winner:
                print(f"    [OK]  Scores & winner already correct — no update needed.")
                continue

            print(f"    [FIX] {db_t1}: {old_t1!r} → {t1_score_str!r}")
            print(f"    [FIX] {db_t2}: {old_t2!r} → {t2_score_str!r}")
            print(f"    [FIX] Winner: {old_winner!r} → {db_winner!r}")

            await db.matches.update_one(
                {"match_id": match_id},
                {"$set": {
                    "team1_final_score": t1_score_str,
                    "team2_final_score": t2_score_str,
                    "api_status":        official_status,
                    "winner_team":       db_winner,
                }}
            )
            print(f"    [DONE] DB updated for {match_id}.")

    print("\n[FIX] All completed matches processed.")
    client_db.close()


if __name__ == "__main__":
    asyncio.run(fix_all_completed_matches())
