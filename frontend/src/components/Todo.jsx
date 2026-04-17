import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast";
import ConfirmModal from "./ConfirmModal";

const FILTERS = ["all", "active", "done"];
const SORT_OPTIONS = [
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "priority", label: "Priority" },
  { value: "due", label: "Due date" },
];
const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };

export default function Todo() {
  const [todos, setTodos] = useState([]);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [showModal, setShowModal] = useState(false);
  const [editTodo, setEditTodo] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [subtaskText, setSubtaskText] = useState("");
  const [showTemplates, setShowTemplates] = useState(false);
  const [templates, setTemplates] = useState({});
  const [form, setForm] = useState({ text: "", priority: "medium", due: "", category: "", recurrence: "" });
  const toast = useToast();

  const load = () => api.getTodos(filter).then(setTodos);
  useEffect(() => { load(); }, [filter]);

  let filtered = todos.filter((t) =>
    t.text.toLowerCase().includes(search.toLowerCase()) ||
    t.category.toLowerCase().includes(search.toLowerCase())
  );

  if (sort === "oldest") filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  if (sort === "priority") filtered.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
  if (sort === "due") filtered.sort((a, b) => (a.due || "9999") > (b.due || "9999") ? 1 : -1);

  const total = todos.length;
  const doneCount = todos.filter((t) => t.done).length;
  const pct = total ? Math.round((doneCount / total) * 100) : 0;
  const today = new Date().toISOString().slice(0, 10);

  function openAdd() {
    setEditTodo(null);
    setForm({ text: "", priority: "medium", due: "", category: "", recurrence: "" });
    setShowModal(true);
  }

  function openEdit(t) {
    setEditTodo(t);
    setForm({ text: t.text, priority: t.priority, due: t.due || "", category: t.category, recurrence: t.recurrence || "" });
    setShowModal(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.text.trim()) return;
    if (editTodo) {
      await api.updateTodo(editTodo.id, form);
      toast("Task updated");
    } else {
      await api.createTodo(form);
      toast("Task added");
    }
    setShowModal(false);
    load();
  }

  async function toggle(todo) {
    await api.updateTodo(todo.id, { done: !todo.done });
    toast(todo.done ? "Task reopened" : (todo.recurrence ? "Done! Next one created" : "Task done!"));
    load();
  }

  async function confirmDelete() {
    await api.deleteTodo(deleteId);
    setDeleteId(null);
    toast("Task deleted", "error");
    load();
  }

  async function addSubtask(todoId) {
    if (!subtaskText.trim()) return;
    await api.createSubtask(todoId, subtaskText.trim());
    setSubtaskText("");
    load();
  }

  async function toggleSubtask(todoId, subId) {
    await api.toggleSubtask(todoId, subId);
    load();
  }

  async function deleteSubtask(todoId, subId) {
    await api.deleteSubtask(todoId, subId);
    load();
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Todo</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select className="sort-select" value={sort} onChange={(e) => setSort(e.target.value)}>
              {SORT_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <div className="filter-tabs">
              {FILTERS.map((f) => (
                <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>
                  {f}
                </button>
              ))}
            </div>
            <button className="btn" onClick={async () => {
              const t = await api.getTodoTemplates();
              setTemplates(t);
              setShowTemplates(true);
            }}>Templates</button>
            <button className="btn btn-primary" onClick={openAdd}>+ Add</button>
          </div>
        </div>

        <div className="search-wrapper">
          <input
            className="search-bar"
            placeholder="Search tasks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="progress-bar">
          <div className="fill" style={{ width: `${pct}%` }} />
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <p>{search ? "No matching tasks" : "No tasks yet"}</p>
            {!search && (
              <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                <button className="btn" onClick={async () => {
                  const t = await api.getTodoTemplates();
                  setTemplates(t);
                  setShowTemplates(true);
                }}>Use template</button>
                <button className="btn btn-primary" onClick={openAdd}>Add your first task</button>
              </div>
            )}
          </div>
        ) : (
          filtered.map((t) => (
            <div key={t.id}>
              <div className={`todo-item ${t.done ? "done" : ""}`}>
                <div
                  className={`todo-checkbox ${t.done ? "checked" : ""}`}
                  onClick={() => toggle(t)}
                >
                  {t.done && "\u2713"}
                </div>
                <span
                  className="todo-text"
                  style={{ cursor: "pointer" }}
                  onClick={() => setExpandedId(expandedId === t.id ? null : t.id)}
                >
                  {t.text}
                  {t.recurrence && (
                    <span style={{ fontSize: 11, color: "var(--cyan)", marginLeft: 8 }}>
                      {"\u21bb"} {t.recurrence}
                    </span>
                  )}
                  {t.category && (
                    <span style={{ fontSize: 11, color: "var(--text-dim)", marginLeft: 8 }}>
                      #{t.category}
                    </span>
                  )}
                  {t.subtasks && t.subtasks.length > 0 && (
                    <span style={{ fontSize: 11, color: "var(--text-dim)", marginLeft: 8 }}>
                      [{t.subtasks.filter((s) => s.done).length}/{t.subtasks.length}]
                    </span>
                  )}
                </span>
                <span className={`priority-badge ${t.priority}`}>{t.priority}</span>
                {t.due && (
                  <span className={`todo-due ${!t.done && t.due < today ? "overdue" : ""}`}>
                    {t.due}
                  </span>
                )}
                <button className="btn btn-danger" onClick={() => openEdit(t)} style={{ color: "var(--cyan)" }}>
                  {"\u270e"}
                </button>
                <button className="btn btn-danger" onClick={() => setDeleteId(t.id)}>
                  {"\u2715"}
                </button>
              </div>

              {expandedId === t.id && (
                <div>
                  <div className="subtask-list">
                    {(t.subtasks || []).map((s) => (
                      <div key={s.id} className={`subtask-item ${s.done ? "done" : ""}`}>
                        <div
                          className={`subtask-checkbox ${s.done ? "checked" : ""}`}
                          onClick={() => toggleSubtask(t.id, s.id)}
                        >
                          {s.done && "\u2713"}
                        </div>
                        <span style={{ flex: 1 }}>{s.text}</span>
                        <button
                          className="btn btn-danger"
                          style={{ fontSize: 10, padding: "2px 4px" }}
                          onClick={() => deleteSubtask(t.id, s.id)}
                        >
                          {"\u2715"}
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="subtask-add">
                    <input
                      placeholder="Add subtask..."
                      value={subtaskText}
                      onChange={(e) => setSubtaskText(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && addSubtask(t.id)}
                    />
                    <button className="btn" style={{ padding: "4px 8px", fontSize: 12 }} onClick={() => addSubtask(t.id)}>
                      +
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editTodo ? "Edit Task" : "Add Task"}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Task</label>
                <input autoFocus placeholder="What needs to be done?" value={form.text}
                  onChange={(e) => setForm({ ...form, text: e.target.value })} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label>Priority</label>
                  <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Recurrence</label>
                  <select value={form.recurrence} onChange={(e) => setForm({ ...form, recurrence: e.target.value })}>
                    <option value="">None</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Due date</label>
                <input type="date" value={form.due} onChange={(e) => setForm({ ...form, due: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input placeholder="e.g. work, personal" value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editTodo ? "Save" : "Add"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTemplates && (
        <div className="modal-overlay" onClick={() => setShowTemplates(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Task Templates</h3>
            <div className="template-list">
              {Object.entries(templates).map(([key, name]) => (
                <button key={key} className="template-item" onClick={async () => {
                  await api.applyTodoTemplate(key);
                  toast("Template applied!");
                  setShowTemplates(false);
                  load();
                }}>
                  <span className="template-name">{name}</span>
                  <span className="template-arrow">{"\u2192"}</span>
                </button>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setShowTemplates(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {deleteId && (
        <ConfirmModal
          title="Delete Task"
          message="This action cannot be undone."
          onConfirm={confirmDelete}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </div>
  );
}
