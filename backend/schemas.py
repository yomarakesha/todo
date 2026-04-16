from datetime import date as Date
from datetime import datetime as DateTime
from typing import Optional

from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str


# ── Todo ──────────────────────────────────────────

class TodoCreate(BaseModel):
    text: str
    priority: str = "medium"
    due: Optional[str] = None
    category: str = ""
    recurrence: str = ""


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None
    priority: Optional[str] = None
    due: Optional[str] = None
    category: Optional[str] = None
    recurrence: Optional[str] = None


class SubtaskOut(BaseModel):
    id: int
    todo_id: int
    text: str
    done: bool
    model_config = {"from_attributes": True}


class TodoOut(BaseModel):
    id: int
    text: str
    done: bool
    priority: str
    due: Optional[str]
    category: str
    recurrence: str
    created_at: DateTime
    subtasks: list[SubtaskOut] = []

    model_config = {"from_attributes": True}


# ── Subtask ───────────────────────────────────────

class SubtaskCreate(BaseModel):
    text: str


# ── Workout ───────────────────────────────────────

class WorkoutCreate(BaseModel):
    exercise: str
    weight: float = 0
    sets: int = 0
    reps: int = 0
    muscle_group: str = "other"
    date: Optional[Date] = None


class WorkoutUpdate(BaseModel):
    exercise: Optional[str] = None
    weight: Optional[float] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    muscle_group: Optional[str] = None
    date: Optional[Date] = None


class WorkoutOut(BaseModel):
    id: int
    exercise: str
    weight: float
    sets: int
    reps: int
    muscle_group: str
    date: Date

    model_config = {"from_attributes": True}


# ── Habit ─────────────────────────────────────────

class HabitCreate(BaseModel):
    name: str


class HabitUpdate(BaseModel):
    name: Optional[str] = None


class HabitWithLog(BaseModel):
    id: int
    name: str
    created_at: DateTime
    log: dict[str, bool]

    model_config = {"from_attributes": True}


# ── Pomodoro ──────────────────────────────────────

class PomodoroSessionCreate(BaseModel):
    duration: int = 25


class PomodoroSessionOut(BaseModel):
    id: int
    date: Date
    duration: int
    completed_at: DateTime

    model_config = {"from_attributes": True}


# ── Notes ─────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = ""
    content: str = ""
    date: Optional[Date] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    date: Date
    updated_at: DateTime

    model_config = {"from_attributes": True}


# ── Stats ─────────────────────────────────────────

class DashboardStats(BaseModel):
    todos_active: int
    todos_done: int
    todos_overdue: int
    workouts_this_week: int
    last_exercise: str
    max_weight: float
    habits_total: int
    habits_done_today: int
    best_streak: int
    pomodoro_today: int
