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
        
        # Save to temp file for manual inspection if needed
        temp_path = os.path.join(os.getcwd(), "comm_api_inspect.json")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=4)
            
        print("Match Header Keys:", data.get("matchHeader", {}).keys())
        print("Miniscore Info:")
        miniscore = data.get("miniscore", {})
        print("  State:", miniscore.get("matchScoreDetails", {}).get("state"))
        print("  Inn 1 Score:", miniscore.get("matchScoreDetails", {}).get("innScore1"))
        print("  Inn 2 Score:", miniscore.get("matchScoreDetails", {}).get("innScore2"))
        print("  Custom Status:", miniscore.get("matchScoreDetails", {}).get("customStatus"))

if __name__ == "__main__":
    asyncio.run(inspect_comm_api("149629"))
