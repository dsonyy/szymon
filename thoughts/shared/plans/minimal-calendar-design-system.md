# Minimal Calendar Design System Implementation Plan

## Overview

Refactor the frontend from a table-based task view to a column-based calendar showing the current week (Monday-Sunday) plus a Backlog column, with week navigation, using Times New Roman for calendar headers and Courier New for tasks.

## Current State Analysis

- `web/src/App.jsx:1-291` - Monolithic React component with table layout
- Inline JS styles (lines 3-83) - will be replaced with new design system
- Existing task CRUD operations (lines 118-174) - will be reused
- Task data includes `due` field (RFC 3339 format) for calendar grouping

## Desired End State

A column-based calendar view with:
- 8 columns: Mon-Sun + Backlog (tasks without due dates or outside current week)
- Week navigation (previous/next, "Today" button)
- Clicking a day column opens task creation with that date pre-filled
- Today's column highlighted
- Mobile: columns stack vertically
- Typography: Times New Roman (headers), Courier New (tasks)

### Verification:
- Visual inspection of calendar layout with 8 columns
- Week navigation changes displayed dates
- Tasks appear in correct columns based on due date
- Today column has distinct styling
- Mobile view shows stacked columns

## What We're NOT Doing

- Drag-and-drop task rescheduling (future feature)
- Task editing inline (existing delete/complete operations only)
- Multi-week view or month view
- Task filtering or search

## Implementation Approach

Single-phase refactor of `App.jsx`:
1. Add design system constants
2. Add date utility functions
3. Add week navigation state
4. Replace table layout with calendar grid
5. Add responsive mobile handling

## Phase 1: Complete Calendar Refactor

### Overview
Replace the entire table-based UI with the new calendar view in a single cohesive change.

### Changes Required:

#### 1. Design System Constants
**File**: `web/src/App.jsx`
**Changes**: Replace existing styles (lines 3-83) with new design system

```javascript
const designSystem = {
  fonts: {
    calendar: "'Times New Roman', Times, serif",
    tasks: "'Courier New', Courier, monospace",
    ui: "system-ui, -apple-system, sans-serif"
  },
  colors: {
    text: "#1a1a1a",
    textMuted: "#666",
    textLight: "#999",
    border: "#e0e0e0",
    borderLight: "#f0f0f0",
    background: "#fff",
    backgroundHover: "#fafafa",
    backgroundToday: "#fffbeb",
    accent: "#333",
    completed: "#999"
  },
  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem"
  }
};
```

#### 2. Date Utility Functions
**File**: `web/src/App.jsx`
**Changes**: Add helper functions after design system

```javascript
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
```

#### 3. Styles Object
**File**: `web/src/App.jsx`
**Changes**: Add new styles object after utility functions

```javascript
const styles = {
  app: {
    fontFamily: designSystem.fonts.ui,
    minHeight: "100vh",
    backgroundColor: designSystem.colors.background,
  },
  header: {
    padding: designSystem.spacing.md,
    borderBottom: `1px solid ${designSystem.colors.border}`,
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
    borderBottom: `1px solid ${designSystem.colors.border}`,
  },
  navButton: {
    padding: `${designSystem.spacing.xs} ${designSystem.spacing.sm}`,
    border: `1px solid ${designSystem.colors.border}`,
    borderRadius: "4px",
    backgroundColor: designSystem.colors.background,
    cursor: "pointer",
    fontFamily: designSystem.fonts.ui,
    fontSize: "0.875rem",
  },
  weekLabel: {
    fontFamily: designSystem.fonts.calendar,
    fontSize: "1.125rem",
    minWidth: "200px",
    textAlign: "center",
  },
  calendarContainer: {
    display: "grid",
    gridTemplateColumns: "repeat(8, 1fr)",
    minHeight: "calc(100vh - 120px)",
  },
  column: {
    borderRight: `1px solid ${designSystem.colors.border}`,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  columnToday: {
    backgroundColor: designSystem.colors.backgroundToday,
  },
  columnBacklog: {
    borderRight: "none",
  },
  dayHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    borderBottom: `1px solid ${designSystem.colors.border}`,
    textAlign: "center",
    cursor: "pointer",
  },
  dayNumber: {
    fontSize: "2rem",
    fontWeight: "normal",
    lineHeight: 1,
  },
  dayName: {
    fontSize: "0.75rem",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    color: designSystem.colors.textMuted,
    marginTop: designSystem.spacing.xs,
  },
  backlogHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    borderBottom: `1px solid ${designSystem.colors.border}`,
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
    borderBottom: `1px solid ${designSystem.colors.borderLight}`,
    display: "flex",
    alignItems: "flex-start",
    gap: designSystem.spacing.xs,
  },
  taskCheckbox: {
    marginTop: "2px",
    cursor: "pointer",
    flexShrink: 0,
  },
  taskContent: {
    flex: 1,
    minWidth: 0,
  },
  taskTitle: {
    wordBreak: "break-word",
  },
  taskTitleCompleted: {
    textDecoration: "line-through",
    color: designSystem.colors.completed,
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
    color: designSystem.colors.textLight,
    cursor: "pointer",
    fontSize: "0.75rem",
    opacity: 0.5,
    flexShrink: 0,
  },
  addTaskForm: {
    padding: designSystem.spacing.sm,
    borderTop: `1px solid ${designSystem.colors.borderLight}`,
  },
  addTaskInput: {
    width: "100%",
    padding: designSystem.spacing.xs,
    border: `1px solid ${designSystem.colors.border}`,
    borderRadius: "4px",
    fontFamily: designSystem.fonts.tasks,
    fontSize: "0.8125rem",
    boxSizing: "border-box",
  },
  error: {
    padding: designSystem.spacing.md,
    backgroundColor: "#fee",
    borderBottom: `1px solid #c00`,
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
  mobileColumn: {
    borderBottom: `1px solid ${designSystem.colors.border}`,
    borderRight: "none",
  },
};
```

#### 4. Component State Changes
**File**: `web/src/App.jsx`
**Changes**: Add new state variables in App component

```javascript
// Existing state (keep)
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
```

#### 5. New Hooks and Derived State
**File**: `web/src/App.jsx`
**Changes**: Add after state declarations

```javascript
// Mobile detection
useEffect(() => {
  const handleResize = () => setIsMobile(window.innerWidth < 768);
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);

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
```

#### 6. Modified createTask Function
**File**: `web/src/App.jsx`
**Changes**: Update to accept optional due date

```javascript
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
```

#### 7. New JSX Structure
**File**: `web/src/App.jsx`
**Changes**: Replace entire return statement

```jsx
return (
  <div style={styles.app}>
    {/* Header */}
    <div style={styles.header}>
      <h1 style={styles.title}>Szymon</h1>
      <span>
        {health?.status === "ok" ? "●" : "○"} API
      </span>
    </div>

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
            ← Prev
          </button>
          <span style={styles.weekLabel}>
            {weekStart.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </span>
          <button style={styles.navButton} onClick={() => setWeekOffset(w => w + 1)}>
            Next →
          </button>
          {weekOffset !== 0 && (
            <button style={styles.navButton} onClick={() => setWeekOffset(0)}>
              Today
            </button>
          )}
          <button style={styles.navButton} onClick={loadTasks}>
            ↻
          </button>
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
                    {day.toLocaleDateString('en-US', { weekday: 'short' })}
                  </div>
                </div>

                <div style={styles.taskList}>
                  {dayTasks.map((task) => (
                    <div key={task.id} style={styles.taskItem}>
                      <input
                        type="checkbox"
                        style={styles.taskCheckbox}
                        checked={task.status === "completed"}
                        onChange={() => toggleComplete(task)}
                      />
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
                  <input
                    type="checkbox"
                    style={styles.taskCheckbox}
                    checked={task.status === "completed"}
                    onChange={() => toggleComplete(task)}
                  />
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
```

#### 8. Required Import Update
**File**: `web/src/App.jsx`
**Changes**: Add `useMemo` to imports

```javascript
import { useState, useEffect, useMemo } from "react";
```

### Success Criteria:

#### Automated Verification:
- [x] No build errors: `cd web && npm run build`
- [ ] Dev server starts: `cd web && npm run dev`
- [ ] No console errors in browser dev tools

#### Manual Verification:
- [ ] 8 columns visible (Mon-Sun + Backlog)
- [ ] Week navigation buttons work (Prev/Next/Today)
- [ ] Today's column has yellow background
- [ ] Clicking a day header shows input field for new task
- [ ] New tasks appear in correct column based on due date
- [ ] Tasks without due dates appear in Backlog
- [ ] Tasks outside current week appear in Backlog
- [ ] Checkbox toggles task completion (strikethrough)
- [ ] Delete button (×) removes task
- [ ] Mobile view (< 768px) shows stacked columns
- [ ] Times New Roman visible in day headers
- [ ] Courier New visible in task text

---

## Testing Strategy

### Manual Testing Steps:
1. Load the page - verify 8-column calendar displays
2. Check current week dates match actual calendar
3. Click "Next →" - verify week advances
4. Click "← Prev" - verify week goes back
5. Click "Today" - verify returns to current week
6. Click a day header - verify input appears
7. Type task and press Enter - verify task appears in that column
8. Click Backlog header - add task without due date
9. Check a task's checkbox - verify strikethrough
10. Uncheck - verify strikethrough removed
11. Click × - verify task deleted (after confirmation)
12. Resize browser to < 768px - verify columns stack
13. Create task with future due date, navigate to that week, verify it appears

## References

- Research document: `thoughts/shared/research/2026-02-01_minimal-calendar-design-system.md`
- Current implementation: `web/src/App.jsx:1-291`
