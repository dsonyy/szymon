import { useState, useEffect } from "react";

const styles = {
  container: {
    fontFamily: "system-ui",
    padding: "2rem",
    maxWidth: "900px",
    margin: "0 auto",
  },
  header: {
    marginBottom: "2rem",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    marginTop: "1rem",
  },
  th: {
    textAlign: "left",
    padding: "0.75rem",
    borderBottom: "2px solid #ddd",
    backgroundColor: "#f5f5f5",
  },
  td: {
    padding: "0.75rem",
    borderBottom: "1px solid #eee",
  },
  completed: {
    textDecoration: "line-through",
    color: "#888",
  },
  button: {
    padding: "0.25rem 0.5rem",
    marginRight: "0.25rem",
    cursor: "pointer",
    border: "1px solid #ccc",
    borderRadius: "4px",
    backgroundColor: "#fff",
  },
  dangerButton: {
    padding: "0.25rem 0.5rem",
    cursor: "pointer",
    border: "1px solid #c00",
    borderRadius: "4px",
    backgroundColor: "#fff",
    color: "#c00",
  },
  form: {
    display: "flex",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
  input: {
    padding: "0.5rem",
    border: "1px solid #ccc",
    borderRadius: "4px",
    flex: 1,
  },
  submitButton: {
    padding: "0.5rem 1rem",
    cursor: "pointer",
    border: "none",
    borderRadius: "4px",
    backgroundColor: "#007bff",
    color: "#fff",
  },
  error: {
    padding: "1rem",
    backgroundColor: "#fee",
    border: "1px solid #c00",
    borderRadius: "4px",
    marginBottom: "1rem",
  },
  loading: {
    color: "#666",
    fontStyle: "italic",
  },
  authLink: {
    color: "#007bff",
    textDecoration: "underline",
    cursor: "pointer",
  },
};

export default function App() {
  const [health, setHealth] = useState(null);
  const [authStatus, setAuthStatus] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newTaskTitle, setNewTaskTitle] = useState("");

  useEffect(() => {
    fetch("/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch(console.error);

    checkAuthAndLoadTasks();
  }, []);

  const checkAuthAndLoadTasks = async () => {
    try {
      const authRes = await fetch("/api/tasks/auth/status");
      const auth = await authRes.json();
      setAuthStatus(auth);

      if (auth.configured && auth.authenticated) {
        await loadTasks();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTasks = async () => {
    try {
      const res = await fetch("/api/tasks");
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to load tasks");
      }
      const data = await res.json();
      setTasks(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  };

  const createTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;

    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTaskTitle }),
      });
      if (!res.ok) throw new Error("Failed to create task");
      setNewTaskTitle("");
      await loadTasks();
    } catch (e) {
      setError(e.message);
    }
  };

  const toggleComplete = async (task) => {
    try {
      const endpoint =
        task.status === "completed"
          ? `/api/tasks/${task.id}/uncomplete`
          : `/api/tasks/${task.id}/complete`;
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) throw new Error("Failed to update task");
      await loadTasks();
    } catch (e) {
      setError(e.message);
    }
  };

  const deleteTask = async (taskId) => {
    if (!confirm("Delete this task?")) return;
    try {
      const res = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete task");
      await loadTasks();
    } catch (e) {
      setError(e.message);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>Szymon</h1>
        <p>Personal assistant gateway</p>
        <p>
          API Status: <strong>{health?.status ?? "loading..."}</strong>
        </p>
      </div>

      <h2>Google Tasks</h2>

      {error && <div style={styles.error}>{error}</div>}

      {loading ? (
        <p style={styles.loading}>Loading...</p>
      ) : !authStatus?.configured ? (
        <p>
          Google Tasks not configured. Set <code>GOOGLE_CLIENT_ID</code> and{" "}
          <code>GOOGLE_CLIENT_SECRET</code> in your <code>.env</code> file.
        </p>
      ) : !authStatus?.authenticated ? (
        <div>
          <p>Not authenticated with Google Tasks.</p>
          <p>
            <a href="/api/tasks/auth/login" style={styles.authLink}>
              Click here to login with Google
            </a>
          </p>
        </div>
      ) : (
        <>
          <form style={styles.form} onSubmit={createTask}>
            <input
              style={styles.input}
              type="text"
              placeholder="New task title..."
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
            />
            <button style={styles.submitButton} type="submit">
              Add Task
            </button>
          </form>

          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Title</th>
                <th style={styles.th}>Due</th>
                <th style={styles.th}>Updated</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 ? (
                <tr>
                  <td style={styles.td} colSpan="5">
                    No tasks found
                  </td>
                </tr>
              ) : (
                tasks.map((task) => (
                  <tr key={task.id}>
                    <td style={styles.td}>
                      <input
                        type="checkbox"
                        checked={task.status === "completed"}
                        onChange={() => toggleComplete(task)}
                      />
                    </td>
                    <td
                      style={{
                        ...styles.td,
                        ...(task.status === "completed" ? styles.completed : {}),
                      }}
                    >
                      {task.title}
                      {task.notes && (
                        <div style={{ fontSize: "0.85em", color: "#666" }}>
                          {task.notes}
                        </div>
                      )}
                    </td>
                    <td style={styles.td}>{formatDate(task.due)}</td>
                    <td style={styles.td}>{formatDate(task.updated)}</td>
                    <td style={styles.td}>
                      <button
                        style={styles.dangerButton}
                        onClick={() => deleteTask(task.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          <p style={{ marginTop: "1rem" }}>
            <button style={styles.button} onClick={loadTasks}>
              Refresh
            </button>
          </p>
        </>
      )}
    </div>
  );
}
