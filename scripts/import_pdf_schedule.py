import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import pdfplumber
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
PDF_PATH = "app/TATA IPL 2026 Season Schedule.pdf"

TEAMS = {
    "Royal Challengers Bengaluru": "RCB",
    "Chennai Super Kings": "CSK",
    "Mumbai Indians": "MI",
    "Kolkata Knight Riders": "KKR",
    "Rajasthan Royals": "RR",
    "Punjab Kings": "PBKS",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG",
    "Delhi Capitals": "DC",
    "Sunrisers Hyderabad": "SRH"
}

def parse_line(line):
    # Example format: '1 28-MAR-26 Sat 7:30 PM Royal Challengers Bengaluru Sunrisers Hyderabad Bengaluru'
    parts = line.split()
    if len(parts) < 6: return None
    
    match_num = parts[0]
    if not match_num.isdigit(): return None
    
    date_str = parts[1]
    day_str = parts[2]
    
    try:
        dt = datetime.strptime(date_str, "%d-%b-%y")
        iso_date = dt.strftime("%Y-%m-%d")
    except ValueError:
        return None
        
    time_str = f"{parts[3]} {parts[4]}"
    rest = " ".join(parts[5:])
    
    found_teams = []
    for full_name in TEAMS.keys():
        idx = rest.find(full_name)
        if idx != -1:
            found_teams.append((idx, full_name))
            
    found_teams.sort(key=lambda x: x[0])
    
    if len(found_teams) >= 2:
        t1_full = found_teams[0][1]
        t2_full = found_teams[1][1]
        
        # Remove team names to get the venue
        venue = rest.replace(t1_full, "").replace(t2_full, "").strip()
        
        # Small format fix
        time_display = time_str if len(time_str.split(':')[0]) == 2 else f"0{time_str}"
        
        # Fix venue spaces
        venue = " ".join(venue.split()) 

        return {
            "match_id": f"ipl_2026_{int(match_num):02d}",
            "date": iso_date,
            "time": time_display,
            "team1": TEAMS[t1_full],
            "team2": TEAMS[t2_full],
            "team1_full": t1_full,
            "team2_full": t2_full,
            "venue": venue,
            "status": "UPCOMING"
        }
    return None

async def ingest_schedule():
    print(f"NEXUS: Opening PDF document {PDF_PATH}...")
    matches_to_insert = []
    
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    # Sometimes the row is a list of lines or single string
                    if not row: continue
                    val = row[0] if isinstance(row, list) else row
                    if val:
                        parsed = parse_line(str(val))
                        if parsed:
                            matches_to_insert.append(parsed)
                            
    print(f"Extraction complete. Found {len(matches_to_insert)} valid match records.")
    
    if matches_to_insert:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.ipl_game
        # Clear existing
        await db.matches.delete_many({})
        print("Database matches collection cleared.")
        
        await db.matches.insert_many(matches_to_insert)
        print("NEXUS: Schedule ingested successfully. The Arena is primed.")
        client.close()
    else:
        print("Error: Could not extract matches.")

if __name__ == "__main__":
    asyncio.run(ingest_schedule())
