import json
from app.db.redis import redis_client
from app.config import settings

async def process_ball(match_id: str, innings: int, ball_no: int, actual_runs: int):
    users = await redis_client.smembers(f"match:{match_id}:users")

    for user in users:
        key = f"match:{match_id}:predictions:{user}"
        data = await redis_client.get(key)
        if not data:
            continue
        predictions = json.loads(data)

        predicted = next(
            (p["runs"] for p in predictions
             if p["innings"] == innings and p["ball"] == ball_no),
            None
        )

        if predicted is None:
            continue

        score = 0
        if predicted == actual_runs:
            score = settings.SCORING_EXACT
        elif abs(predicted - actual_runs) == 1:
            score = settings.SCORING_NEAR

        if score > 0:
            await redis_client.zincrby(f"match:{match_id}:leaderboard", score, user)
