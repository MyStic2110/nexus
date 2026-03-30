import asyncio
import os
import sys
import pytz
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to sys.path
sys.path.append(os.getcwd())
from app.config import settings

async def main():
    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.DB_NAME]
        
        IST = pytz.timezone("Asia/Kolkata")
        ist_date = datetime.now(IST).strftime("%Y-%m-%d")
        print(f"Current IST Date: {ist_date}")

        matches = await db.matches.find({"date": ist_date}).to_list(100)
        if not matches:
            print("No matches found for today.")
            # Let's check for any LIVE matches regardless of date
            matches = await db.matches.find({"status": "LIVE"}).to_list(100)
            if matches:
                print("Found LIVE matches (regardless of date):")
            else:
                print("No LIVE matches found either.")
        
        if matches:
            print(f"{'MatchID':<15} | {'CID':<10} | {'Status':<15} | {'Date':<15} | {'Teams':<30}")
            print("-" * 90)
            for m in matches:
                match_id = m.get('match_id', 'N/A')
            cid = m.get('cricbuzz_id', 'N/A')
            status = m.get('status', 'N/A')
            date = m.get('date', 'N/A')
            teams = f"{m.get('team1', 'N/A')} vs {m.get('team2', 'N/A')}"
            print(f"{match_id:<15} | {cid:<10} | {status:<15} | {date:<15} | {teams:<30}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    asyncio.run(main())
