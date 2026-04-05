import httpx
import asyncio
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_points_table(series_id):
    url = f"https://m.cricbuzz.com/api/series/{series_id}/points-table"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            print(f"Points Table keys for Series {series_id}:", data.keys())
            
            # Save for inspection
            temp_path = os.path.join(os.getcwd(), "tmp", f"points_table_{series_id}.json")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Saved to {temp_path}")
            
            # Print first entry overview
            points_table = data.get("pointsTable", [])
            if points_table:
                groups = points_table[0].get("pointsTableInfo", [])
                for team in groups[:3]:
                    print(f"Team: {team.get('teamName')} | P: {team.get('points')} | NRR: {team.get('nrr')}")
        else:
            print(f"Points Table endpoint failed with status {res.status_code}")

if __name__ == "__main__":
    asyncio.run(inspect_points_table("9241"))
