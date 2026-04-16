export default function ConfirmModal({ title, message, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 360 }}>
        <h3>{title || "Confirm"}</h3>
        <p style={{ color: "var(--text-dim)", marginBottom: 24, fontSize: 14 }}>
          {message || "Are you sure?"}
        </p>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button
            className="btn"
            style={{ background: "var(--red)", color: "#fff", borderColor: "var(--red)" }}
            onClick={onConfirm}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
