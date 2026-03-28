import httpx
from app.config import settings

async def fetch_last_2_overs(match_id: str):
    url = f"{settings.CRICKET_API_BASE}/match/{match_id}/balls"
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, params={"apikey": settings.CRICKET_API_KEY})
        data = res.json()

    results = []
    for ball in data.get("data", []):
        innings = ball.get("innings")
        over = ball.get("over")
        if over < 18:
            continue
        ball_no = ((over - 18) * 6) + ball.get("ball")
        results.append({
            "innings": innings,
            "ball_number": ball_no,
            "runs": ball.get("runs", 0)
        })
    return results
