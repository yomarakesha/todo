import os
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from auth import create_token, decode_token, hash_password, verify_password
from database import Base, engine, get_db
from models import Habit, HabitLog, Note, PomodoroSession, Subtask, Todo, User, Workout
from schemas import (
    AuthRequest,
    AuthResponse,
    DashboardStats,
    HabitCreate,
    HabitUpdate,
    HabitWithLog,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    PomodoroSessionCreate,
    PomodoroSessionOut,
    SubtaskCreate,
    SubtaskOut,
    TodoCreate,
    TodoOut,
    TodoUpdate,
    WorkoutCreate,
    WorkoutOut,
    WorkoutUpdate,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Life Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ── Auth dependency ──────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ══════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=AuthResponse)
def register(data: AuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    if len(data.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(data.password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")
    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=create_token(user.id, user.username), username=user.username)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(data: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return AuthResponse(token=create_token(user.id, user.username), username=user.username)


# ══════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════

@app.get("/api/dashboard", response_model=DashboardStats)
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


# ══════════════════════════════════════════════════
# Todos
# ══════════════════════════════════════════════════

def _todo_with_subtasks(todo: Todo, db: Session) -> dict:
    subtasks = db.query(Subtask).filter(Subtask.todo_id == todo.id).all()
    return {
        "id": todo.id, "text": todo.text, "done": todo.done,
        "priority": todo.priority, "due": todo.due, "category": todo.category,
        "recurrence": todo.recurrence, "created_at": todo.created_at,
        "subtasks": subtasks,
    }


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos(filter: str = "all", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Todo).filter(Todo.user_id == user.id)
    if filter == "active":
        q = q.filter(Todo.done.is_(False))
    elif filter == "done":
        q = q.filter(Todo.done.is_(True))
    todos = q.order_by(Todo.created_at.desc()).all()
    return [_todo_with_subtasks(t, db) for t in todos]


@app.post("/api/todos", response_model=TodoOut, status_code=201)
def create_todo(data: TodoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = Todo(
        user_id=user.id, text=data.text.strip(), priority=data.priority,
        due=data.due or None, category=data.category, recurrence=data.recurrence,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return _todo_with_subtasks(todo, db)


@app.patch("/api/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, data: TodoUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404, "Todo not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle recurring task completion
    if "done" in update_data and update_data["done"] and todo.recurrence:
        _create_next_recurring(todo, db, user.id)

    for field, val in update_data.items():
        setattr(todo, field, val)
    db.commit()
    db.refresh(todo)
    return _todo_with_subtasks(todo, db)


def _create_next_recurring(todo: Todo, db: Session, user_id: int):
    today = date.today()
    if todo.recurrence == "daily":
        next_due = today + timedelta(days=1)
    elif todo.recurrence == "weekly":
        next_due = today + timedelta(weeks=1)
    elif todo.recurrence == "monthly":
        next_due = today.replace(month=today.month % 12 + 1) if today.month < 12 else today.replace(year=today.year + 1, month=1)
    else:
        return
    new_todo = Todo(
        user_id=user_id, text=todo.text, priority=todo.priority,
        due=next_due.isoformat(), category=todo.category, recurrence=todo.recurrence,
    )
    db.add(new_todo)


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404, "Todo not found")
    db.query(Subtask).filter(Subtask.todo_id == todo_id).delete()
    db.delete(todo)
    db.commit()


# ── Subtasks ─────────────────────────────────────

@app.get("/api/todos/{todo_id}/subtasks", response_model=list[SubtaskOut])
def list_subtasks(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    return db.query(Subtask).filter(Subtask.todo_id == todo_id).all()


@app.post("/api/todos/{todo_id}/subtasks", response_model=SubtaskOut, status_code=201)
def create_subtask(todo_id: int, data: SubtaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    sub = Subtask(todo_id=todo_id, text=data.text.strip())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@app.post("/api/todos/{todo_id}/subtasks/{sub_id}/toggle", response_model=SubtaskOut)
def toggle_subtask(todo_id: int, sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    sub = db.query(Subtask).filter(Subtask.id == sub_id, Subtask.todo_id == todo_id).first()
    if not sub:
        raise HTTPException(404)
    sub.done = not sub.done
    db.commit()
    db.refresh(sub)
    return sub


@app.delete("/api/todos/{todo_id}/subtasks/{sub_id}", status_code=204)
def delete_subtask(todo_id: int, sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    sub = db.query(Subtask).filter(Subtask.id == sub_id, Subtask.todo_id == todo_id).first()
    if not sub:
        raise HTTPException(404)
    db.delete(sub)
    db.commit()


# ══════════════════════════════════════════════════
# Workouts
# ══════════════════════════════════════════════════

@app.get("/api/workouts", response_model=list[WorkoutOut])
def list_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Workout).filter(Workout.user_id == user.id).order_by(Workout.date.desc()).all()


@app.post("/api/workouts", response_model=WorkoutOut, status_code=201)
def create_workout(data: WorkoutCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = Workout(
        user_id=user.id, exercise=data.exercise.strip(), weight=data.weight,
        sets=data.sets, reps=data.reps, muscle_group=data.muscle_group,
        date=data.date or date.today(),
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@app.patch("/api/workouts/{wid}", response_model=WorkoutOut)
def update_workout(wid: int, data: WorkoutUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = db.query(Workout).filter(Workout.id == wid, Workout.user_id == user.id).first()
    if not w:
        raise HTTPException(404)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(w, field, val)
    db.commit()
    db.refresh(w)
    return w


@app.delete("/api/workouts/{wid}", status_code=204)
def delete_workout(wid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = db.query(Workout).filter(Workout.id == wid, Workout.user_id == user.id).first()
    if not w:
        raise HTTPException(404)
    db.delete(w)
    db.commit()


# ══════════════════════════════════════════════════
# Habits
# ══════════════════════════════════════════════════

@app.get("/api/habits", response_model=list[HabitWithLog])
def list_habits(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    result = []
    for h in habits:
        logs = db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()
        log_dict = {l.date.isoformat(): l.done for l in logs}
        result.append(HabitWithLog(id=h.id, name=h.name, created_at=h.created_at, log=log_dict))
    return result


@app.post("/api/habits", response_model=HabitWithLog, status_code=201)
def create_habit(data: HabitCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    habit = Habit(user_id=user.id, name=data.name.strip())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return HabitWithLog(id=habit.id, name=habit.name, created_at=habit.created_at, log={})


@app.patch("/api/habits/{hid}", response_model=HabitWithLog)
def update_habit(hid: int, data: HabitUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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


@app.delete("/api/habits/{hid}", status_code=204)
def delete_habit(hid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(Habit).filter(Habit.id == hid, Habit.user_id == user.id).first()
    if not h:
        raise HTTPException(404)
    db.query(HabitLog).filter(HabitLog.habit_id == hid).delete()
    db.delete(h)
    db.commit()


@app.post("/api/habits/{hid}/toggle")
def toggle_habit(hid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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


# ══════════════════════════════════════════════════
# Pomodoro
# ══════════════════════════════════════════════════

@app.get("/api/pomodoro/today")
def pomodoro_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    count = db.query(PomodoroSession).filter(
        PomodoroSession.user_id == user.id, PomodoroSession.date == today
    ).count()
    return {"date": today.isoformat(), "sessions": count}


@app.post("/api/pomodoro/complete", response_model=PomodoroSessionOut, status_code=201)
def complete_pomodoro(data: PomodoroSessionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = PomodoroSession(user_id=user.id, duration=data.duration, date=date.today())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ══════════════════════════════════════════════════
# Notes
# ══════════════════════════════════════════════════

@app.get("/api/notes", response_model=list[NoteOut])
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.user_id == user.id).order_by(Note.date.desc()).all()


@app.get("/api/notes/{nid}", response_model=NoteOut)
def get_note(nid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == nid, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(404)
    return n


@app.post("/api/notes", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = Note(
        user_id=user.id, title=data.title, content=data.content,
        date=data.date or date.today(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.patch("/api/notes/{nid}", response_model=NoteOut)
def update_note(nid: int, data: NoteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == nid, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(404)
    if data.title is not None:
        n.title = data.title
    if data.content is not None:
        n.content = data.content
    n.updated_at = datetime.now()
    db.commit()
    db.refresh(n)
    return n


@app.delete("/api/notes/{nid}", status_code=204)
def delete_note(nid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == nid, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(404)
    db.delete(n)
    db.commit()


# ══════════════════════════════════════════════════
# Analytics
# ══════════════════════════════════════════════════

@app.get("/api/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()

    # Workouts per day (last 30 days)
    workout_days = {}
    for i in range(30):
        d = today - timedelta(days=29 - i)
        workout_days[d.isoformat()] = 0
    workouts = db.query(Workout).filter(
        Workout.user_id == user.id, Workout.date >= today - timedelta(days=29)
    ).all()
    for w in workouts:
        key = w.date.isoformat()
        if key in workout_days:
            workout_days[key] += 1

    # Habit heatmap (last 12 weeks)
    habits = db.query(Habit).filter(Habit.user_id == user.id).all()
    habit_heatmap = {}
    for i in range(84):
        d = today - timedelta(days=83 - i)
        ds = d.isoformat()
        count = 0
        for h in habits:
            log = db.query(HabitLog).filter(
                HabitLog.habit_id == h.id, HabitLog.date == d, HabitLog.done.is_(True)
            ).first()
            if log:
                count += 1
        habit_heatmap[ds] = count

    # Pomodoro per day (last 14 days)
    pomo_days = {}
    for i in range(14):
        d = today - timedelta(days=13 - i)
        count = db.query(PomodoroSession).filter(
            PomodoroSession.user_id == user.id, PomodoroSession.date == d
        ).count()
        pomo_days[d.isoformat()] = count

    # Todos completed per day (last 14 days)
    todos = db.query(Todo).filter(Todo.user_id == user.id, Todo.done.is_(True)).all()
    todo_done_days = {}
    for i in range(14):
        d = today - timedelta(days=13 - i)
        todo_done_days[d.isoformat()] = 0
    # Approximate from created_at date for done tasks
    for t in todos:
        key = t.created_at.date().isoformat()
        if key in todo_done_days:
            todo_done_days[key] += 1

    # Muscle group distribution
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


# ══════════════════════════════════════════════════
# Static files (SPA) — must be AFTER all /api routes
# ══════════════════════════════════════════════════

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


# ══════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
