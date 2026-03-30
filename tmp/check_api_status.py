import httpx
import asyncio
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def main():
    cid = "149640"
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{cid}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=HEADERS)
            data = res.json()
            header = data.get("matchHeader", {})
            print(f"Match: {header.get('team1', {}).get('name')} vs {header.get('team2', {}).get('name')}")
            print(f"State: {header.get('state')}")
            print(f"Status: {header.get('status')}")
            
            miniscore = data.get("miniscore", {})
            print(f"Miniscore State: {miniscore.get('matchScoreDetails', {}).get('state')}")
            print(f"Current Innings: {miniscore.get('matchScoreDetails', {}).get('inningsId')}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
