from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from catalogs import TODO_TEMPLATES
from database import get_db
from deps import get_current_user
from models import Subtask, Todo, User
from schemas import SubtaskCreate, SubtaskOut, TodoCreate, TodoOut, TodoUpdate

router = APIRouter(prefix="/api/todos", tags=["todos"])


def _todo_with_subtasks(todo: Todo, db: Session) -> dict:
    subtasks = db.query(Subtask).filter(Subtask.todo_id == todo.id).all()
    return {
        "id": todo.id, "text": todo.text, "done": todo.done,
        "priority": todo.priority, "due": todo.due, "category": todo.category,
        "recurrence": todo.recurrence, "created_at": todo.created_at,
        "subtasks": subtasks,
    }


def _create_next_recurring(todo: Todo, db: Session, user_id: int):
    today = date.today()
    if todo.recurrence == "daily":
        next_due = today + timedelta(days=1)
    elif todo.recurrence == "weekly":
        next_due = today + timedelta(weeks=1)
    elif todo.recurrence == "monthly":
        next_due = (
            today.replace(month=today.month % 12 + 1)
            if today.month < 12
            else today.replace(year=today.year + 1, month=1)
        )
    else:
        return
    new_todo = Todo(
        user_id=user_id, text=todo.text, priority=todo.priority,
        due=next_due.isoformat(), category=todo.category, recurrence=todo.recurrence,
    )
    db.add(new_todo)


@router.get("/templates")
def list_todo_templates():
    return {key: val["name"] for key, val in TODO_TEMPLATES.items()}


@router.post("/templates/{template_key}", status_code=201)
def apply_todo_template(
    template_key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tpl = TODO_TEMPLATES.get(template_key)
    if not tpl:
        raise HTTPException(404, "Template not found")
    created = []
    for task in tpl["tasks"]:
        todo = Todo(user_id=user.id, text=task["text"])
        db.add(todo)
        db.commit()
        db.refresh(todo)
        for st in task.get("subtasks", []):
            sub = Subtask(todo_id=todo.id, text=st)
            db.add(sub)
        db.commit()
        created.append(_todo_with_subtasks(todo, db))
    return created


@router.get("", response_model=list[TodoOut])
def list_todos(
    filter: str = "all",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Todo).filter(Todo.user_id == user.id)
    if filter == "active":
        q = q.filter(Todo.done.is_(False))
    elif filter == "done":
        q = q.filter(Todo.done.is_(True))
    todos = q.order_by(Todo.created_at.desc()).all()
    return [_todo_with_subtasks(t, db) for t in todos]


@router.post("", response_model=TodoOut, status_code=201)
def create_todo(
    data: TodoCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = Todo(
        user_id=user.id, text=data.text.strip(), priority=data.priority,
        due=data.due or None, category=data.category, recurrence=data.recurrence,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return _todo_with_subtasks(todo, db)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: int,
    data: TodoUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404, "Todo not found")

    update_data = data.model_dump(exclude_unset=True)

    if "done" in update_data and update_data["done"] and todo.recurrence:
        _create_next_recurring(todo, db, user.id)

    for field, val in update_data.items():
        setattr(todo, field, val)
    db.commit()
    db.refresh(todo)
    return _todo_with_subtasks(todo, db)


@router.delete("/{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404, "Todo not found")
    db.query(Subtask).filter(Subtask.todo_id == todo_id).delete()
    db.delete(todo)
    db.commit()


@router.get("/{todo_id}/subtasks", response_model=list[SubtaskOut])
def list_subtasks(
    todo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    return db.query(Subtask).filter(Subtask.todo_id == todo_id).all()


@router.post("/{todo_id}/subtasks", response_model=SubtaskOut, status_code=201)
def create_subtask(
    todo_id: int,
    data: SubtaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    sub = Subtask(todo_id=todo_id, text=data.text.strip())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.post("/{todo_id}/subtasks/{sub_id}/toggle", response_model=SubtaskOut)
def toggle_subtask(
    todo_id: int,
    sub_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


@router.delete("/{todo_id}/subtasks/{sub_id}", status_code=204)
def delete_subtask(
    todo_id: int,
    sub_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.user_id == user.id).first()
    if not todo:
        raise HTTPException(404)
    sub = db.query(Subtask).filter(Subtask.id == sub_id, Subtask.todo_id == todo_id).first()
    if not sub:
        raise HTTPException(404)
    db.delete(sub)
    db.commit()
