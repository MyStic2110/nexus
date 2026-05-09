import asyncio
import httpx
import os
from dotenv import load_dotenv

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
    'Accept': 'application/json'
}

async def debug_mapping():
    c_id = "149618"
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{c_id}"
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        data = res.json()
        
        miniscore = data.get("miniscore") or {}
        score_details = miniscore.get("matchScoreDetails") or {}
        inn_list = score_details.get("inningsScoreList") or []
        
        # 1. Build map
        innings_score_by_team = {}
        for inn in inn_list:
            bat_team_name = (inn.get('batTeamName') or "").strip().upper()
            if bat_team_name:
                s = f"{inn.get('score')}/{inn.get('wickets')} ({inn.get('overs')})"
                innings_score_by_team[bat_team_name] = s
        
        print("Innings Score Map:", innings_score_by_team)
        
        # 2. Match teams
        db_t1 = "RCB"
        db_t1_full = "ROYAL CHALLENGERS BENGALURU"
        db_t2 = "SRH"
        db_t2_full = "SUNRISERS HYDERABAD"
        
        def find_score_for_team(short_name, full_name):
            if not short_name and not full_name: return ""
            if short_name in innings_score_by_team: 
                print(f"Matched {short_name} directly")
                return innings_score_by_team[short_name]
            if full_name in innings_score_by_team: 
                print(f"Matched {full_name} directly")
                return innings_score_by_team[full_name]
            for api_name, score in innings_score_by_team.items():
                if api_name in full_name or full_name in api_name or (short_name and short_name in api_name):
                    print(f"Matched {api_name} via partial/substring matching")
                    return score
            return ""

        t1_score = find_score_for_team(db_t1, db_t1_full)
        t2_score = find_score_for_team(db_t2, db_t2_full)
        
        print(f"Result -> T1 (RCB): {t1_score}, T2 (SRH): {t2_score}")

if __name__ == "__main__":
    asyncio.run(debug_mapping())
