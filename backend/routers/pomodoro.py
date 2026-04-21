from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import PomodoroSession, User
from schemas import PomodoroSessionCreate, PomodoroSessionOut

router = APIRouter(prefix="/api/pomodoro", tags=["pomodoro"])


@router.get("/today")
def pomodoro_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    count = (
        db.query(PomodoroSession)
        .filter(PomodoroSession.user_id == user.id, PomodoroSession.date == today)
        .count()
    )
    return {"date": today.isoformat(), "sessions": count}


@router.post("/complete", response_model=PomodoroSessionOut, status_code=201)
def complete_pomodoro(
    data: PomodoroSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = PomodoroSession(user_id=user.id, duration=data.duration, date=date.today())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
