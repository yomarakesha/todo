import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast";
import ConfirmModal from "./ConfirmModal";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getWeekDates() {
  const today = new Date();
  const day = today.getDay();
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((day + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

function getStreak(log) {
  let d = new Date();
  let n = 0;
  while (log[d.toISOString().slice(0, 10)]) {
    n++;
    d.setDate(d.getDate() - 1);
  }
  return n;
}

export default function Habits() {
  const [habits, setHabits] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [name, setName] = useState("");
  const toast = useToast();

  const load = () => api.getHabits().then(setHabits);
  useEffect(() => { load(); }, []);

  const week = getWeekDates();
  const today = new Date().toISOString().slice(0, 10);

  function openAdd() {
    setEditItem(null);
    setName("");
    setShowModal(true);
  }

  function openEdit(h) {
    setEditItem(h);
    setName(h.name);
    setShowModal(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    if (editItem) {
      await api.updateHabit(editItem.id, { name: name.trim() });
      toast("Habit updated");
    } else {
      await api.createHabit({ name: name.trim() });
      toast("Habit added");
    }
    setShowModal(false);
    load();
  }

  async function toggle(habitId) {
    const res = await api.toggleHabit(habitId);
    toast(res.done ? "Habit done!" : "Habit unchecked", res.done ? "success" : "info");
    load();
  }

  async function confirmDelete() {
    await api.deleteHabit(deleteId);
    setDeleteId(null);
    toast("Habit deleted", "error");
    load();
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Habits</h2>
          <button className="btn btn-primary" onClick={openAdd}>+ Add</button>
        </div>

        {habits.length === 0 ? (
          <div className="empty">
            <p>No habits tracked</p>
            <button className="btn btn-primary" onClick={openAdd}>Add your first habit</button>
          </div>
        ) : (
          <>
            <div className="week-header">
              <div className="habit-name">Habit</div>
              <div className="habit-week">
                {DAY_NAMES.map((d, i) => (
                  <div key={i} className="day-label">{d}</div>
                ))}
              </div>
              <div className="habit-streak" style={{ color: "var(--text-dim)", fontWeight: 400, fontSize: 12 }}>Streak</div>
              <div className="habit-actions" />
            </div>

            {habits.map((h) => {
              const streak = getStreak(h.log);
              return (
                <div key={h.id} className="habit-row">
                  <div className="habit-name">{h.name}</div>
                  <div className="habit-week">
                    {week.map((d) => {
                      const isDone = h.log[d];
                      const isToday = d === today;
                      const isFuture = d > today;
                      return (
                        <div
                          key={d}
                          className={`habit-day${isDone ? " done" : ""}${isToday ? " today" : ""}${isFuture ? " future" : ""}`}
                          onClick={() => { if (isToday) toggle(h.id); }}
                        >
                          {isDone ? "\u2713" : "\u00b7"}
                        </div>
                      );
                    })}
                  </div>
                  <div className="habit-streak">{streak}d</div>
                  <div className="habit-actions" style={{ display: "flex", gap: 2 }}>
                    <button className="btn btn-danger" onClick={() => openEdit(h)} style={{ color: "var(--cyan)", fontSize: 12 }}>{"\u270e"}</button>
                    <button className="btn btn-danger" onClick={() => setDeleteId(h.id)} style={{ fontSize: 12 }}>{"\u2715"}</button>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editItem ? "Edit Habit" : "Add Habit"}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Habit name</label>
                <input autoFocus placeholder="e.g. Meditate" value={name}
                  onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editItem ? "Save" : "Add"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteId && (
        <ConfirmModal title="Delete Habit" message="All history will be lost."
          onConfirm={confirmDelete} onCancel={() => setDeleteId(null)} />
      )}
    </div>
  );
}
