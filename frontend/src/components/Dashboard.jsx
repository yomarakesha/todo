import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const TIPS = [
  "Small steps every day lead to big results.",
  "Don't break the chain \u2014 keep your streaks alive!",
  "The best workout is the one you actually do.",
  "Focus on progress, not perfection.",
  "One task at a time. You've got this.",
  "Discipline is choosing between what you want now and what you want most.",
  "The secret of getting ahead is getting started.",
  "Rest when you must, but never quit.",
];

export default function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.dashboard().then(setStats);
  }, []);

  if (!stats) return null;

  const tip = TIPS[Math.floor(new Date().getTime() / 86400000) % TIPS.length];

  return (
    <div>
      <div className="quote">"{tip}"</div>

      <div className="dash-grid">
        <Link to="/todo" className="stat-card green">
          <div className="stat-label">Todo</div>
          <div className="stat-value">{stats.todos_active}</div>
          <div className="stat-sub">
            active tasks &middot; {stats.todos_done} done
            {stats.todos_overdue > 0 && (
              <span style={{ color: "var(--red)" }}>
                {" "}&middot; {stats.todos_overdue} overdue
              </span>
            )}
          </div>
        </Link>

        <Link to="/gym" className="stat-card blue">
          <div className="stat-label">Gym</div>
          <div className="stat-value">{stats.workouts_this_week}</div>
          <div className="stat-sub">
            this week &middot; last: {stats.last_exercise} &middot; max: {stats.max_weight}kg
          </div>
        </Link>

        <Link to="/habits" className="stat-card magenta">
          <div className="stat-label">Habits</div>
          <div className="stat-value">
            {stats.habits_done_today}/{stats.habits_total}
          </div>
          <div className="stat-sub">
            done today &middot; best streak: {stats.best_streak}d
          </div>
        </Link>

        <Link to="/pomodoro" className="stat-card yellow">
          <div className="stat-label">Pomodoro</div>
          <div className="stat-value">{stats.pomodoro_today}</div>
          <div className="stat-sub">sessions today</div>
        </Link>
      </div>
    </div>
  );
}
