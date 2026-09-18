from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    zrx_id = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=True)
    wallet_balance = Column(Float, default=0.0)
    is_blocked = Column(Integer, default=0)

class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    game_category = Column(String) # e.g., "Free Fire MAX", "BGMI", "COD Mobile"
    match_format = Column(String)  # e.g., "Solo", "Duo", "Squad"
    title = Column(String)         # e.g., "Free Fire Solo Daily Clash"
    entry_fee = Column(Float)
    prize_pool = Column(Float)
    slots = Column(Integer)
    start_time = Column(String)    # e.g., "Today, 06:00 PM"
    status = Column(String, default="Active")

class MatchRoom(Base):
    __tablename__ = "match_rooms"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    room_id = Column(String, default="Hidden")
    room_password = Column(String, default="Hidden")
    status = Column(String, default="Pending")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    payment_status = Column(String, default="PENDING")
    utr_number = Column(String, nullable=True)

class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer, default=0)
    status = Column(String, default="Verifying")