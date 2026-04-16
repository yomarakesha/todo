#!/usr/bin/env python3
"""
Life Tracker — полнофункциональное TUI-приложение для продуктивности.

Модули: Dashboard · TODO · GYM · HABITS · POMODORO
Управление: только клавиатура, без мыши.
Стек: Rich (рендер) + readchar (ввод) + threading (таймер).
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import readchar
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

DATA_PATH = Path.home() / ".life_tracker.json"

BANNER = r"""
 ╦  ╦╔═╗╔═╗  ╔╦╗╦═╗╔═╗╔═╗╦╔═╔═╗╦═╗
 ║  ║╠╣ ║╣    ║ ╠╦╝╠═╣║  ╠╩╗║╣ ╠╦╝
 ╩═╝╩╚  ╚═╝   ╩ ╩╚═╩ ╩╚═╝╩ ╩╚═╝╩╚═
"""

TIPS = [
    "Small steps every day lead to big results.",
    "Don't break the chain — keep your streaks alive!",
    "The best workout is the one you actually do.",
    "Focus on progress, not perfection.",
    "One task at a time. You've got this.",
    "Discipline is choosing between what you want now and what you want most.",
    "The secret of getting ahead is getting started.",
    "Rest when you must, but never quit.",
]

PRIORITIES = ["low", "medium", "high"]
PRIORITY_COLORS = {"low": "green", "medium": "yellow", "high": "red"}
PRIORITY_ICONS = {"low": "◇", "medium": "◆", "high": "◈"}

MUSCLE_GROUPS = ["chest", "back", "shoulders", "arms", "legs", "core", "cardio", "other"]

SPARK = "▁▂▃▄▅▆▇█"

FILTERS = ["all", "active", "done"]

# ═══════════════════════════════════════════════════════════════
# Data helpers
# ═══════════════════════════════════════════════════════════════


def _load() -> dict[str, Any]:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"todos": [], "workouts": [], "habits": [],
            "pomodoro": {"work": 25, "brk": 5, "long_brk": 15, "sessions": {}}}


def _save(d: dict[str, Any]) -> None:
    DATA_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _sparkline(vals: list[float]) -> str:
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    rng = hi - lo or 1
    return "".join(SPARK[min(int((v - lo) / rng * 7), 7)] for v in vals)


def _streak(log: dict[str, bool]) -> int:
    d = datetime.now().date()
    n = 0
    while log.get(d.strftime("%Y-%m-%d")):
        n += 1
        d -= timedelta(days=1)
    return n


def _week_dates() -> list[str]:
    t = datetime.now().date()
    mon = t - timedelta(days=t.weekday())
    return [(mon + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]


def _tip_of_the_day() -> str:
    idx = int(datetime.now().strftime("%j")) % len(TIPS)
    return TIPS[idx]


# ═══════════════════════════════════════════════════════════════
# Form system  (text input built on readchar)
# ═══════════════════════════════════════════════════════════════


class FormField:
    def __init__(self, key: str, label: str, ftype: str = "text",
                 options: list[str] | None = None, default: str = "",
                 placeholder: str = ""):
        self.key = key
        self.label = label
        self.ftype = ftype          # text | number | select | date
        self.options = options or []
        self.value = default
        self.placeholder = placeholder
        self.sel = 0
        if ftype == "select" and default in self.options:
            self.sel = self.options.index(default)
            self.value = default
        elif ftype == "select" and self.options:
            self.value = self.options[0]


class Form:
    def __init__(self, title: str, fields: list[FormField], kind: str = ""):
        self.title = title
        self.fields = fields
        self.idx = 0
        self.kind = kind
        self.submitted = False
        self.cancelled = False

    @property
    def cur(self) -> FormField:
        return self.fields[self.idx]

    def handle(self, key: str) -> None:
        if key == readchar.key.ESC or key == "\x1b":
            self.cancelled = True
            return
        if key in (readchar.key.ENTER, "\r", "\n"):
            if self.idx < len(self.fields) - 1:
                self.idx += 1
            else:
                self.submitted = True
            return
        if key == "\t":
            self.idx = (self.idx + 1) % len(self.fields)
            return

        f = self.cur
        if f.ftype == "select":
            if key in (readchar.key.LEFT, readchar.key.UP):
                f.sel = (f.sel - 1) % len(f.options)
                f.value = f.options[f.sel]
            elif key in (readchar.key.RIGHT, readchar.key.DOWN):
                f.sel = (f.sel + 1) % len(f.options)
                f.value = f.options[f.sel]
            return

        if key in (readchar.key.BACKSPACE, "\x7f", "\x08"):
            f.value = f.value[:-1]
        elif len(key) == 1 and key.isprintable():
            if f.ftype == "number":
                if key.isdigit() or (key == "." and "." not in f.value):
                    f.value += key
            else:
                f.value += key

    def vals(self) -> dict[str, str]:
        return {f.key: f.value for f in self.fields}

    def render(self) -> Panel:
        parts: list[Text] = []
        for i, f in enumerate(self.fields):
            active = i == self.idx
            pfx = ">> " if active else "   "
            color = "cyan bold" if active else "white"
            parts.append(Text.from_markup(f"[{color}]{pfx}{f.label}[/{color}]"))
            if f.ftype == "select":
                left = " <" if active else "  "
                right = ">" if active else " "
                parts.append(Text.from_markup(f"    {left} {f.options[f.sel]} {right}"))
            else:
                cur = "█" if active else ""
                shown = f.value if f.value else f"[dim]{f.placeholder}[/dim]"
                parts.append(Text.from_markup(f"    {shown}{cur}"))
            parts.append(Text(""))
        parts.append(Text.from_markup("[dim]Tab/Enter: next  |  Esc: cancel[/dim]"))
        return Panel(Group(*parts), title=f"[bold cyan] {self.title} [/bold cyan]",
                     border_style="cyan", width=54, padding=(1, 2))


# ═══════════════════════════════════════════════════════════════
# Application
# ═══════════════════════════════════════════════════════════════


class App:
    def __init__(self) -> None:
        self.data = _load()
        self.running = True
        self.screen = "dashboard"
        self.keys: queue.Queue[str] = queue.Queue()

        # cursors
        self.todo_cur = 0
        self.gym_cur = 0
        self.hab_cur = 0
        self.todo_filter = "all"

        # form
        self.form: Form | None = None

        # confirm-delete
        self.confirming = False

        # help overlay
        self.show_help = False

        # notifications
        self._note = ""
        self._note_t = 0.0

        # pomodoro state
        self.pomo_state = "idle"      # idle | running | paused | done
        self.pomo_mode = "work"       # work | break
        self.pomo_left = self.data["pomodoro"]["work"] * 60.0
        self.pomo_tick = 0.0
        self._sync_pomo_sessions()

    # ── helpers ────────────────────────────────────────

    def notify(self, msg: str, dur: float = 2.5) -> None:
        self._note = msg
        self._note_t = time.time() + dur

    @property
    def note(self) -> str:
        return self._note if time.time() < self._note_t else ""

    def _sync_pomo_sessions(self) -> None:
        self.pomo_today = self.data["pomodoro"].get("sessions", {}).get(_today(), 0)

    def _filtered_todos(self) -> list[tuple[int, dict]]:
        out = []
        for i, t in enumerate(self.data["todos"]):
            if self.todo_filter == "active" and t["done"]:
                continue
            if self.todo_filter == "done" and not t["done"]:
                continue
            out.append((i, t))
        return out

    def _clamp_cursors(self) -> None:
        ft = self._filtered_todos()
        if ft:
            self.todo_cur = max(0, min(self.todo_cur, len(ft) - 1))
        else:
            self.todo_cur = 0
        wk = self.data["workouts"]
        self.gym_cur = max(0, min(self.gym_cur, len(wk) - 1)) if wk else 0
        hb = self.data["habits"]
        self.hab_cur = max(0, min(self.hab_cur, len(hb) - 1)) if hb else 0

    # ── pomodoro tick (called every render cycle) ─────

    def _pomo_tick(self) -> None:
        if self.pomo_state != "running":
            return
        now = time.time()
        self.pomo_left -= now - self.pomo_tick
        self.pomo_tick = now
        if self.pomo_left <= 0:
            self.pomo_left = 0
            self.pomo_state = "done"
            sys.stdout.write("\a")
            sys.stdout.flush()
            if self.pomo_mode == "work":
                sess = self.data["pomodoro"].setdefault("sessions", {})
                sess[_today()] = sess.get(_today(), 0) + 1
                _save(self.data)
                self._sync_pomo_sessions()
                self.notify("Work session complete! Take a break.")
            else:
                self.notify("Break over! Time to focus.")

    # ── key handling ──────────────────────────────────

    def handle(self, key: str) -> None:
        # confirm delete
        if self.confirming:
            self.confirming = False
            if key in ("y", "Y"):
                self._do_delete()
            else:
                self.notify("Cancelled")
            return

        # form input
        if self.form:
            self.form.handle(key)
            if self.form.submitted:
                self._on_form_submit()
            elif self.form.cancelled:
                self.form = None
            return

        # help overlay
        if self.show_help:
            self.show_help = False
            return

        # global
        if key in ("q", "Q"):
            self.running = False
            return
        if key == "?":
            self.show_help = True
            return

        # number navigation (always available)
        if key == "1":
            self.screen = "todo"; return
        if key == "2":
            self.screen = "gym"; return
        if key == "3":
            self.screen = "habits"; return
        if key == "4":
            self.screen = "pomodoro"; return

        # back
        if key in ("b", "B") or (key == readchar.key.ESC):
            if self.screen != "dashboard":
                self.screen = "dashboard"
                return

        # dispatch per screen
        handler = getattr(self, f"_key_{self.screen}", None)
        if handler:
            handler(key)

    # ── per-screen key handlers ───────────────────────

    def _key_dashboard(self, key: str) -> None:
        pass  # 1-4 handled globally

    def _key_todo(self, key: str) -> None:
        ft = self._filtered_todos()
        if key in (readchar.key.UP, "k", "K") and ft:
            self.todo_cur = max(0, self.todo_cur - 1)
        elif key in (readchar.key.DOWN, "j", "J") and ft:
            self.todo_cur = min(len(ft) - 1, self.todo_cur + 1)
        elif key in ("a", "A"):
            self.form = Form("Add Task", [
                FormField("text", "Task", placeholder="What needs to be done?"),
                FormField("priority", "Priority", "select", PRIORITIES, "medium"),
                FormField("due", "Due date", "date", placeholder="YYYY-MM-DD (empty = none)"),
            ], kind="add_todo")
        elif key in ("d", "D", readchar.key.DELETE) and ft:
            self.confirming = True
        elif key == " " and ft:
            real_idx = ft[self.todo_cur][0]
            self.data["todos"][real_idx]["done"] = not self.data["todos"][real_idx]["done"]
            _save(self.data)
            self.notify("Toggled")
        elif key in ("f", "F"):
            ci = FILTERS.index(self.todo_filter)
            self.todo_filter = FILTERS[(ci + 1) % len(FILTERS)]
            self.todo_cur = 0
            self.notify(f"Filter: {self.todo_filter}")

    def _key_gym(self, key: str) -> None:
        wk = self.data["workouts"]
        if key in (readchar.key.UP, "k", "K") and wk:
            self.gym_cur = max(0, self.gym_cur - 1)
        elif key in (readchar.key.DOWN, "j", "J") and wk:
            self.gym_cur = min(len(wk) - 1, self.gym_cur + 1)
        elif key in ("a", "A"):
            self.form = Form("Add Workout", [
                FormField("exercise", "Exercise", placeholder="e.g. Bench Press"),
                FormField("weight", "Weight (kg)", "number", placeholder="0"),
                FormField("sets", "Sets", "number", placeholder="0"),
                FormField("reps", "Reps", "number", placeholder="0"),
                FormField("group", "Muscle group", "select", MUSCLE_GROUPS, "chest"),
                FormField("date", "Date", "date", placeholder=f"empty = {_today()}"),
            ], kind="add_workout")
        elif key in ("d", "D", readchar.key.DELETE) and wk:
            self.confirming = True
        elif key in ("s", "S") and wk:
            self._show_gym_stats()

    def _key_habits(self, key: str) -> None:
        hb = self.data["habits"]
        if key in (readchar.key.UP, "k", "K") and hb:
            self.hab_cur = max(0, self.hab_cur - 1)
        elif key in (readchar.key.DOWN, "j", "J") and hb:
            self.hab_cur = min(len(hb) - 1, self.hab_cur + 1)
        elif key in ("a", "A"):
            self.form = Form("Add Habit", [
                FormField("name", "Habit name", placeholder="e.g. Meditate"),
            ], kind="add_habit")
        elif key in ("d", "D", readchar.key.DELETE) and hb:
            self.confirming = True
        elif key == " " and hb:
            h = hb[self.hab_cur]
            td = _today()
            h.setdefault("log", {})
            h["log"][td] = not h["log"].get(td, False)
            _save(self.data)
            st = "done" if h["log"][td] else "undone"
            self.notify(f"{h['name']} — {st}")

    def _key_pomodoro(self, key: str) -> None:
        if key in ("s", "S", " "):
            if self.pomo_state == "idle":
                self.pomo_state = "running"
                self.pomo_tick = time.time()
                self.notify("Timer started")
            elif self.pomo_state == "running":
                self.pomo_state = "paused"
                self.notify("Paused")
            elif self.pomo_state == "paused":
                self.pomo_state = "running"
                self.pomo_tick = time.time()
                self.notify("Resumed")
            elif self.pomo_state == "done":
                # advance to next mode
                if self.pomo_mode == "work":
                    long = (self.pomo_today % 4 == 0 and self.pomo_today > 0)
                    self.pomo_mode = "break"
                    mins = self.data["pomodoro"]["long_brk"] if long else self.data["pomodoro"]["brk"]
                else:
                    self.pomo_mode = "work"
                    mins = self.data["pomodoro"]["work"]
                self.pomo_left = mins * 60
                self.pomo_state = "running"
                self.pomo_tick = time.time()
                self.notify(f"{'Long break' if self.pomo_mode == 'break' and mins > 5 else self.pomo_mode.title()} — {mins} min")
        elif key in ("r", "R"):
            mins = self.data["pomodoro"]["work"] if self.pomo_mode == "work" else self.data["pomodoro"]["brk"]
            self.pomo_left = mins * 60
            self.pomo_state = "idle"
            self.notify("Reset")
        elif key == "+" and self.pomo_state == "idle":
            self.data["pomodoro"]["work"] = min(90, self.data["pomodoro"]["work"] + 1)
            self.pomo_left = self.data["pomodoro"]["work"] * 60
            _save(self.data)
        elif key == "-" and self.pomo_state == "idle":
            self.data["pomodoro"]["work"] = max(1, self.data["pomodoro"]["work"] - 1)
            self.pomo_left = self.data["pomodoro"]["work"] * 60
            _save(self.data)

    # ── delete dispatch ───────────────────────────────

    def _do_delete(self) -> None:
        if self.screen == "todo":
            ft = self._filtered_todos()
            if ft and self.todo_cur < len(ft):
                real = ft[self.todo_cur][0]
                removed = self.data["todos"].pop(real)
                _save(self.data)
                self._clamp_cursors()
                self.notify(f"Deleted: {removed['text']}")
        elif self.screen == "gym":
            wk = self.data["workouts"]
            if wk and self.gym_cur < len(wk):
                removed = wk.pop(self.gym_cur)
                _save(self.data)
                self._clamp_cursors()
                self.notify(f"Deleted: {removed['exercise']}")
        elif self.screen == "habits":
            hb = self.data["habits"]
            if hb and self.hab_cur < len(hb):
                removed = hb.pop(self.hab_cur)
                _save(self.data)
                self._clamp_cursors()
                self.notify(f"Deleted: {removed['name']}")

    # ── gym stats popup (rendered as special screen) ──

    def _show_gym_stats(self) -> None:
        wk = self.data["workouts"]
        if not wk:
            return
        ex = wk[self.gym_cur]["exercise"]
        records = [w for w in wk if w["exercise"] == ex]
        records.sort(key=lambda w: w["date"])
        self.notify(
            f"  {ex}  |  Sessions: {len(records)}  |  "
            f"Max: {max(r['weight'] for r in records)}kg  |  "
            f"Progress: {_sparkline([r['weight'] for r in records])}  |  "
            f"Last: {records[-1]['date']} {records[-1]['weight']}kg "
            f"{records[-1]['sets']}x{records[-1]['reps']}",
            dur=6,
        )

    # ── form submit ───────────────────────────────────

    def _on_form_submit(self) -> None:
        if not self.form:
            return
        v = self.form.vals()
        kind = self.form.kind
        self.form = None

        if kind == "add_todo":
            if not v["text"].strip():
                self.notify("Task text required"); return
            self.data["todos"].append({
                "id": _uid(), "text": v["text"].strip(),
                "done": False, "priority": v["priority"],
                "due": v["due"].strip() or "", "created": _today(),
            })
            _save(self.data)
            self.notify(f"Added: {v['text'].strip()}")

        elif kind == "add_workout":
            if not v["exercise"].strip():
                self.notify("Exercise name required"); return
            self.data["workouts"].append({
                "id": _uid(), "exercise": v["exercise"].strip(),
                "weight": float(v["weight"] or 0),
                "sets": int(v["sets"] or 0), "reps": int(v["reps"] or 0),
                "group": v["group"], "date": v["date"].strip() or _today(),
            })
            _save(self.data)
            self.notify(f"Recorded: {v['exercise'].strip()}")

        elif kind == "add_habit":
            if not v["name"].strip():
                self.notify("Habit name required"); return
            self.data["habits"].append({
                "id": _uid(), "name": v["name"].strip(), "log": {},
            })
            _save(self.data)
            self.notify(f"Habit added: {v['name'].strip()}")

    # ══════════════════════════════════════════════════
    # Rendering
    # ══════════════════════════════════════════════════

    def render(self) -> Group:
        self._pomo_tick()
        self._clamp_cursors()

        if self.show_help:
            body = self._r_help()
        elif self.form:
            body = Align.center(self.form.render(), vertical="middle")
        elif self.screen == "dashboard":
            body = self._r_dash()
        elif self.screen == "todo":
            body = self._r_todo()
        elif self.screen == "gym":
            body = self._r_gym()
        elif self.screen == "habits":
            body = self._r_habits()
        elif self.screen == "pomodoro":
            body = self._r_pomo()
        else:
            body = Text("Unknown screen")

        status = self._r_status()
        return Group(body, Text(""), status)

    # ── dashboard ─────────────────────────────────────

    def _r_dash(self) -> Panel:
        parts: list[Any] = []

        # banner
        parts.append(Align.center(Text(BANNER, style="bold cyan")))
        parts.append(Align.center(Text(f'"{_tip_of_the_day()}"', style="italic dim")))
        parts.append(Text(""))

        # stat cards in a 2×2 grid (using a table)
        grid = Table.grid(padding=(0, 2))
        grid.add_column(min_width=28)
        grid.add_column(min_width=28)

        # TODO card
        todos = self.data["todos"]
        active = sum(1 for t in todos if not t["done"])
        done_today = sum(1 for t in todos if t["done"])
        overdue = sum(1 for t in todos if not t["done"] and t.get("due") and t["due"] < _today())
        todo_lines = f"  Active: {active}\n  Done: {done_today}"
        if overdue:
            todo_lines += f"\n  [red]Overdue: {overdue}[/red]"
        todo_card = Panel(Text.from_markup(todo_lines), title="[bold green][1] TODO[/bold green]",
                          border_style="green", width=28, height=7)

        # GYM card
        wk = self.data["workouts"]
        week_start = (datetime.now().date() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        this_week = sum(1 for w in wk if w["date"] >= week_start)
        last_ex = wk[-1]["exercise"] if wk else "—"
        max_w = max((w["weight"] for w in wk), default=0)
        gym_lines = f"  This week: {this_week}\n  Last: {last_ex}\n  Max weight: {max_w}kg"
        gym_card = Panel(Text.from_markup(gym_lines), title="[bold blue][2] GYM[/bold blue]",
                         border_style="blue", width=28, height=7)

        # HABITS card
        hbs = self.data["habits"]
        best = max((_streak(h.get("log", {})) for h in hbs), default=0) if hbs else 0
        done_h = sum(1 for h in hbs if h.get("log", {}).get(_today()))
        hab_lines = f"  Tracking: {len(hbs)}\n  Done today: {done_h}/{len(hbs)}\n  Best streak: {best}d"
        hab_card = Panel(Text.from_markup(hab_lines), title="[bold magenta][3] HABITS[/bold magenta]",
                         border_style="magenta", width=28, height=7)

        # POMO card
        m, s = divmod(int(self.pomo_left), 60)
        state_txt = {"idle": "IDLE", "running": "RUNNING", "paused": "PAUSED", "done": "TIME'S UP"}
        pomo_lines = (f"  {m:02d}:{s:02d}  {state_txt[self.pomo_state]}\n"
                      f"  Mode: {self.pomo_mode.upper()}\n"
                      f"  Today: {self.pomo_today} sessions")
        pomo_card = Panel(Text.from_markup(pomo_lines), title="[bold yellow][4] POMODORO[/bold yellow]",
                          border_style="yellow", width=28, height=7)

        grid.add_row(todo_card, gym_card)
        grid.add_row(hab_card, pomo_card)
        parts.append(Align.center(grid))

        parts.append(Text(""))
        parts.append(Align.center(Text.from_markup(
            "[dim][1-4] Navigate    [?] Help    [Q] Quit[/dim]")))

        return Panel(Group(*parts), border_style="bright_cyan", padding=(1, 2))

    # ── todo ──────────────────────────────────────────

    def _r_todo(self) -> Panel:
        ft = self._filtered_todos()
        todos = self.data["todos"]
        total = len(todos)
        done_n = sum(1 for t in todos if t["done"])

        # progress
        pct = (done_n / total * 100) if total else 0
        bar_w = 20
        filled = int(pct / 100 * bar_w)
        bar = f"[green]{'█' * filled}[/green][dim]{'░' * (bar_w - filled)}[/dim] {pct:.0f}%"

        header = Text.from_markup(
            f"  Filter: [bold cyan]{self.todo_filter.upper()}[/bold cyan]"
            f"    {bar}    Total: {total}\n"
        )

        if not ft:
            body = Text.from_markup("\n  [dim]No tasks. Press [bold]A[/bold] to add one.[/dim]\n")
        else:
            tbl = Table(box=None, pad_edge=False, show_header=True,
                        header_style="bold dim", expand=True)
            tbl.add_column("", width=3)
            tbl.add_column("Pri", width=4)
            tbl.add_column("Task", ratio=1)
            tbl.add_column("Due", width=12)
            tbl.add_column("Done", width=5)
            for vi, (ri, t) in enumerate(ft):
                pri_c = PRIORITY_COLORS[t["priority"]]
                pri_i = PRIORITY_ICONS[t["priority"]]
                check = "[x]" if t["done"] else "[ ]"
                due = t.get("due", "")
                due_style = ""
                if due and not t["done"] and due < _today():
                    due_style = "bold red"
                style = "reverse" if vi == self.todo_cur else ""
                text_style = "strike dim" if t["done"] else ""
                tbl.add_row(
                    Text(f" {vi+1}", style=style),
                    Text(f" {pri_i}", style=f"{pri_c} {style}"),
                    Text(f" {t['text']}", style=f"{text_style} {style}"),
                    Text(f" {due}", style=f"{due_style} {style}"),
                    Text(f" {check}", style=style),
                )
            body = tbl

        hints = Text.from_markup(
            "\n[dim]  [A]dd  [D]elete  [Space]Toggle  [F]ilter  "
            "[J/K]Move  [B]ack  [?]Help[/dim]")

        return Panel(Group(header, body, hints),
                     title="[bold green] TODO [/bold green]",
                     border_style="green", padding=(1, 1))

    # ── gym ───────────────────────────────────────────

    def _r_gym(self) -> Panel:
        wk = self.data["workouts"]

        if not wk:
            body = Text.from_markup("\n  [dim]No workouts. Press [bold]A[/bold] to add one.[/dim]\n")
            spark_panel = Text("")
        else:
            tbl = Table(box=None, pad_edge=False, show_header=True,
                        header_style="bold dim", expand=True)
            tbl.add_column("", width=3)
            tbl.add_column("Date", width=12)
            tbl.add_column("Exercise", ratio=1)
            tbl.add_column("kg", width=7)
            tbl.add_column("Sets", width=5)
            tbl.add_column("Reps", width=5)
            tbl.add_column("Group", width=10)
            for i, w in enumerate(wk):
                st = "reverse" if i == self.gym_cur else ""
                tbl.add_row(
                    Text(f" {i+1}", style=st),
                    Text(f" {w['date']}", style=st),
                    Text(f" {w['exercise']}", style=st),
                    Text(f" {w['weight']}", style=st),
                    Text(f" {w['sets']}", style=st),
                    Text(f" {w['reps']}", style=st),
                    Text(f" {w.get('group', '')}", style=st),
                )
            body = tbl

            # sparkline for selected exercise
            sel_ex = wk[self.gym_cur]["exercise"]
            recs = sorted([w for w in wk if w["exercise"] == sel_ex], key=lambda w: w["date"])
            weights = [r["weight"] for r in recs]
            sp = _sparkline(weights)
            mx = max(weights) if weights else 0
            spark_panel = Text.from_markup(
                f"\n  [bold]{sel_ex}[/bold]  "
                f"Progress: [cyan]{sp}[/cyan]  "
                f"Max: [green]{mx}kg[/green]  "
                f"Sessions: {len(recs)}"
            )

        hints = Text.from_markup(
            "\n[dim]  [A]dd  [D]elete  [S]tats  [J/K]Move  [B]ack  [?]Help[/dim]")

        return Panel(Group(body, spark_panel, hints),
                     title="[bold blue] GYM [/bold blue]",
                     border_style="blue", padding=(1, 1))

    # ── habits ────────────────────────────────────────

    def _r_habits(self) -> Panel:
        hbs = self.data["habits"]
        week = _week_dates()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        if not hbs:
            body = Text.from_markup("\n  [dim]No habits. Press [bold]A[/bold] to add one.[/dim]\n")
        else:
            tbl = Table(box=None, pad_edge=False, show_header=True,
                        header_style="bold dim", expand=True)
            tbl.add_column("", width=3)
            tbl.add_column("Habit", min_width=14)
            for dn in day_names:
                tbl.add_column(dn, width=5, justify="center")
            tbl.add_column("Streak", width=8, justify="right")

            for i, h in enumerate(hbs):
                st = "reverse" if i == self.hab_cur else ""
                log = h.get("log", {})
                day_cells: list[Text] = []
                for d in week:
                    if log.get(d):
                        day_cells.append(Text(" ✓ ", style=f"bold green {st}"))
                    elif d <= _today():
                        day_cells.append(Text(" · ", style=f"dim {st}"))
                    else:
                        day_cells.append(Text("   ", style=st))
                sk = _streak(log)
                sk_style = "bold yellow" if sk >= 7 else ("bold cyan" if sk >= 3 else "")
                tbl.add_row(
                    Text(f" {i+1}", style=st),
                    Text(f" {h['name']}", style=st),
                    *day_cells,
                    Text(f" {sk}d ", style=f"{sk_style} {st}"),
                )
            body = tbl

        hints = Text.from_markup(
            "\n[dim]  [A]dd  [D]elete  [Space]Toggle today  "
            "[J/K]Move  [B]ack  [?]Help[/dim]")

        return Panel(Group(body, hints),
                     title="[bold magenta] HABITS [/bold magenta]",
                     border_style="magenta", padding=(1, 1))

    # ── pomodoro ──────────────────────────────────────

    def _r_pomo(self) -> Panel:
        m, s = divmod(int(self.pomo_left), 60)
        time_str = f"{m:02d}:{s:02d}"

        state_map = {
            "idle": ("[dim]IDLE[/dim]", "dim"),
            "running": ("[bold green]RUNNING[/bold green]", "green"),
            "paused": ("[bold yellow]PAUSED[/bold yellow]", "yellow"),
            "done": ("[bold red blink]TIME'S UP[/bold red blink]", "red"),
        }
        state_label, timer_color = state_map[self.pomo_state]
        mode_label = "[bold]WORK[/bold]" if self.pomo_mode == "work" else "[bold cyan]BREAK[/bold cyan]"

        total_secs = (self.data["pomodoro"]["work"] if self.pomo_mode == "work"
                      else self.data["pomodoro"]["brk"]) * 60
        pct = self.pomo_left / total_secs if total_secs else 0
        bar_w = 24
        filled = int(pct * bar_w)
        bar = f"[{timer_color}]{'█' * filled}[/{timer_color}][dim]{'░' * (bar_w - filled)}[/dim]"

        timer_box = Panel(
            Align.center(Text.from_markup(
                f"[bold {timer_color}]{time_str}[/bold {timer_color}]\n{mode_label}"
            )),
            border_style=timer_color, width=20, height=5,
        )

        parts = [
            Text(""),
            Align.center(timer_box),
            Text(""),
            Align.center(Text.from_markup(state_label)),
            Align.center(Text.from_markup(bar)),
            Text(""),
            Align.center(Text.from_markup(
                f"Sessions today: [bold]{self.pomo_today}[/bold]    "
                f"Work: [bold]{self.data['pomodoro']['work']}[/bold]m    "
                f"Break: [bold]{self.data['pomodoro']['brk']}[/bold]m"
            )),
            Text(""),
            Align.center(Text.from_markup(
                "[dim][S/Space] Start/Pause  [R]eset  [+/-] Adjust  [B]ack[/dim]")),
        ]

        return Panel(Group(*parts),
                     title="[bold yellow] POMODORO [/bold yellow]",
                     border_style="yellow", padding=(1, 2))

    # ── help ──────────────────────────────────────────

    def _r_help(self) -> Panel:
        t = Text.from_markup("""
[bold cyan]NAVIGATION[/bold cyan]
  1 / 2 / 3 / 4    Go to TODO / GYM / HABITS / POMODORO
  B / Esc           Back to Dashboard
  ↑ / K  ↓ / J     Move cursor
  Q                 Quit
  ?                 Toggle this help

[bold green]TODO[/bold green]
  A                 Add task
  D / Delete        Delete selected task
  Space             Toggle done / undone
  F                 Cycle filter (all → active → done)

[bold blue]GYM[/bold blue]
  A                 Add workout
  D / Delete        Delete selected workout
  S                 Show stats for selected exercise

[bold magenta]HABITS[/bold magenta]
  A                 Add habit
  D / Delete        Delete selected habit
  Space             Toggle today's completion

[bold yellow]POMODORO[/bold yellow]
  S / Space         Start / Pause / Next
  R                 Reset timer
  + / -             Adjust work duration (±1 min)

[dim]Press any key to close[/dim]""")
        return Panel(t, title="[bold] HELP [/bold]",
                     border_style="bright_cyan", padding=(1, 2))

    # ── status bar ────────────────────────────────────

    def _r_status(self) -> Text:
        left = f" {self.screen.upper()}"
        if self.confirming:
            mid = "  [bold red]Delete? [Y/N][/bold red]"
        elif self.note:
            mid = f"  [bold green]{self.note}[/bold green]"
        else:
            mid = ""
        pomo = ""
        if self.pomo_state == "running":
            m, s = divmod(int(self.pomo_left), 60)
            pomo = f"  [yellow]⏱ {m:02d}:{s:02d}[/yellow]"
        return Text.from_markup(f"[reverse] {left}{mid}{pomo} [/reverse]")

    # ══════════════════════════════════════════════════
    # Main loop
    # ══════════════════════════════════════════════════

    def run(self) -> None:
        console = Console(highlight=False)

        def reader() -> None:
            while self.running:
                try:
                    k = readchar.readkey()
                    self.keys.put(k)
                except (KeyboardInterrupt, EOFError):
                    self.running = False
                    break

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        # Enter alternate screen manually (works on Win10+/WSL/SSH)
        sys.stdout.write("\033[?1049h")  # enter alt screen
        sys.stdout.write("\033[?25l")    # hide cursor
        sys.stdout.flush()

        try:
            while self.running:
                try:
                    key = self.keys.get(timeout=0.2)
                    self.handle(key)
                except queue.Empty:
                    pass

                # render: move to top-left and print
                sys.stdout.write("\033[H")  # cursor home
                sys.stdout.flush()
                console.print(self.render(), end="")
                # clear any leftover lines below
                sys.stdout.write("\033[J")
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[?25h")    # show cursor
            sys.stdout.write("\033[?1049l")  # exit alt screen
            sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    App().run()
