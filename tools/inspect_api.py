import httpx
import asyncio
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_comm_api(match_id):
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        data = res.json()
        
        header = data.get("matchHeader", {})
        miniscore = data.get("miniscore", {})
        score_details = miniscore.get("matchScoreDetails", {})
        inn_list = score_details.get("inningsScoreList", [])
        
        print(f"Match: {header.get('team1', {}).get('shortName')} vs {header.get('team2', {}).get('shortName')}")
        print(f"Result: {header.get('result', {}).get('winningTeam')}")
        print(f"Match Status: {header.get('status')}")
        print("\nInnings Score List Metadata:")
        for inn in inn_list:
            print(f"  Innings ID: {inn.get('inningsId')}")
            print(f"  Bat Team Name: {inn.get('batTeamName')}")
            print(f"  Score: {inn.get('score')}/{inn.get('wickets')} ({inn.get('overs')})")
            print("-" * 15)

if __name__ == "__main__":
    asyncio.run(inspect_comm_api("149618"))
