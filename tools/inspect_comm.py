import httpx
import asyncio
import json
import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

async def inspect_commentary(match_id):
    url = f"https://m.cricbuzz.com/api/mcenter/comm/{match_id}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS)
        data = res.json()
        
        # Save to temp file
        temp_path = os.path.join(os.getcwd(), "tmp", "full_comm_data.json")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=4)
            
        print("Root level keys:", data.keys())
        
        comm_list = data.get("commList", [])
        print(f"\nFound {len(comm_list)} commentary entries.")
        for i, comm in enumerate(comm_list[:3]):
            print(f"[{i}] {comm.get('commText')}")
            
        miniscore = data.get("miniscore", {})
        print("\nMiniscore stats keys:", miniscore.keys())
        
        batsman = miniscore.get("batsman", [])
        print("\nBatsman Info:")
        for b in batsman:
            print(f"  {b.get('name')}: R={b.get('runs')} B={b.get('balls')} SR={b.get('strikeRate')}")
            
        bowler = miniscore.get("bowler", [])
        print("\nBowler Info:")
        for b in bowler:
            print(f"  {b.get('name')}: O={b.get('overs')} M={b.get('maidens')} R={b.get('runs')} W={b.get('wickets')}")

if __name__ == "__main__":
    # Test with Match 1 CID
    asyncio.run(inspect_commentary("149618"))
