const API = import.meta.env.VITE_API_URL || "/api";

function getHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: getHeaders(),
    ...options,
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    return null;
  }
  if (options.method === "DELETE") return null;
  return res.json();
}

export const api = {
  // Auth
  login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  // Dashboard
  dashboard: () => request("/dashboard"),

  // Todos
  getTodos: (filter = "all") => request(`/todos?filter=${filter}`),
  createTodo: (data) => request("/todos", { method: "POST", body: JSON.stringify(data) }),
  updateTodo: (id, data) => request(`/todos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTodo: (id) => request(`/todos/${id}`, { method: "DELETE" }),

  // Subtasks
  getSubtasks: (todoId) => request(`/todos/${todoId}/subtasks`),
  createSubtask: (todoId, text) =>
    request(`/todos/${todoId}/subtasks`, { method: "POST", body: JSON.stringify({ text }) }),
  toggleSubtask: (todoId, subtaskId) =>
    request(`/todos/${todoId}/subtasks/${subtaskId}/toggle`, { method: "POST" }),
  deleteSubtask: (todoId, subtaskId) =>
    request(`/todos/${todoId}/subtasks/${subtaskId}`, { method: "DELETE" }),

  // Exercises catalog
  getExercises: () => request("/exercises"),
  getLastWorkout: (exercise) => request(`/workouts/last?exercise=${encodeURIComponent(exercise)}`),

  // Todo templates
  getTodoTemplates: () => request("/todos/templates"),
  applyTodoTemplate: (key) => request(`/todos/templates/${key}`, { method: "POST" }),

  // Habit templates
  getHabitTemplates: () => request("/habits/templates"),
  applyHabitTemplate: (key) => request(`/habits/templates/${key}`, { method: "POST" }),

  // Workouts
  getWorkouts: () => request("/workouts"),
  createWorkout: (data) => request("/workouts", { method: "POST", body: JSON.stringify(data) }),
  updateWorkout: (id, data) => request(`/workouts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteWorkout: (id) => request(`/workouts/${id}`, { method: "DELETE" }),

  // Habits
  getHabits: () => request("/habits"),
  createHabit: (data) => request("/habits", { method: "POST", body: JSON.stringify(data) }),
  updateHabit: (id, data) => request(`/habits/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteHabit: (id) => request(`/habits/${id}`, { method: "DELETE" }),
  toggleHabit: (id) => request(`/habits/${id}/toggle`, { method: "POST" }),

  // Pomodoro
  pomodoroToday: () => request("/pomodoro/today"),
  completePomodoro: (duration = 25) =>
    request("/pomodoro/complete", { method: "POST", body: JSON.stringify({ duration }) }),

  // Notes
  getNotes: () => request("/notes"),
  getNote: (id) => request(`/notes/${id}`),
  createNote: (data) => request("/notes", { method: "POST", body: JSON.stringify(data) }),
  updateNote: (id, data) => request(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteNote: (id) => request(`/notes/${id}`, { method: "DELETE" }),

  // Analytics
  analytics: () => request("/analytics"),

  // Push notifications
  getVapidKey: () => request("/push/vapid-key"),
  pushSubscribe: (data) => request("/push/subscribe", { method: "POST", body: JSON.stringify(data) }),
  pushUnsubscribe: () => request("/push/unsubscribe", { method: "DELETE" }),
  pushTest: () => request("/push/test", { method: "POST" }),
};
