import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast";
import ConfirmModal from "./ConfirmModal";

const MUSCLE_GROUP_LABELS = {
  chest: "Грудь", back: "Спина", legs: "Ноги", shoulders: "Плечи",
  biceps: "Бицепс", triceps: "Трицепс", abs: "Пресс", cardio: "Кардио", other: "Другое",
};

export default function Gym() {
  const [workouts, setWorkouts] = useState([]);
  const [catalog, setCatalog] = useState({});
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [search, setSearch] = useState("");
  const [customExercise, setCustomExercise] = useState(false);
  const [form, setForm] = useState({
    exercise: "", weight: "", sets: "", reps: "", muscle_group: "chest", date: "",
  });
  const toast = useToast();

  const load = () => api.getWorkouts().then(setWorkouts);
  useEffect(() => {
    load();
    api.getExercises().then(setCatalog);
  }, []);

  const filtered = workouts.filter((w) =>
    w.exercise.toLowerCase().includes(search.toLowerCase()) ||
    w.muscle_group.toLowerCase().includes(search.toLowerCase())
  );

  const exercisesForGroup = catalog[form.muscle_group] || [];

  function openAdd() {
    setEditItem(null);
    setCustomExercise(false);
    setForm({ exercise: "", weight: "", sets: "", reps: "", muscle_group: "chest", date: "" });
    setShowModal(true);
  }

  function openEdit(w) {
    setEditItem(w);
    setCustomExercise(true);
    setForm({
      exercise: w.exercise, weight: String(w.weight), sets: String(w.sets),
      reps: String(w.reps), muscle_group: w.muscle_group, date: w.date,
    });
    setShowModal(true);
  }

  async function handleExerciseSelect(exercise) {
    setForm((f) => ({ ...f, exercise }));
    if (!exercise || editItem) return;
    const last = await api.getLastWorkout(exercise);
    if (last) {
      setForm((f) => ({
        ...f,
        exercise,
        weight: String(last.weight),
        sets: String(last.sets),
        reps: String(last.reps),
      }));
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.exercise.trim()) return;
    const data = {
      exercise: form.exercise, weight: parseFloat(form.weight) || 0,
      sets: parseInt(form.sets) || 0, reps: parseInt(form.reps) || 0,
      muscle_group: form.muscle_group, date: form.date || null,
    };
    if (editItem) {
      await api.updateWorkout(editItem.id, data);
      toast("Workout updated");
    } else {
      await api.createWorkout(data);
      toast("Workout recorded");
    }
    setShowModal(false);
    load();
  }

  async function confirmDelete() {
    await api.deleteWorkout(deleteId);
    setDeleteId(null);
    toast("Workout deleted", "error");
    load();
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Gym</h2>
          <button className="btn btn-primary" onClick={openAdd}>+ Add</button>
        </div>

        <div className="search-wrapper">
          <input className="search-bar" placeholder="Search exercises..."
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <p>{search ? "No matching workouts" : "No workouts recorded"}</p>
            {!search && <button className="btn btn-primary" onClick={openAdd}>Add your first workout</button>}
          </div>
        ) : (
          <table className="workout-table">
            <thead>
              <tr><th>Date</th><th>Exercise</th><th>kg</th><th>Sets</th><th>Reps</th><th>Group</th><th></th></tr>
            </thead>
            <tbody>
              {filtered.map((w) => (
                <tr key={w.id}>
                  <td>{w.date}</td>
                  <td>{w.exercise}</td>
                  <td>{w.weight}</td>
                  <td>{w.sets}</td>
                  <td>{w.reps}</td>
                  <td><span className="muscle-badge">{MUSCLE_GROUP_LABELS[w.muscle_group] || w.muscle_group}</span></td>
                  <td style={{ display: "flex", gap: 4 }}>
                    <button className="btn btn-danger" onClick={() => openEdit(w)} style={{ color: "var(--cyan)" }}>{"\u270e"}</button>
                    <button className="btn btn-danger" onClick={() => setDeleteId(w.id)}>{"\u2715"}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editItem ? "Edit Workout" : "Add Workout"}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Muscle group</label>
                <select value={form.muscle_group}
                  onChange={(e) => {
                    setForm({ ...form, muscle_group: e.target.value, exercise: "" });
                    setCustomExercise(false);
                  }}>
                  {Object.entries(MUSCLE_GROUP_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Exercise</label>
                {!customExercise && exercisesForGroup.length > 0 ? (
                  <>
                    <select value={form.exercise}
                      onChange={(e) => {
                        if (e.target.value === "__custom__") {
                          setCustomExercise(true);
                          setForm({ ...form, exercise: "" });
                        } else {
                          handleExerciseSelect(e.target.value);
                        }
                      }}>
                      <option value="">-- Выберите упражнение --</option>
                      {exercisesForGroup.map((ex) => (
                        <option key={ex} value={ex}>{ex}</option>
                      ))}
                      <option value="__custom__">Своё упражнение...</option>
                    </select>
                  </>
                ) : (
                  <div style={{ display: "flex", gap: 8 }}>
                    <input autoFocus placeholder="Название упражнения" value={form.exercise}
                      onChange={(e) => setForm({ ...form, exercise: e.target.value })}
                      style={{ flex: 1 }} />
                    {!editItem && exercisesForGroup.length > 0 && (
                      <button type="button" className="btn" onClick={() => setCustomExercise(false)}>Каталог</button>
                    )}
                  </div>
                )}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label>Weight (kg)</label>
                  <input type="number" step="0.5" placeholder="0" value={form.weight}
                    onChange={(e) => setForm({ ...form, weight: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Sets</label>
                  <input type="number" placeholder="0" value={form.sets}
                    onChange={(e) => setForm({ ...form, sets: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Reps</label>
                  <input type="number" placeholder="0" value={form.reps}
                    onChange={(e) => setForm({ ...form, reps: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label>Date</label>
                <input type="date" value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })} />
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
        <ConfirmModal title="Delete Workout" message="This action cannot be undone."
          onConfirm={confirmDelete} onCancel={() => setDeleteId(null)} />
      )}
    </div>
  );
}
