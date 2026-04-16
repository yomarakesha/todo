import { useEffect, useState, useRef } from "react";
import { api } from "../api";
import { useToast } from "./Toast";
import ConfirmModal from "./ConfirmModal";

export default function Notes() {
  const [notes, setNotes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const saveTimer = useRef(null);
  const toast = useToast();

  const load = () => api.getNotes().then(setNotes);
  useEffect(() => { load(); }, []);

  function selectNote(note) {
    setSelected(note);
    setTitle(note.title);
    setContent(note.content);
  }

  async function createNew() {
    const today = new Date().toISOString().slice(0, 10);
    const note = await api.createNote({ title: today, content: "", date: today });
    await load();
    setSelected(note);
    setTitle(note.title);
    setContent(note.content);
    toast("Note created");
  }

  function handleChange(field, value) {
    if (field === "title") setTitle(value);
    else setContent(value);

    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      if (selected) {
        const data = field === "title" ? { title: value } : { content: value };
        api.updateNote(selected.id, data).then(() => load());
      }
    }, 500);
  }

  async function confirmDelete() {
    await api.deleteNote(deleteId);
    setDeleteId(null);
    if (selected && selected.id === deleteId) {
      setSelected(null);
      setTitle("");
      setContent("");
    }
    toast("Note deleted", "error");
    load();
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Notes</h2>
          <button className="btn btn-primary" onClick={createNew}>+ New</button>
        </div>

        {notes.length === 0 && !selected ? (
          <div className="empty">
            <p>No notes yet</p>
            <button className="btn btn-primary" onClick={createNew}>Write your first note</button>
          </div>
        ) : (
          <div className="notes-grid">
            <div className="notes-list">
              {notes.map((n) => (
                <div
                  key={n.id}
                  className={`note-item ${selected?.id === n.id ? "active" : ""}`}
                  onClick={() => selectNote(n)}
                >
                  <div className="note-date">{n.date}</div>
                  <div className="note-preview">{n.title || "Untitled"}</div>
                  <button
                    className="btn btn-danger"
                    style={{ fontSize: 10, padding: "2px 4px", marginTop: 4 }}
                    onClick={(e) => { e.stopPropagation(); setDeleteId(n.id); }}
                  >
                    {"\u2715"}
                  </button>
                </div>
              ))}
            </div>

            <div className="note-editor">
              {selected ? (
                <>
                  <div className="form-group">
                    <input
                      style={{
                        width: "100%", padding: "10px 14px", background: "var(--bg)",
                        border: "1px solid var(--border)", borderRadius: 8,
                        color: "var(--text)", fontSize: 18, fontWeight: 600, outline: "none",
                        marginBottom: 12,
                      }}
                      value={title}
                      onChange={(e) => handleChange("title", e.target.value)}
                      placeholder="Title"
                    />
                  </div>
                  <textarea
                    value={content}
                    onChange={(e) => handleChange("content", e.target.value)}
                    placeholder="Write your thoughts..."
                  />
                </>
              ) : (
                <div className="empty">
                  <p>Select a note or create a new one</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {deleteId && (
        <ConfirmModal title="Delete Note" message="This action cannot be undone."
          onConfirm={confirmDelete} onCancel={() => setDeleteId(null)} />
      )}
    </div>
  );
}
