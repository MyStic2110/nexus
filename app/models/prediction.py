from pydantic import BaseModel
from typing import List, Optional

class BallPrediction(BaseModel):
    ball: int
    runs: str  # Support "0", "1", "2", "4", "6", "W"
    innings: Optional[int] = 1

class UserPrediction(BaseModel):
    predictions: List[BallPrediction]
