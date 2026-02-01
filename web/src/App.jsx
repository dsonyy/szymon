import { useState, useEffect, useMemo } from "react";

const designSystem = {
  fonts: {
    calendar: "Arial, sans-serif",
    tasks: "Arial, sans-serif",
    ui: "Arial, sans-serif"
  },
  colors: {
    text: "#000",
    textMuted: "#000",
    textLight: "#000",
    border: "#e0e0e0",
    borderLight: "#f0f0f0",
    background: "#fff",
    backgroundHover: "#fafafa",
    backgroundToday: "#fffbeb",
    accent: "#000",
    completed: "#000"
  },
  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem"
  }
};

// Get Monday of the week containing the given date
const getWeekStart = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
};

// Generate array of 7 days starting from Monday
const getWeekDays = (weekStart) => {
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return date;
  });
};

// Check if two dates are the same day
const isSameDay = (d1, d2) => {
  return d1.toDateString() === d2.toDateString();
};

// Check if a date falls within the week
const isInWeek = (date, weekStart) => {
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 7);
  return date >= weekStart && date < weekEnd;
};

// Group tasks by date
const groupTasksByDate = (tasks, weekDays) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const weekStart = weekDays[0];

  const groups = {
    backlog: [],
    ...Object.fromEntries(weekDays.map(d => [d.toDateString(), []]))
  };

  tasks.forEach(task => {
    if (!task.due) {
      groups.backlog.push(task);
    } else {
      const dueDate = new Date(task.due);
      dueDate.setHours(0, 0, 0, 0);
      const dateKey = dueDate.toDateString();

      if (groups[dateKey] !== undefined) {
        groups[dateKey].push(task);
      } else {
        // Task outside current week goes to backlog
        groups.backlog.push(task);
      }
    }
  });

  return groups;
};

const styles = {
  app: {
    fontFamily: designSystem.fonts.ui,
    minHeight: "100vh",
    backgroundColor: designSystem.colors.background,
  },
  header: {
    padding: designSystem.spacing.md,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    fontFamily: designSystem.fonts.calendar,
    fontSize: "1.5rem",
    fontWeight: "normal",
    margin: 0,
  },
  navigation: {
    display: "flex",
    alignItems: "center",
    gap: designSystem.spacing.md,
    padding: designSystem.spacing.md,
  },
  navButton: {
    padding: designSystem.spacing.xs,
    border: "none",
    backgroundColor: "transparent",
    cursor: "pointer",
    fontFamily: designSystem.fonts.ui,
    fontSize: "0.875rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  calendarContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(8, 1fr)",
    minHeight: "calc(100vh - 120px)",
  },
  column: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  columnToday: {},
  columnBacklog: {},
  dayHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    textAlign: "center",
    cursor: "pointer",
  },
  dayNumber: {
    fontSize: "64px",
    fontWeight: "bold",
    lineHeight: 1,
  },
  dayName: {
    fontSize: "16px",
    fontWeight: "bold",
    color: designSystem.colors.text,
    marginTop: designSystem.spacing.xs,
  },
  backlogHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    textAlign: "center",
    fontSize: "1rem",
    cursor: "pointer",
  },
  taskList: {
    flex: 1,
    overflowY: "auto",
    padding: designSystem.spacing.xs,
  },
  taskItem: {
    fontFamily: designSystem.fonts.tasks,
    fontSize: "0.8125rem",
    padding: designSystem.spacing.sm,
    display: "flex",
    alignItems: "flex-start",
    gap: designSystem.spacing.xs,
  },
  taskCheckbox: {
    width: "10px",
    height: "10px",
    border: "2px solid #000",
    borderRadius: "3px",
    backgroundColor: "#fff",
    cursor: "pointer",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginTop: "3px",
  },
  taskCheckboxChecked: {
    width: "10px",
    height: "10px",
    border: "2px solid #000",
    borderRadius: "3px",
    backgroundColor: "#000",
    cursor: "pointer",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginTop: "3px",
  },
  taskContent: {
    flex: 1,
    minWidth: 0,
  },
  taskTitle: {
    wordBreak: "break-word",
  },
  taskTitleCompleted: {
    opacity: 0.5,
  },
  taskNotes: {
    fontSize: "0.75rem",
    color: designSystem.colors.textMuted,
    marginTop: "2px",
    wordBreak: "break-word",
  },
  taskDelete: {
    padding: "2px 4px",
    border: "none",
    background: "none",
    color: designSystem.colors.text,
    cursor: "pointer",
    fontSize: "0.75rem",
    opacity: 0.3,
    flexShrink: 0,
  },
  addTaskForm: {
    padding: designSystem.spacing.sm,
  },
  addTaskInput: {
    width: "100%",
    padding: designSystem.spacing.xs,
    border: "none",
    fontFamily: designSystem.fonts.tasks,
    fontSize: "0.8125rem",
    boxSizing: "border-box",
    outline: "none",
  },
  error: {
    padding: designSystem.spacing.md,
    backgroundColor: "#fee",
    color: "#c00",
  },
  loading: {
    padding: designSystem.spacing.xl,
    textAlign: "center",
    color: designSystem.colors.textMuted,
  },
  authMessage: {
    padding: designSystem.spacing.xl,
    textAlign: "center",
  },
  authLink: {
    color: "#007bff",
    textDecoration: "underline",
  },
  // Mobile styles
  mobileContainer: {
    display: "flex",
    flexDirection: "column",
  },
  mobileColumn: {},
};

export default function App() {
  // Existing state
  const [health, setHealth] = useState(null);
  const [authStatus, setAuthStatus] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // New state
  const [weekOffset, setWeekOffset] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [addingToDate, setAddingToDate] = useState(null); // Date or 'backlog'
  const [newTaskTitle, setNewTaskTitle] = useState("");

  useEffect(() => {
    fetch("/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch(console.error);

    checkAuthAndLoadTasks();
  }, []);

  // Mobile detection
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Auto-refresh tasks every 30 seconds
  useEffect(() => {
    if (!authStatus?.authenticated) return;
    const interval = setInterval(loadTasks, 30000);
    return () => clearInterval(interval);
  }, [authStatus?.authenticated]);

  // Calculate current week
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const weekStart = useMemo(() => {
    const start = getWeekStart(new Date());
    start.setDate(start.getDate() + weekOffset * 7);
    return start;
  }, [weekOffset]);

  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);

  const groupedTasks = useMemo(
    () => groupTasksByDate(tasks, weekDays),
    [tasks, weekDays]
  );

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
      const body = { title: newTaskTitle };
      if (addingToDate && addingToDate !== 'backlog') {
        // Format as RFC 3339 date (midnight UTC)
        body.due = addingToDate.toISOString();
      }

      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to create task");
      setNewTaskTitle("");
      setAddingToDate(null);
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

  return (
    <div style={styles.app}>
      {error && <div style={styles.error}>{error}</div>}

      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : !authStatus?.configured ? (
        <div style={styles.authMessage}>
          <p>Google Tasks not configured.</p>
          <p>
            Set <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> in <code>.env</code>
          </p>
        </div>
      ) : !authStatus?.authenticated ? (
        <div style={styles.authMessage}>
          <p>Not authenticated with Google Tasks.</p>
          <a href="/api/tasks/auth/login" style={styles.authLink}>
            Login with Google
          </a>
        </div>
      ) : (
        <>
          {/* Week Navigation */}
          <div style={styles.navigation}>
            <button style={styles.navButton} onClick={() => setWeekOffset(w => w - 1)}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 4 L6 10 L12 16" />
              </svg>
            </button>
            <button style={styles.navButton} onClick={() => setWeekOffset(w => w + 1)}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 4 L14 10 L8 16" />
              </svg>
            </button>
            {weekOffset !== 0 && (
              <button style={styles.navButton} onClick={() => setWeekOffset(0)}>
                Today
              </button>
            )}
          </div>

          {/* Calendar Grid */}
          <div style={isMobile ? styles.mobileContainer : styles.calendarContainer}>
            {/* Day Columns */}
            {weekDays.map((day) => {
              const dateKey = day.toDateString();
              const isToday = isSameDay(day, today);
              const dayTasks = groupedTasks[dateKey] || [];

              return (
                <div
                  key={dateKey}
                  style={{
                    ...styles.column,
                    ...(isToday ? styles.columnToday : {}),
                    ...(isMobile ? styles.mobileColumn : {}),
                  }}
                >
                  <div
                    style={styles.dayHeader}
                    onClick={() => setAddingToDate(day)}
                  >
                    <div style={styles.dayNumber}>{day.getDate()}</div>
                    <div style={styles.dayName}>
                      {day.toLocaleDateString('en-US', { weekday: 'long' })}
                    </div>
                  </div>

                  <div style={styles.taskList}>
                    {dayTasks.map((task) => (
                      <div key={task.id} style={styles.taskItem}>
                        <div
                          style={task.status === "completed" ? styles.taskCheckboxChecked : styles.taskCheckbox}
                          onClick={() => toggleComplete(task)}
                        >
                          {task.status === "completed" && (
                            <svg width="12" height="12" viewBox="0 0 10 10" fill="none" stroke="#fff" strokeWidth="2">
                              <path d="M1 5 L4 8 L9 2" />
                            </svg>
                          )}
                        </div>
                        <div style={styles.taskContent}>
                          <div style={{
                            ...styles.taskTitle,
                            ...(task.status === "completed" ? styles.taskTitleCompleted : {}),
                          }}>
                            {task.title}
                          </div>
                          {task.notes && (
                            <div style={styles.taskNotes}>{task.notes}</div>
                          )}
                        </div>
                        <button
                          style={styles.taskDelete}
                          onClick={() => deleteTask(task.id)}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>

                  {addingToDate && isSameDay(addingToDate, day) && (
                    <form style={styles.addTaskForm} onSubmit={createTask}>
                      <input
                        style={styles.addTaskInput}
                        type="text"
                        placeholder="New task..."
                        value={newTaskTitle}
                        onChange={(e) => setNewTaskTitle(e.target.value)}
                        autoFocus
                        onBlur={() => !newTaskTitle && setAddingToDate(null)}
                      />
                    </form>
                  )}
                </div>
              );
            })}

            {/* Backlog Column */}
            <div style={{
              ...styles.column,
              ...styles.columnBacklog,
              ...(isMobile ? styles.mobileColumn : {}),
            }}>
              <div
                style={styles.backlogHeader}
                onClick={() => setAddingToDate('backlog')}
              >
                Backlog
              </div>

              <div style={styles.taskList}>
                {groupedTasks.backlog.map((task) => (
                  <div key={task.id} style={styles.taskItem}>
                    <div
                      style={task.status === "completed" ? styles.taskCheckboxChecked : styles.taskCheckbox}
                      onClick={() => toggleComplete(task)}
                    >
                      {task.status === "completed" && (
                        <svg width="12" height="12" viewBox="0 0 10 10" fill="none" stroke="#fff" strokeWidth="2">
                          <path d="M1 5 L4 8 L9 2" />
                        </svg>
                      )}
                    </div>
                    <div style={styles.taskContent}>
                      <div style={{
                        ...styles.taskTitle,
                        ...(task.status === "completed" ? styles.taskTitleCompleted : {}),
                      }}>
                        {task.title}
                      </div>
                      {task.notes && (
                        <div style={styles.taskNotes}>{task.notes}</div>
                      )}
                    </div>
                    <button
                      style={styles.taskDelete}
                      onClick={() => deleteTask(task.id)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>

              {addingToDate === 'backlog' && (
                <form style={styles.addTaskForm} onSubmit={createTask}>
                  <input
                    style={styles.addTaskInput}
                    type="text"
                    placeholder="New task..."
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    autoFocus
                    onBlur={() => !newTaskTitle && setAddingToDate(null)}
                  />
                </form>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
