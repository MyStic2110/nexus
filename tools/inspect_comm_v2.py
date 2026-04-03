import httpx
import asyncio
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_commentary_v2(match_id):
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        data = res.json()
        
        # matchCommentary might be a list or object
        match_comm = data.get("matchCommentary", {})
        comm_list = match_comm.get("commList", [])
        print(f"\nFound {len(comm_list)} commentary entries.")
        for i, comm in enumerate(comm_list[:5]):
            print(f"[{i}] {comm.get('commText')}")
            
        miniscore = data.get("miniscore", {})
        print("\nMiniscore stats keys:", miniscore.keys())
        
        for key in ['batsmanStriker', 'batsmanNonStriker', 'bowlerStriker', 'bowlerNonStriker']:
            val = miniscore.get(key)
            if val:
                print(f"\n{key}: {val}")
        
        print(f"\nlatestPerformance: {miniscore.get('latestPerformance')}")
        print(f"\nrecentOvsStats: {miniscore.get('recentOvsStats')}")

if __name__ == "__main__":
    asyncio.run(inspect_commentary_v2("149618"))
