import { useState, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";

const designSystem = {
  fonts: {
    calendar: "'Times New Roman', Times, serif",
    tasks: "'Courier New', Courier, monospace",
    ui: "system-ui, -apple-system, sans-serif"
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

const formatTime = (dateTimeStr) => {
  const date = new Date(dateTimeStr);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
};

const groupEventsByDate = (events, weekDays) => {
  const groups = Object.fromEntries(weekDays.map(d => [d.toDateString(), []]));

  events.forEach(event => {
    // Handle all-day events (have date) vs timed events (have dateTime)
    const startStr = event.start?.dateTime || event.start?.date;
    if (!startStr) return;

    const startDate = new Date(startStr);
    startDate.setHours(0, 0, 0, 0);
    const dateKey = startDate.toDateString();

    if (groups[dateKey] !== undefined) {
      groups[dateKey].push(event);
    }
  });

  // Sort events by start time within each day
  Object.keys(groups).forEach(key => {
    groups[key].sort((a, b) => {
      const aTime = new Date(a.start?.dateTime || a.start?.date);
      const bTime = new Date(b.start?.dateTime || b.start?.date);
      return aTime - bTime;
    });
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
  viewTabs: {
    display: "flex",
    gap: designSystem.spacing.xs,
    padding: designSystem.spacing.md,
    borderBottom: `1px solid ${designSystem.colors.border}`,
  },
  viewTab: {
    padding: `${designSystem.spacing.sm} ${designSystem.spacing.md}`,
    textDecoration: "none",
    color: designSystem.colors.textMuted,
    borderRadius: "4px",
  },
  viewTabActive: {
    backgroundColor: designSystem.colors.backgroundToday,
    color: designSystem.colors.text,
    fontWeight: "500",
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
    gridTemplateColumns: "repeat(7, 1fr)",
    minHeight: "calc(100vh - 180px)",
  },
  column: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  columnToday: {
    backgroundColor: designSystem.colors.backgroundToday,
  },
  dayHeader: {
    fontFamily: designSystem.fonts.calendar,
    padding: designSystem.spacing.md,
    textAlign: "center",
  },
  dayNumber: {
    fontSize: "96pt",
    fontWeight: "bold",
    lineHeight: 1,
  },
  dayName: {
    fontSize: "16px",
    fontWeight: "bold",
    color: designSystem.colors.text,
    marginTop: designSystem.spacing.xs,
  },
  taskList: {
    flex: 1,
    overflowY: "auto",
    padding: designSystem.spacing.xs,
  },
  eventItem: {
    fontFamily: designSystem.fonts.tasks,
    fontSize: "0.8125rem",
    padding: designSystem.spacing.sm,
    borderBottom: `1px solid ${designSystem.colors.borderLight}`,
  },
  eventTime: {
    fontSize: "0.75rem",
    color: designSystem.colors.textMuted,
    marginBottom: "2px",
  },
  eventTitle: {
    wordBreak: "break-word",
  },
  eventLocation: {
    fontSize: "0.75rem",
    color: designSystem.colors.textMuted,
    marginTop: "2px",
  },
  calendarSelector: {
    padding: designSystem.spacing.sm,
    border: `1px solid ${designSystem.colors.border}`,
    borderRadius: "4px",
    fontFamily: designSystem.fonts.ui,
    fontSize: "0.875rem",
    backgroundColor: designSystem.colors.background,
    marginLeft: "auto",
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

export default function Calendar() {
  const location = useLocation();
  const [health, setHealth] = useState(null);
  const [authStatus, setAuthStatus] = useState(null);
  const [events, setEvents] = useState([]);
  const [calendars, setCalendars] = useState([]);
  const [selectedCalendar, setSelectedCalendar] = useState("primary");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weekOffset, setWeekOffset] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Mobile detection
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fetch health on mount
  useEffect(() => {
    fetch("/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  // Calculate week
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const weekStart = useMemo(() => {
    const start = getWeekStart(new Date());
    start.setDate(start.getDate() + weekOffset * 7);
    return start;
  }, [weekOffset]);

  const weekEnd = useMemo(() => {
    const end = new Date(weekStart);
    end.setDate(end.getDate() + 7);
    return end;
  }, [weekStart]);

  const weekDays = useMemo(() => getWeekDays(weekStart), [weekStart]);

  const groupedEvents = useMemo(
    () => groupEventsByDate(events, weekDays),
    [events, weekDays]
  );

  const checkAuthAndLoad = async () => {
    try {
      const authRes = await fetch("/api/calendar/auth/status");
      const auth = await authRes.json();
      setAuthStatus(auth);

      if (auth.configured && auth.authenticated) {
        await loadCalendars();
        await loadEvents();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCalendars = async () => {
    try {
      const res = await fetch("/api/calendar/calendars");
      if (!res.ok) throw new Error("Failed to load calendars");
      const data = await res.json();
      setCalendars(data);
    } catch (e) {
      console.error("Failed to load calendars:", e);
    }
  };

  const loadEvents = async () => {
    try {
      const timeMin = weekStart.toISOString();
      const timeMax = weekEnd.toISOString();
      const res = await fetch(
        `/api/calendar/events?calendar_id=${selectedCalendar}&time_min=${timeMin}&time_max=${timeMax}`
      );
      if (!res.ok) throw new Error("Failed to load events");
      const data = await res.json();
      setEvents(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    checkAuthAndLoad();
  }, []);

  useEffect(() => {
    if (authStatus?.authenticated) {
      loadEvents();
    }
  }, [weekOffset, selectedCalendar]);

  return (
    <div style={styles.app}>
      {error && <div style={styles.error}>{error}</div>}

      {loading ? (
        <div style={styles.loading}>Loading...</div>
      ) : !authStatus?.configured ? (
        <div style={styles.authMessage}>
          <p>Google Calendar not configured.</p>
          <p>
            Set <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> in <code>.env</code>
          </p>
        </div>
      ) : !authStatus?.authenticated ? (
        <div style={styles.authMessage}>
          <p>Not authenticated with Google Calendar.</p>
          <a href="/api/calendar/auth/login" style={styles.authLink}>
            Login with Google
          </a>
        </div>
      ) : (
        <>
          {/* View Navigation Tabs */}
          <div style={styles.viewTabs}>
            <a
              href="/"
              style={{
                ...styles.viewTab,
                ...(location.pathname === "/" ? styles.viewTabActive : {}),
              }}
            >
              Tasks
            </a>
            <a
              href="/calendar"
              style={{
                ...styles.viewTab,
                ...(location.pathname === "/calendar" ? styles.viewTabActive : {}),
              }}
            >
              Calendar
            </a>
          </div>

          {/* Navigation */}
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

            {/* Calendar selector */}
            <select
              style={styles.calendarSelector}
              value={selectedCalendar}
              onChange={(e) => setSelectedCalendar(e.target.value)}
            >
              {calendars.map(cal => (
                <option key={cal.id} value={cal.id}>
                  {cal.summary}
                </option>
              ))}
            </select>
          </div>

          {/* Week Grid */}
          <div style={isMobile ? styles.mobileContainer : styles.calendarContainer}>
            {weekDays.map((day) => {
              const dateKey = day.toDateString();
              const isToday = isSameDay(day, today);
              const dayEvents = groupedEvents[dateKey] || [];

              return (
                <div
                  key={dateKey}
                  style={{
                    ...styles.column,
                    ...(isToday ? styles.columnToday : {}),
                    ...(isMobile ? styles.mobileColumn : {}),
                  }}
                >
                  <div style={styles.dayHeader}>
                    <div style={styles.dayNumber}>{day.getDate()}</div>
                    <div style={styles.dayName}>
                      {day.toLocaleDateString('en-US', { weekday: 'long' })}
                    </div>
                  </div>

                  <div style={styles.taskList}>
                    {dayEvents.map((event) => (
                      <div key={event.id} style={styles.eventItem}>
                        {event.start?.dateTime && (
                          <div style={styles.eventTime}>
                            {formatTime(event.start.dateTime)}
                            {event.end?.dateTime && ` - ${formatTime(event.end.dateTime)}`}
                          </div>
                        )}
                        <div style={styles.eventTitle}>{event.summary}</div>
                        {event.location && (
                          <div style={styles.eventLocation}>{event.location}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
