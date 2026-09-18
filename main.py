import random
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ZYROX eSports API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/users/")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    generated_zrx_id = f"ZRX-{random.randint(10000, 99999)}"
    new_user = models.User(
        zrx_id=generated_zrx_id,
        name=user.name,
        email=user.email,
        password=user.password,
        wallet_balance=0.0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Registered successfully", "user_id": new_user.id, "zrx_id": new_user.zrx_id, "wallet": new_user.wallet_balance}

@app.post("/users/login")
def login_user(data: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.get("email")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found!")
    if user.is_blocked == 1:
        raise HTTPException(status_code=403, detail="Account suspended by Admin!")
    if user.password and user.password != data.get("password"):
        raise HTTPException(status_code=400, detail="Incorrect password!")
    return {"message": "Login successful", "user_id": user.id, "zrx_id": user.zrx_id, "wallet": user.wallet_balance, "name": user.name}

@app.post("/users/forgot-password")
def forgot_password(data: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.get("email")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found!")
    user.password = data.get("new_password")
    db.commit()
    return {"message": "Password updated successfully!"}

@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "zrx_id": u.zrx_id, "name": u.name, "email": u.email, "wallet": u.wallet_balance, "is_blocked": u.is_blocked} for u in users]

@app.post("/admin/users/{user_id}/block")
def block_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_blocked = 1 if user.is_blocked == 0 else 0
        db.commit()
    return {"message": "Status updated"}

@app.post("/users/topup")
def topup_wallet(data: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == data.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.wallet_balance += float(data.get("amount", 0))
    db.commit()
    return {"message": "Topup success", "new_wallet": user.wallet_balance}

@app.get("/users/{user_id}/history")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    participants = db.query(models.Participant).filter(models.Participant.user_id == user_id).all()
    history = []
    for p in participants:
        tourney = db.query(models.Tournament).filter(models.Tournament.id == p.tournament_id).first()
        if tourney:
            history.append({"title": tourney.title, "game": tourney.game_category, "format": tourney.match_format, "fee": tourney.entry_fee, "status": p.payment_status, "match_status": tourney.status})
    return history

@app.post("/tournaments/")
def create_tournament(t: schemas.TournamentCreate, db: Session = Depends(get_db)):
    nt = models.Tournament(
        game_category=t.game_category,
        match_format=t.match_format,
        title=t.title,
        entry_fee=t.entry_fee,
        prize_pool=t.prize_pool,
        slots=t.slots,
        start_time=t.start_time,
        status="Active"
    )
    db.add(nt)
    db.commit()
    db.refresh(nt)
    
    room = models.MatchRoom(tournament_id=nt.id, room_id="Hidden", room_password="Hidden", status="Pending")
    db.add(room)
    db.commit()
    return {"message": "Tournament created", "tournament_id": nt.id}

@app.get("/tournaments/")
def list_tournaments(db: Session = Depends(get_db)):
    return db.query(models.Tournament).all()

@app.post("/tournaments/{tournament_id}/cancel")
def cancel_tournament(tournament_id: int, db: Session = Depends(get_db)):
    tourney = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tourney:
        raise HTTPException(status_code=404, detail="Not found")
    tourney.status = "Cancelled"
    
    participants = db.query(models.Participant).filter(models.Participant.tournament_id == tournament_id, models.Participant.payment_status == "SUCCESS").all()
    for p in participants:
        user = db.query(models.User).filter(models.User.id == p.user_id).first()
        if user:
            user.wallet_balance += tourney.entry_fee
        p.payment_status = "REFUNDED"
    db.commit()
    return {"message": "Cancelled and refunded"}

@app.post("/tournaments/{tournament_id}/room")
def publish_room(tournament_id: int, rd: schemas.RoomPublish, db: Session = Depends(get_db)):
    room = db.query(models.MatchRoom).filter(models.MatchRoom.tournament_id == tournament_id).first()
    if room:
        room.room_id = rd.room_id
        room.room_password = rd.room_password
        room.status = "Published"
    db.commit()
    return {"message": "Room published"}

@app.get("/tournaments/{tournament_id}/room/{user_id}")
def get_secure_room(tournament_id: int, user_id: int, db: Session = Depends(get_db)):
    tourney = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if tourney and tourney.status == "Cancelled":
        return {"status": "Cancelled", "room_id": "Cancelled", "room_password": "-"}
        
    p = db.query(models.Participant).filter(models.Participant.tournament_id == tournament_id, models.Participant.user_id == user_id, models.Participant.payment_status == "SUCCESS").first()
    if not p:
        raise HTTPException(status_code=403, detail="Access Denied")
    room = db.query(models.MatchRoom).filter(models.MatchRoom.tournament_id == tournament_id).first()
    if not room or room.status != "Published":
        return {"status": "Pending", "room_id": "Will open 10 mins before match", "room_password": "---"}
    return {"status": room.status, "room_id": room.room_id, "room_password": room.room_password}

@app.post("/tournaments/join")
def join_tournament(data: schemas.JoinTournament, db: Session = Depends(get_db)):
    tourney = db.query(models.Tournament).filter(models.Tournament.id == data.tournament_id).first()
    if not tourney or tourney.status == "Cancelled":
        raise HTTPException(status_code=400, detail="Tournament unavailable or cancelled")
        
    user = db.query(models.User).filter(models.User.id == data.user_id).first()
    if user.wallet_balance < tourney.entry_fee:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance!")
        
    user.wallet_balance -= tourney.entry_fee
    existing = db.query(models.Participant).filter(models.Participant.tournament_id == data.tournament_id, models.Participant.user_id == data.user_id).first()
    if existing:
        existing.payment_status = "SUCCESS"
    else:
        p = models.Participant(tournament_id=data.tournament_id, user_id=data.user_id, payment_status="SUCCESS", utr_number="WALLET")
        db.add(p)
    db.commit()
    return {"message": "Joined", "remaining_wallet": user.wallet_balance}

@app.get("/tournaments/{tournament_id}/leaderboard")
def get_leaderboard(tournament_id: int, db: Session = Depends(get_db)):
    res = db.query(models.MatchResult).filter(models.MatchResult.tournament_id == tournament_id).all()
    return [{"zrx_id": "ZRX", "score": r.score} for r in res]