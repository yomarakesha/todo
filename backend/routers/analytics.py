from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Habit, HabitLog, PomodoroSession, Todo, User, Workout

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()

    workout_days = {}
    for i in range(30):
        d = today - timedelta(days=29 - i)
        workout_days[d.isoformat()] = 0
    workouts = (
        db.query(Workout)
        .filter(Workout.user_id == user.id, Workout.date >= today - timedelta(days=29))
        .all()
    )
    for w in workouts:
        key = w.date.isoformat()
        if key in workout_days:
            workout_days[key] += 1

    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    habit_heatmap = {}
    for i in range(84):
        d = today - timedelta(days=83 - i)
        ds = d.isoformat()
        count = 0
        for h in habits:
            log = (
                db.query(HabitLog)
                .filter(HabitLog.habit_id == h.id, HabitLog.date == d, HabitLog.done.is_(True))
                .first()
            )
            if log:
                count += 1
        habit_heatmap[ds] = count

    pomo_days = {}
    for i in range(14):
        d = today - timedelta(days=13 - i)
        count = (
            db.query(PomodoroSession)
            .filter(PomodoroSession.user_id == user.id, PomodoroSession.date == d)
            .count()
        )
        pomo_days[d.isoformat()] = count

    todos = db.query(Todo).filter(Todo.user_id == user.id, Todo.done.is_(True)).all()
    todo_done_days = {}
    for i in range(14):
        d = today - timedelta(days=13 - i)
        todo_done_days[d.isoformat()] = 0
    for t in todos:
        key = t.created_at.date().isoformat()
        if key in todo_done_days:
            todo_done_days[key] += 1

    all_workouts = db.query(Workout).filter(Workout.user_id == user.id).all()
    muscle_dist = {}
    for w in all_workouts:
        muscle_dist[w.muscle_group] = muscle_dist.get(w.muscle_group, 0) + 1

    return {
        "workout_days": workout_days,
        "habit_heatmap": habit_heatmap,
        "habits_total": len(habits),
        "pomo_days": pomo_days,
        "todo_done_days": todo_done_days,
        "muscle_distribution": muscle_dist,
    }
