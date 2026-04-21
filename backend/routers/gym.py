from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from catalogs import EXERCISE_CATALOG
from database import get_db
from deps import get_current_user
from models import User, Workout
from schemas import WorkoutCreate, WorkoutOut, WorkoutUpdate

router = APIRouter(tags=["gym"])


@router.get("/api/exercises")
def get_exercises():
    return EXERCISE_CATALOG


@router.get("/api/workouts/last")
def last_workout_for_exercise(
    exercise: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = (
        db.query(Workout)
        .filter(Workout.user_id == user.id, Workout.exercise == exercise)
        .order_by(Workout.date.desc())
        .first()
    )
    if not w:
        return None
    return {
        "exercise": w.exercise, "weight": w.weight, "sets": w.sets,
        "reps": w.reps, "muscle_group": w.muscle_group,
    }


@router.get("/api/workouts", response_model=list[WorkoutOut])
def list_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Workout)
        .filter(Workout.user_id == user.id)
        .order_by(Workout.date.desc())
        .all()
    )


@router.post("/api/workouts", response_model=WorkoutOut, status_code=201)
def create_workout(
    data: WorkoutCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workout = Workout(
        user_id=user.id, exercise=data.exercise.strip(), weight=data.weight,
        sets=data.sets, reps=data.reps, muscle_group=data.muscle_group,
        date=data.date or date.today(),
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@router.patch("/api/workouts/{wid}", response_model=WorkoutOut)
def update_workout(
    wid: int,
    data: WorkoutUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = db.query(Workout).filter(Workout.id == wid, Workout.user_id == user.id).first()
    if not w:
        raise HTTPException(404)
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(w, field, val)
    db.commit()
    db.refresh(w)
    return w


@router.delete("/api/workouts/{wid}", status_code=204)
def delete_workout(
    wid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = db.query(Workout).filter(Workout.id == wid, Workout.user_id == user.id).first()
    if not w:
        raise HTTPException(404)
    db.delete(w)
    db.commit()
