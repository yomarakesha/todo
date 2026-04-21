from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Note, User
from schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=list[NoteOut])
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.user_id == user.id).order_by(Note.date.desc()).all()


@router.get("/{nid}", response_model=NoteOut)
def get_note(nid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == nid, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(404)
    return n


@router.post("", response_model=NoteOut, status_code=201)
def create_note(
    data: NoteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = Note(
        user_id=user.id, title=data.title, content=data.content,
        date=data.date or date.today(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.patch("/{nid}", response_model=NoteOut)
def update_note(
    nid: int,
    data: NoteUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


@router.delete("/{nid}", status_code=204)
def delete_note(nid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Note).filter(Note.id == nid, Note.user_id == user.id).first()
    if not n:
        raise HTTPException(404)
    db.delete(n)
    db.commit()
