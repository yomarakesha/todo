from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import PushSubscription, User
from push import get_public_key, send_push
from schemas import PushSubscriptionCreate

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-key")
def vapid_public_key():
    return {"publicKey": get_public_key()}


@router.post("/subscribe", status_code=201)
def push_subscribe(
    data: PushSubscriptionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == data.endpoint).first()
    if existing:
        existing.user_id = user.id
        existing.p256dh = data.keys["p256dh"]
        existing.auth = data.keys["auth"]
    else:
        sub = PushSubscription(
            user_id=user.id, endpoint=data.endpoint,
            p256dh=data.keys["p256dh"], auth=data.keys["auth"],
        )
        db.add(sub)
    db.commit()
    return {"status": "subscribed"}


@router.delete("/unsubscribe", status_code=204)
def push_unsubscribe(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(PushSubscription).filter(PushSubscription.user_id == user.id).delete()
    db.commit()


@router.post("/test")
def push_test(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
    if not subs:
        raise HTTPException(404, "No push subscriptions found")
    sent = 0
    for sub in subs:
        sub_info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        result = send_push(sub_info, "Life Tracker", "Push-уведомления работают!", "/")
        if result is True:
            sent += 1
        elif result == "gone":
            db.delete(sub)
            db.commit()
    return {"sent": sent}
