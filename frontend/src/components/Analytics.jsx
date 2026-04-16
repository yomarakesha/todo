import { useEffect, useState } from "react";
import { api } from "../api";

export default function Analytics() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.analytics().then(setData);
  }, []);

  if (!data) return null;

  const workoutDays = Object.entries(data.workout_days);
  const maxWorkout = Math.max(...Object.values(data.workout_days), 1);

  const pomoDays = Object.entries(data.pomo_days);
  const maxPomo = Math.max(...Object.values(data.pomo_days), 1);

  const todoDays = Object.entries(data.todo_done_days);
  const maxTodo = Math.max(...Object.values(data.todo_done_days), 1);

  const heatmapDays = Object.entries(data.habit_heatmap);
  const maxHabit = Math.max(data.habits_total || 1, 1);

  const muscleDist = Object.entries(data.muscle_distribution);
  const maxMuscle = Math.max(...muscleDist.map(([, v]) => v), 1);

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Analytics</h2>
        </div>

        <div className="analytics-grid">
          {/* Workouts chart */}
          <div className="chart-card">
            <h3>Workouts (30 days)</h3>
            <div className="bar-chart">
              {workoutDays.map(([d, v]) => (
                <div
                  key={d}
                  className="bar"
                  data-label={`${d.slice(5)}: ${v}`}
                  style={{
                    height: `${(v / maxWorkout) * 100}%`,
                    background: "var(--blue)",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Pomodoro chart */}
          <div className="chart-card">
            <h3>Pomodoro (14 days)</h3>
            <div className="bar-chart">
              {pomoDays.map(([d, v]) => (
                <div
                  key={d}
                  className="bar"
                  data-label={`${d.slice(5)}: ${v}`}
                  style={{
                    height: `${(v / maxPomo) * 100}%`,
                    background: "var(--yellow)",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Tasks done chart */}
          <div className="chart-card">
            <h3>Tasks Completed (14 days)</h3>
            <div className="bar-chart">
              {todoDays.map(([d, v]) => (
                <div
                  key={d}
                  className="bar"
                  data-label={`${d.slice(5)}: ${v}`}
                  style={{
                    height: `${(v / maxTodo) * 100}%`,
                    background: "var(--green)",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Muscle distribution */}
          <div className="chart-card">
            <h3>Muscle Groups</h3>
            {muscleDist.length === 0 ? (
              <div className="empty" style={{ padding: 20 }}>No data</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {muscleDist.map(([group, count]) => (
                  <div key={group} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 70, fontSize: 12, color: "var(--text-dim)" }}>{group}</span>
                    <div style={{
                      flex: 1, height: 16, background: "var(--bg)",
                      borderRadius: 4, overflow: "hidden",
                    }}>
                      <div style={{
                        width: `${(count / maxMuscle) * 100}%`,
                        height: "100%", background: "var(--blue)", borderRadius: 4,
                      }} />
                    </div>
                    <span style={{ fontSize: 12, color: "var(--text-dim)", width: 24 }}>{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Habit heatmap */}
          <div className="chart-card" style={{ gridColumn: "1 / -1" }}>
            <h3>Habit Heatmap (12 weeks)</h3>
            <div className="heatmap">
              {heatmapDays.map(([d, v]) => {
                const level = v === 0 ? 0 : Math.min(4, Math.ceil((v / maxHabit) * 4));
                return (
                  <div
                    key={d}
                    className={`heatmap-cell level-${level}`}
                    title={`${d}: ${v}/${data.habits_total}`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
