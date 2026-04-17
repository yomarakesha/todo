import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast";

export default function Settings() {
  const [pushSupported, setPushSupported] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const supported = "serviceWorker" in navigator && "PushManager" in window;
    setPushSupported(supported);
    if (supported) {
      navigator.serviceWorker.ready.then((reg) => {
        reg.pushManager.getSubscription().then((sub) => {
          setPushEnabled(!!sub);
        });
      });
    }
  }, []);

  async function togglePush() {
    setLoading(true);
    try {
      if (pushEnabled) {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          await sub.unsubscribe();
          await api.pushUnsubscribe();
        }
        setPushEnabled(false);
        toast("Notifications disabled");
      } else {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          toast("Permission denied", "error");
          setLoading(false);
          return;
        }

        const vapidRes = await api.getVapidKey();
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidRes.publicKey),
        });

        const subJson = sub.toJSON();
        await api.pushSubscribe({
          endpoint: subJson.endpoint,
          keys: subJson.keys,
        });

        setPushEnabled(true);
        toast("Notifications enabled!");
      }
    } catch (err) {
      console.error("Push toggle error:", err);
      toast("Error: " + err.message, "error");
    }
    setLoading(false);
  }

  async function testPush() {
    try {
      await api.pushTest();
      toast("Test notification sent");
    } catch {
      toast("Failed to send test", "error");
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Settings</h2>
        </div>

        <div className="settings-section">
          <h3 className="settings-title">Push Notifications</h3>
          <p className="settings-desc">
            Get daily reminders about overdue tasks (9:00) and incomplete habits (20:00).
          </p>

          {!pushSupported ? (
            <p className="settings-desc" style={{ color: "var(--red)" }}>
              Push notifications are not supported in this browser.
            </p>
          ) : (
            <div className="settings-row">
              <div>
                <span className="settings-label">Enable notifications</span>
                <span className="settings-status">
                  {pushEnabled ? "Active" : "Disabled"}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className={`btn ${pushEnabled ? "btn-danger" : "btn-primary"}`}
                  onClick={togglePush}
                  disabled={loading}
                  style={pushEnabled ? { color: "var(--red)", border: "1px solid var(--red)", background: "rgba(255,82,82,0.1)", padding: "8px 16px" } : {}}
                >
                  {loading ? "..." : pushEnabled ? "Disable" : "Enable"}
                </button>
                {pushEnabled && (
                  <button className="btn" onClick={testPush}>
                    Test
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}
