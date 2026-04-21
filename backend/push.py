import base64
import json
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# ── VAPID key management ─────────────────────────

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "mailto:admin@lifetracker.app")

_vapid_ready = False


def _ensure_vapid_keys():
    global VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, _vapid_ready

    if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
        _vapid_ready = True
        return

    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            PublicFormat,
        )

        keys_dir = os.path.join(os.path.dirname(__file__), ".vapid_keys")
        priv_path = os.path.join(keys_dir, "private_key.pem")
        pub_path = os.path.join(keys_dir, "public_key.txt")

        if os.path.exists(priv_path) and os.path.exists(pub_path):
            with open(priv_path) as f:
                VAPID_PRIVATE_KEY = f.read().strip()
            with open(pub_path) as f:
                VAPID_PUBLIC_KEY = f.read().strip()
            _vapid_ready = True
            return

        # Generate new ECDSA key pair
        private_key = ec.generate_private_key(ec.SECP256R1())

        VAPID_PRIVATE_KEY = private_key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        ).decode()

        raw_pub = private_key.public_key().public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint
        )
        VAPID_PUBLIC_KEY = base64.urlsafe_b64encode(raw_pub).decode().rstrip("=")

        # Persist to disk
        try:
            os.makedirs(keys_dir, exist_ok=True)
            with open(priv_path, "w") as f:
                f.write(VAPID_PRIVATE_KEY)
            with open(pub_path, "w") as f:
                f.write(VAPID_PUBLIC_KEY)
        except OSError:
            logger.warning("Could not persist VAPID keys to disk (read-only fs?)")

        _vapid_ready = True
        logger.info("Generated new VAPID keys")

    except Exception as e:
        logger.error("Failed to generate VAPID keys: %s", e)
        _vapid_ready = False


_ensure_vapid_keys()


def get_public_key() -> str:
    return VAPID_PUBLIC_KEY


def send_push(subscription_info: dict, title: str, body: str, url: str = "/"):
    if not _vapid_ready:
        logger.warning("VAPID keys not configured, skipping push")
        return False

    from pywebpush import webpush, WebPushException

    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_EMAIL},
        )
        return True
    except WebPushException as e:
        logger.warning("Push failed: %s", e)
        if e.response and e.response.status_code in (404, 410):
            return "gone"
        return False
    except Exception as e:
        logger.error("Unexpected push error: %s", e)
        return False


# ── Scheduler ────────────────────────────────────

_scheduler_started = False


def start_scheduler(get_db_func):
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    def run_reminders():
        while True:
            try:
                _send_daily_reminders(get_db_func)
            except Exception as e:
                logger.error("Scheduler error: %s", e)
            time.sleep(3600)

    t = threading.Thread(target=run_reminders, daemon=True)
    t.start()
    logger.info("Push notification scheduler started")


def _send_daily_reminders(get_db_func):
    from models import Habit, HabitLog, PushSubscription, Todo, User

    db = next(get_db_func())
    try:
        today = date.today()
        now_hour = datetime.now().hour

        if now_hour not in (9, 20):
            return

        users = db.query(User).all()
        for user in users:
            subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
            if not subs:
                continue

            messages = []

            if now_hour == 9:
                overdue = db.query(Todo).filter(
                    Todo.user_id == user.id, Todo.done.is_(False),
                    Todo.due.isnot(None), Todo.due < today.isoformat()
                ).count()
                active = db.query(Todo).filter(
                    Todo.user_id == user.id, Todo.done.is_(False)
                ).count()
                if overdue > 0:
                    messages.append(("Просроченные задачи", f"У вас {overdue} просроченных задач из {active} активных", "/todo"))
                elif active > 0:
                    messages.append(("Доброе утро!", f"У вас {active} активных задач на сегодня", "/todo"))

            if now_hour == 20:
                habits = db.query(Habit).filter(Habit.user_id == user.id).all()
                if habits:
                    done_today = db.query(HabitLog).join(Habit).filter(
                        Habit.user_id == user.id, HabitLog.date == today, HabitLog.done.is_(True)
                    ).count()
                    remaining = len(habits) - done_today
                    if remaining > 0:
                        messages.append(("Привычки", f"Осталось выполнить {remaining} из {len(habits)} привычек", "/habits"))

            for title, body, url in messages:
                for sub in subs:
                    sub_info = {
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    }
                    result = send_push(sub_info, title, body, url)
                    if result == "gone":
                        db.delete(sub)
                        db.commit()
    finally:
        db.close()
