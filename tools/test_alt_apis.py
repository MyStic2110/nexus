import httpx
import asyncio
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_scorecard(match_id):
    # Potential Scorecard endpoint
    url = f"https://m.cricbuzz.com/api/mcenter/scorecard/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            print(f"Scorecard keys for {match_id}:", data.keys())
            # Save for inspection
            with open("tmp/scorecard_inspect.json", "w") as f:
                json.dump(data, f, indent=4)
        else:
            print(f"Scorecard endpoint failed with status {res.status_code}")

async def inspect_graphs(match_id):
    # Potential Graphs endpoint
    url = f"https://m.cricbuzz.com/api/mcenter/graphs/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            print(f"Graphs keys for {match_id}:", data.keys())
        else:
            print(f"Graphs endpoint failed with status {res.status_code}")

if __name__ == "__main__":
    asyncio.run(inspect_scorecard("149618"))
    asyncio.run(inspect_graphs("149618"))
