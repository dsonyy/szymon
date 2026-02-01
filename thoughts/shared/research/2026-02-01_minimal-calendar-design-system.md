---
date: 2026-02-01T12:00:00+01:00
researcher: Claude
git_commit: 5c281a1aff0924d74489da3b1eac9f3d73984952
branch: main
repository: szymon
topic: "Minimal Design System with Column-Based Calendar View"
tags: [research, codebase, frontend, design-system, calendar, react]
status: complete
last_updated: 2026-02-01
last_updated_by: Claude
---

# Research: Minimal Design System with Column-Based Calendar View

**Date**: 2026-02-01T12:00:00+01:00
**Researcher**: Claude
**Git Commit**: 5c281a1aff0924d74489da3b1eac9f3d73984952
**Branch**: main
**Repository**: szymon

## Research Question

How to introduce a new minimal design system and refactor the main front page to display a column-based calendar showing the current week (Monday-Sunday) + backlog column, with week navigation, using Times New Roman for calendar headers and Courier New for tasks, with responsive and elegant design.

## Summary

The current frontend is a minimal React 19 application with Vite, using inline JavaScript styles. The main page (`web/src/App.jsx`) displays tasks in a table format. Refactoring to a column-based calendar view is straightforward since:

1. **No external dependencies needed** - Can be built with pure React and inline styles
2. **Task API already provides due dates** - RFC 3339 format, easy to parse for calendar grouping
3. **Simple architecture** - Single component file, easy to restructure
4. **Existing task operations work** - Create, complete, delete operations can be reused

## Detailed Findings

### Current Frontend Architecture

| Item | Value |
|------|-------|
| Framework | React 19 |
| Build Tool | Vite 6 |
| Styling | Inline JS style objects |
| Entry Point | `web/src/App.jsx` |
| Components | 1 (monolithic App component) |

### Current Styling System (`web/src/App.jsx:3-83`)

The existing styles use:
- `system-ui` font family
- Max-width 900px centered layout
- Simple color palette: `#007bff` (primary), `#c00` (danger), `#666` (muted)
- Table-based task display

### Task Data Structure (from Google Tasks API)

```javascript
{
  id: string,
  title: string,
  notes: string | null,
  due: string | null,      // RFC 3339 timestamp (e.g., "2024-01-15T00:00:00.000Z")
  updated: string,         // RFC 3339 timestamp
  status: "needsAction" | "completed"
}
```

### API Endpoints Available

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tasks` | GET | List all tasks (with `show_completed` param) |
| `/api/tasks` | POST | Create task |
| `/api/tasks/{id}` | PUT | Update task (including due date) |
| `/api/tasks/{id}` | DELETE | Delete task |
| `/api/tasks/{id}/complete` | POST | Mark complete |
| `/api/tasks/{id}/uncomplete` | POST | Mark incomplete |

## Implementation Plan

### 1. New Design System (Inline Styles)

```javascript
const designSystem = {
  // Typography
  fonts: {
    calendar: "'Times New Roman', Times, serif",
    tasks: "'Courier New', Courier, monospace",
    ui: "system-ui, -apple-system, sans-serif"
  },

  // Colors - minimal palette
  colors: {
    text: "#1a1a1a",
    textMuted: "#666",
    textLight: "#999",
    border: "#e0e0e0",
    borderLight: "#f0f0f0",
    background: "#fff",
    backgroundHover: "#fafafa",
    accent: "#333",
    completed: "#999"
  },

  // Spacing scale
  spacing: {
    xs: "0.25rem",
    sm: "0.5rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem"
  }
};
```

### 2. Calendar Component Structure

```
CalendarView
├── WeekNavigation (← Previous Week | Current Week | Next Week →)
├── ColumnContainer (8 columns: Mon-Sun + Backlog)
│   ├── DayColumn (×7)
│   │   ├── DayHeader (day number, day name)
│   │   └── TaskList
│   │       └── TaskItem (×n)
│   └── BacklogColumn
│       ├── BacklogHeader
│       └── TaskList
│           └── TaskItem (×n)
```

### 3. Week Calculation Logic

```javascript
// Get Monday of current week
const getWeekStart = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Sunday
  return new Date(d.setDate(diff));
};

// Generate array of 7 days starting from Monday
const getWeekDays = (weekStart) => {
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return date;
  });
};

// Week navigation
const [weekOffset, setWeekOffset] = useState(0);
const currentWeekStart = useMemo(() => {
  const start = getWeekStart(new Date());
  start.setDate(start.getDate() + weekOffset * 7);
  return start;
}, [weekOffset]);
```

### 4. Task Grouping by Date

```javascript
const groupTasksByDate = (tasks, weekDays) => {
  const groups = {
    backlog: [], // Tasks without due date
    ...Object.fromEntries(weekDays.map(d => [d.toDateString(), []]))
  };

  tasks.forEach(task => {
    if (!task.due) {
      groups.backlog.push(task);
    } else {
      const dueDate = new Date(task.due).toDateString();
      if (groups[dueDate]) {
        groups[dueDate].push(task);
      }
      // Tasks outside current week are not shown (or could go to backlog)
    }
  });

  return groups;
};
```

### 5. Responsive Layout

```javascript
const styles = {
  container: {
    display: "grid",
    gridTemplateColumns: "repeat(8, 1fr)", // 7 days + backlog
    gap: "1px",
    backgroundColor: designSystem.colors.border,
    minHeight: "calc(100vh - 120px)",
  },

  // Responsive breakpoints via media query or JS detection
  containerMobile: {
    gridTemplateColumns: "1fr", // Stack columns on mobile
    gap: "0",
  },

  column: {
    backgroundColor: designSystem.colors.background,
    minWidth: "120px",
    display: "flex",
    flexDirection: "column",
  },

  dayHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    borderBottom: `1px solid ${designSystem.colors.border}`,
    textAlign: "center",
  },

  dayNumber: {
    fontSize: "2rem",
    fontWeight: "normal",
    lineHeight: 1,
  },

  dayName: {
    fontSize: "0.875rem",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: designSystem.colors.textMuted,
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

  checkbox: {
    marginTop: "2px",
    cursor: "pointer",
  },

  taskTitle: {
    flex: 1,
    wordBreak: "break-word",
  },

  taskCompleted: {
    textDecoration: "line-through",
    color: designSystem.colors.completed,
  }
};
```

### 6. Mobile Responsiveness Strategy

Two approaches:

**Option A: CSS-in-JS with window width detection**
```javascript
const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

useEffect(() => {
  const handleResize = () => setIsMobile(window.innerWidth < 768);
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

**Option B: Horizontal scroll on mobile**
```javascript
containerWrapper: {
  overflowX: "auto",
  WebkitOverflowScrolling: "touch",
}
```

### 7. Week Navigation UI

```javascript
const WeekNavigation = ({ weekOffset, setWeekOffset, weekStart }) => (
  <div style={styles.navigation}>
    <button
      onClick={() => setWeekOffset(w => w - 1)}
      style={styles.navButton}
    >
      ← Previous
    </button>

    <span style={styles.weekLabel}>
      {weekStart.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
    </span>

    <button
      onClick={() => setWeekOffset(w => w + 1)}
      style={styles.navButton}
    >
      Next →
    </button>

    {weekOffset !== 0 && (
      <button
        onClick={() => setWeekOffset(0)}
        style={styles.todayButton}
      >
        Today
      </button>
    )}
  </div>
);
```

## Code References

- `web/src/App.jsx:1-291` - Current monolithic component to be refactored
- `web/src/App.jsx:3-83` - Current inline styles to be replaced
- `web/src/App.jsx:86-91` - State management (keep, extend with weekOffset)
- `web/src/App.jsx:118-131` - Task loading logic (reuse as-is)
- `web/src/App.jsx:151-163` - Toggle complete logic (reuse as-is)
- `web/src/App.jsx:165-174` - Delete task logic (reuse as-is)
- `szymon/services/google_tasks.py:16-26` - Task schemas (due date field)

## Architecture Insights

### Patterns to Follow

1. **Keep inline styles** - No need to add CSS dependencies, matches existing pattern
2. **Single component file** - Could split into multiple components in same file for organization
3. **State at top level** - Week offset and tasks state in main App component
4. **Derived state via useMemo** - Group tasks by date, calculate week days

### Design Principles for Minimal Calendar

1. **Typography hierarchy**: Large day numbers (Times New Roman), small task text (Courier New)
2. **Whitespace**: Generous padding, let content breathe
3. **Borders**: Subtle 1px borders to separate columns
4. **Color restraint**: Near-black text, light gray borders, no bright colors except for actions
5. **No shadows**: Keep flat, minimal aesthetic
6. **Responsive**: Stack columns on mobile or allow horizontal scroll

### Suggested File Structure (optional refactor)

```
web/src/
├── App.jsx              # Main app, state management
├── components/
│   ├── Calendar.jsx     # Calendar grid
│   ├── DayColumn.jsx    # Single day column
│   ├── TaskItem.jsx     # Task display
│   └── Navigation.jsx   # Week navigation
├── styles/
│   └── designSystem.js  # Shared style constants
└── utils/
    └── dateUtils.js     # Week calculation helpers
```

However, keeping everything in `App.jsx` is also acceptable for this project size.

## Implementation Checklist

- [ ] Create design system constants (fonts, colors, spacing)
- [ ] Add week calculation utility functions
- [ ] Add `weekOffset` state for navigation
- [ ] Create task grouping logic (by due date + backlog)
- [ ] Build calendar grid layout (8 columns)
- [ ] Style day headers (Times New Roman, large numbers)
- [ ] Style task items (Courier New, checkboxes)
- [ ] Add week navigation buttons
- [ ] Handle responsive layout
- [ ] Test with real Google Tasks data
- [ ] Verify task operations still work

## Open Questions

1. **Tasks outside current week**: Should they be hidden, shown in backlog, or shown with visual indicator?
2. **Creating new tasks**: Should clicking a day pre-fill the due date?
3. **Drag and drop**: Future feature to reschedule tasks by dragging between columns?
4. **Today highlight**: Should current day have special styling?
5. **Task count badge**: Show number of tasks in collapsed mobile view?
