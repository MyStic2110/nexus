import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

POINTS_EXACT_RUN = 10   # Exact run prediction match
POINTS_EXACT_WICKET = 25  # Exact wicket prediction match
POINTS_TYPE = 0          # Bonus for same category (Removed)


def calculate_ball_points(predicted: str, actual: str) -> int:
    """
    Scoring rules:
    - Exact WICKET match (W vs W) → 25 pts
    - Exact RUN match (e.g. 4 vs 4) → 10 pts
    - Mismatch → 0 pts
    """
    p = str(predicted).strip()
    a = str(actual).strip()

    if p == a:
        if p == "W":
            return POINTS_EXACT_WICKET
        return POINTS_EXACT_RUN
        
    # Relaxed matching for wickets with runs (e.g. 1|W, W)
    if p == "W" and "W" in a:
        return POINTS_EXACT_WICKET
        
    # Relaxed matching for runs with byes/leg-byes (e.g. 1Lb, 4B)
    if p != "W" and "W" not in a and p in a:
        return POINTS_EXACT_RUN

    return 0


async def run_for_match(db, match_id: str, session_id: int):
    # Governance: Check if session is truly finished before calculating points.
    # Finshed = Match status COMPLETED OR session has finished over 20.
    match_doc = await db.matches.find_one({"match_id": match_id})
    if not match_doc:
        return

    is_ready = (match_doc.get("status") == "COMPLETED")
    if not is_ready:
        over_20 = await db.live_match_overs.find_one({"match_id": match_id, "session_id": session_id, "over": 20})
        if over_20:
            balls = over_20.get("balls", [])
            legal = [b for b in balls if "Wd" not in str(b) and "Nb" not in str(b)]
            if len(legal) >= 6:
                is_ready = True

    if not is_ready:
        print(f"[NEXUS] Session {session_id} for match {match_id} is still in progress. Skipping points sync.")
        return

    print(f"\n[NEXUS] Calculating points for match={match_id} session={session_id}")

    # --- Step 1: Pull ONLY Overs 19 & 20 from live_match_overs ---
    overs_cursor = db.live_match_overs.find(
        {"match_id": match_id, "session_id": session_id, "over": {"$in": [19, 20]}}
    ).sort("over", 1)
    overs = await overs_cursor.to_list(length=2)

    if not overs:
        print(f"[NEXUS] Death overs (19/20) not found for session {session_id}. Proceeding with 0 actual balls.")
        # No return here, let it proceed to update session_scores with 0 points

    # Build a flat sequence of balls from Over 19 and 20
    actual_balls = []
    # over_map stores the balls for 19 and 20 explicitly to handle cases where 19 exists but 20 doesn't
    over_data = {o["over"]: o.get("balls", []) for o in overs}
    
    # Sequence: 6 balls of over 19, then 6 balls of over 20
    for o_num in [19, 20]:
        balls = over_data.get(o_num, [])
        # Exclude extras to get the 6 legal balls
        legal = [b for b in balls if "Wd" not in str(b) and "Nb" not in str(b)]
        actual_balls.extend(legal)

    total_actual_balls = len(actual_balls)
    print(f"[NEXUS] Points processing: {total_actual_balls} legal balls recovered for session {session_id}")

    if total_actual_balls == 0:
        print(f"[NEXUS] No actual balls recorded for session {session_id}. Users will receive 0 points.")

    # --- Step 2: Fetch all user predictions for this match+session ---
    field_path = f"sessions.{session_id}"
    predictions_cursor = db.predictions.find(
        {"match_id": match_id, field_path: {"$exists": True}}
    )
    predictions = await predictions_cursor.to_list(length=1000)

    if not predictions:
        print(f"[NEXUS] No user predictions found for session {session_id}.")
        return

    print(f"[NEXUS] Processing {len(predictions)} user prediction sets...")

    upserts = []

    for doc in predictions:
        user_id = doc["user_id"]
        session_data = doc.get("sessions", {}).get(str(session_id), {})
        user_preds = session_data.get("predictions", [])

        session_points = 0
        breakdown = []
        for pred in user_preds:
            ball_num = int(pred.get("ball", 0))
            if ball_num < 1 or (ball_num - 1) >= total_actual_balls:
                continue
                
            actual = actual_balls[ball_num - 1]
            predicted = pred.get("runs", "0")
            pts = calculate_ball_points(predicted, actual)
            session_points += pts
            
            breakdown.append({
                "ball_num": ball_num,
                "predicted": predicted,
                "actual": actual,
                "points": pts
            })

        print(f"  -> User {user_id} | Session {session_id} | Points: {session_points}")

        # Upsert session-level score record with breakdown
        await db.session_scores.update_one(
            {"match_id": match_id, "session_id": session_id, "user_id": user_id},
            {"$set": {
                "points": session_points,
                "breakdown": breakdown,
                "updated_at": datetime.now()
            }},
            upsert=True
        )

        # Redis sync removed as we have transitioned to a pure MongoDB architecture.

    # --- Step 3: Recalculate Global User Scores (Prevent Duplication) ---
    # This phase ensures that the user's total score is the sum of all session_scores,
    # meaning running this script multiple times won't double the score.
    print(f"[NEXUS] Refreshing global standings for users who played session {session_id}...")
    distinct_users = await db.session_scores.distinct("user_id")
    for u_id in distinct_users:
        # Sum all session scores for this user
        pipeline = [
            {"$match": {"user_id": u_id}},
            {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}}}
        ]
        agg_result = await db.session_scores.aggregate(pipeline).to_list(1)
        if agg_result:
            total_score = agg_result[0]["total"]
            await db.users.update_one(
                {"_id": u_id},
                {"$set": {"score": total_score}},
                upsert=True
            )

    print(f"[NEXUS] {len(predictions)} users updated for session {session_id}.")


async def calculate_all_sessions_for_match(db, match_id: str):
    """Triggers calculation for both innings of a specific match."""
    print(f"\n[NEXUS] Triggering full match scoring recalculation for {match_id}...")
    for session_id in [1, 2]:
        await run_for_match(db, match_id, session_id)
    print(f"[NEXUS] Full match scoring complete for {match_id}.")


async def calculate_points():
    print("=" * 50)
    print(" NEXUS POINT DISTRIBUTION ENGINE STARTING")
    print("=" * 50)

    client = AsyncIOMotorClient(MONGO_URI)
    db = client.ipl_game

    # Find all matches in the DB
    matches_cursor = db.matches.find({})
    async for match in matches_cursor:
        if "match_id" not in match:
            continue
            
        match_id = match["match_id"]
        print(f"\n[NEXUS] Processing Match: {match_id}  {match.get('team1')} vs {match.get('team2')}")

        # Run for both sessions
        for session_id in [1, 2]:
            await run_for_match(db, match_id, session_id)

    # Print final leaderboard summary
    print("\n[NEXUS] === FINAL STANDINGS SNAPSHOT ===")
    users = await db.users.find({}).sort("score", -1).limit(10).to_list(10)
    for i, u in enumerate(users):
        print(f"  #{i+1}  {u['_id']}  ->  {u.get('score', 0)} pts")

    print("\n[NEXUS] Point distribution complete.")
    client.close()


if __name__ == "__main__":
    asyncio.run(calculate_points())
