from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from catalogs import HABIT_TEMPLATES
from database import get_db
from deps import get_current_user
from models import Habit, HabitLog, User
from schemas import HabitCreate, HabitUpdate, HabitWithLog

router = APIRouter(prefix="/api/habits", tags=["habits"])


@router.get("", response_model=list[HabitWithLog])
def list_habits(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    result = []
    for h in habits:
        logs = db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()
        log_dict = {l.date.isoformat(): l.done for l in logs}
        result.append(HabitWithLog(id=h.id, name=h.name, created_at=h.created_at, log=log_dict))
    return result


@router.post("", response_model=HabitWithLog, status_code=201)
def create_habit(
    data: HabitCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    habit = Habit(user_id=user.id, name=data.name.strip())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return HabitWithLog(id=habit.id, name=habit.name, created_at=habit.created_at, log={})


@router.patch("/{hid}", response_model=HabitWithLog)
def update_habit(
    hid: int,
    data: HabitUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    h = db.query(Habit).filter(Habit.id == hid, Habit.user_id == user.id).first()
    if not h:
        raise HTTPException(404)
    if data.name is not None:
        h.name = data.name.strip()
    db.commit()
    db.refresh(h)
    logs = db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()
    log_dict = {l.date.isoformat(): l.done for l in logs}
    return HabitWithLog(id=h.id, name=h.name, created_at=h.created_at, log=log_dict)


@router.delete("/{hid}", status_code=204)
def delete_habit(
    hid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    h = db.query(Habit).filter(Habit.id == hid, Habit.user_id == user.id).first()
    if not h:
        raise HTTPException(404)
    db.query(HabitLog).filter(HabitLog.habit_id == hid).delete()
    db.delete(h)
    db.commit()


@router.get("/templates")
def list_habit_templates():
    return {key: val["name"] for key, val in HABIT_TEMPLATES.items()}


@router.post("/templates/{template_key}", status_code=201)
def apply_habit_template(
    template_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tpl = HABIT_TEMPLATES.get(template_key)
    if not tpl:
        raise HTTPException(404, "Template not found")
    created = []
    for name in tpl["habits"]:
        habit = Habit(user_id=user.id, name=name)
        db.add(habit)
        db.commit()
        db.refresh(habit)
        created.append(HabitWithLog(id=habit.id, name=habit.name, created_at=habit.created_at, log={}))
    return created


@router.post("/{hid}/toggle")
def toggle_habit(
    hid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    h = db.query(Habit).filter(Habit.id == hid, Habit.user_id == user.id).first()
    if not h:
        raise HTTPException(404)
    today = date.today()
    log = db.query(HabitLog).filter(HabitLog.habit_id == hid, HabitLog.date == today).first()
    if log:
        log.done = not log.done
    else:
        log = HabitLog(habit_id=hid, date=today, done=True)
        db.add(log)
    db.commit()
    return {"date": today.isoformat(), "done": log.done}
