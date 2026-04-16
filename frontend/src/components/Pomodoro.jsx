import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useToast } from "./Toast";

export default function Pomodoro() {
  const [mode, setMode] = useState("work");
  const [state, setState] = useState("idle");
  const [workMin, setWorkMin] = useState(25);
  const [breakMin, setBreakMin] = useState(5);
  const [left, setLeft] = useState(25 * 60);
  const [sessionsToday, setSessionsToday] = useState(0);
  const intervalRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    api.pomodoroToday().then((d) => setSessionsToday(d.sessions));
  }, []);

  useEffect(() => {
    if (state === "running") {
      intervalRef.current = setInterval(() => {
        setLeft((prev) => {
          if (prev <= 1) {
            clearInterval(intervalRef.current);
            setState("done");
            if (mode === "work") {
              api.completePomodoro(workMin).then(() => {
                api.pomodoroToday().then((d) => setSessionsToday(d.sessions));
              });
              toast("Work session complete! Take a break.");
            } else {
              toast("Break over! Time to focus.", "info");
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(intervalRef.current);
  }, [state]);

  const totalSecs = (mode === "work" ? workMin : breakMin) * 60;
  const pct = totalSecs ? (left / totalSecs) * 100 : 0;
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");

  function startPause() {
    if (state === "idle") {
      setState("running");
      toast("Timer started", "info");
    } else if (state === "running") {
      clearInterval(intervalRef.current);
      setState("paused");
      toast("Paused", "info");
    } else if (state === "paused") {
      setState("running");
      toast("Resumed", "info");
    } else if (state === "done") {
      if (mode === "work") {
        const longBreak = sessionsToday > 0 && sessionsToday % 4 === 0;
        const mins = longBreak ? 15 : breakMin;
        setMode("break");
        setLeft(mins * 60);
      } else {
        setMode("work");
        setLeft(workMin * 60);
      }
      setState("running");
    }
  }

  function reset() {
    clearInterval(intervalRef.current);
    setState("idle");
    setLeft((mode === "work" ? workMin : breakMin) * 60);
    toast("Timer reset", "info");
  }

  function adjustWork(delta) {
    if (state !== "idle") return;
    const next = Math.max(1, Math.min(90, workMin + delta));
    setWorkMin(next);
    if (mode === "work") setLeft(next * 60);
  }

  const timerClass = state === "idle" ? "idle" : mode;
  const stateLabel = { idle: "IDLE", running: "RUNNING", paused: "PAUSED", done: "TIME'S UP" }[state];
  const btnLabel = { idle: "Start", running: "Pause", paused: "Resume", done: "Next" }[state];

  return (
    <div>
      <div className="card">
        <div className="pomo-container">
          <div className={`pomo-timer ${timerClass}`}>{mm}:{ss}</div>
          <div className="pomo-mode">{mode === "work" ? "WORK" : "BREAK"} &middot; {stateLabel}</div>
          <div className="pomo-progress">
            <div className={`fill ${mode}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="pomo-controls">
            <button className="btn" onClick={() => adjustWork(-1)} disabled={state !== "idle"}>-</button>
            <button className="btn btn-primary" onClick={startPause}>{btnLabel}</button>
            <button className="btn" onClick={reset}>Reset</button>
            <button className="btn" onClick={() => adjustWork(1)} disabled={state !== "idle"}>+</button>
          </div>
          <div className="pomo-stats">
            <span>Sessions today: <strong>{sessionsToday}</strong></span>
            <span>Work: <strong>{workMin}m</strong></span>
            <span>Break: <strong>{breakMin}m</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}
