from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: str
    password: Optional[str] = None

class TournamentCreate(BaseModel):
    game_category: str
    match_format: str
    title: str
    entry_fee: float
    prize_pool: float
    slots: int
    start_time: str

class RoomPublish(BaseModel):
    room_id: str
    room_password: str

class JoinTournament(BaseModel):
    user_id: int
    tournament_id: int
    utr_number: str

class SubmitResult(BaseModel):
    user_id: int
    score: int