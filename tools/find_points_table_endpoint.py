import httpx
import asyncio
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def try_endpoints(series_id):
    endpoints = [
        f"https://m.cricbuzz.com/api/series/{series_id}/points-table",
        f"https://m.cricbuzz.com/api/series/{series_id}/pointsTable",
        f"https://m.cricbuzz.com/api/series/{series_id}/standings",
        f"https://m.cricbuzz.com/api/mcenter/series/{series_id}/points-table",
        f"https://m.cricbuzz.com/api/mcenter/series/{series_id}/pointsTable",
    ]
    
    async with httpx.AsyncClient() as client:
        for url in endpoints:
            print(f"Trying: {url}")
            try:
                res = await client.get(url, headers=HEADERS)
                if res.status_code == 200:
                    print(f"SUCCESS: {url}")
                    data = res.json()
                    # Print keys
                    print(f"Keys: {data.keys()}")
                    # Store success
                    with open(f"tmp/points_table_success.json", "w") as f:
                        json.dump(data, f, indent=4)
                    return url
                else:
                    print(f"Failed with {res.status_code}")
            except Exception as e:
                print(f"Error: {e}")
    return None

if __name__ == "__main__":
    asyncio.run(try_endpoints("9241"))
