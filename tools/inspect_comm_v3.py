import httpx
import asyncio
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_commentary_v3(match_id):
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        data = res.json()
        
        # 1. Match Header (Toss & Status)
        header = data.get("matchHeader") or {}
        print("\n=== MATCH HEADER ===")
        print(f"Match: {header.get('team1', {}).get('shortName')} vs {header.get('team2', {}).get('shortName')}")
        print(f"Status: {header.get('status')}")
        print(f"State: {header.get('state')}")
        print(f"Toss: {header.get('toss')}")
        
        # 2. Miniscore
        miniscore = data.get("miniscore") or {}
        bat_team_score = miniscore.get('batTeamScoreObj') or {}
        print("\n=== MINISCORE ===")
        print(f"Score Box: {bat_team_score.get('score', '0')}/{bat_team_score.get('wickets', '0')} ({miniscore.get('overs', '0.0')})")
        print(f"Latest Performance: {miniscore.get('latestPerformance')}")
        
        # 3. Commentary (Check for Toss result in text)
        match_comm = data.get("matchCommentary") or {}
        comm_list = match_comm.get("commList") or []
        print(f"\nSearching recent {len(comm_list)} commentary for toss info...")
        for comm in comm_list:
            text = comm.get('commText', '')
            if 'toss' in text.lower() or 'opted to' in text.lower():
                print(f"Found: {text[:100]}...")

if __name__ == "__main__":
    # Today's CID: CSK vs PBKS (149684)
    asyncio.run(inspect_commentary_v3("149684"))
