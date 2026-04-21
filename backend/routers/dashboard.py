from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Habit, HabitLog, PomodoroSession, Todo, User, Workout
from schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    todos = db.query(Todo).filter(Todo.user_id == user.id).all()
    active = sum(1 for t in todos if not t.done)
    done = sum(1 for t in todos if t.done)
    overdue = sum(1 for t in todos if not t.done and t.due and t.due < today.isoformat())

    workouts = db.query(Workout).filter(Workout.user_id == user.id).all()
    this_week = sum(1 for w in workouts if w.date >= week_start)
    last_ex = workouts[-1].exercise if workouts else "\u2014"
    max_w = max((w.weight for w in workouts), default=0)

    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    done_today = (
        db.query(HabitLog)
        .join(Habit, HabitLog.habit_id == Habit.id)
        .filter(Habit.user_id == user.id, HabitLog.date == today, HabitLog.done.is_(True))
        .count()
    )

    best = 0
    for h in habits:
        logs = db.query(HabitLog).filter(HabitLog.habit_id == h.id, HabitLog.done.is_(True)).all()
        dates = {l.date for l in logs}
        streak = 0
        d = today
        while d in dates:
            streak += 1
            d -= timedelta(days=1)
        best = max(best, streak)

    pomo_today = (
        db.query(PomodoroSession)
        .filter(PomodoroSession.user_id == user.id, PomodoroSession.date == today)
        .count()
    )

    return DashboardStats(
        todos_active=active, todos_done=done, todos_overdue=overdue,
        workouts_this_week=this_week, last_exercise=last_ex, max_weight=max_w,
        habits_total=len(habits), habits_done_today=done_today,
        best_streak=best, pomodoro_today=pomo_today,
    )
