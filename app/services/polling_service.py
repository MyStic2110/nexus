import asyncio, json
from app.db.redis import redis_client
from app.services.api_client import fetch_last_2_overs
from app.services.scoring_service import process_ball
from app.config import settings

async def poll_match(match_id: str):
    while True:
        try:
            balls = await fetch_last_2_overs(match_id)

            for ball in balls:
                innings = ball["innings"]
                ball_no = ball["ball_number"]
                runs = ball["runs"]

                key = f"match:{match_id}:innings:{innings}:balls"

                exists = await redis_client.hexists(key, ball_no)
                if exists:
                    continue

                await redis_client.hset(key, ball_no, runs)
                await process_ball(match_id, innings, ball_no, runs)

                await redis_client.publish(
                    f"match:{match_id}:channel",
                    json.dumps({
                        "type": "ball",
                        "innings": innings,
                        "ball": ball_no,
                        "runs": runs
                    })
                )
        except Exception:
            pass

        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)
