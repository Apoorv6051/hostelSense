/* HostelSense — shared demo storage (localStorage) */

function hsLoad(key, defaults) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      localStorage.setItem(key, JSON.stringify(defaults));
      return defaults.slice();
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : defaults.slice();
  } catch (_) {
    return defaults.slice();
  }
}

function hsSave(key, list) {
  try {
    localStorage.setItem(key, JSON.stringify(list));
  } catch (_) {
    /* ignore quota / private mode */
  }
}

function hsAdd(key, item, defaults) {
  const list = hsLoad(key, defaults);
  list.unshift(item);
  hsSave(key, list);
  return list;
}

function hsUpdate(key, id, patch, defaults) {
  const list = hsLoad(key, defaults).map((item) =>
    item.id === id ? { ...item, ...patch } : item
  );
  hsSave(key, list);
  return list;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatWhen(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch (_) {
    return value;
  }
}

function formatDay(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch (_) {
    return value;
  }
}

function toLocalInput(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ========== Visitors ========== */

const HS_VISITORS_KEY = "hs_visitors";

const DEFAULT_VISITORS = [];

function loadVisitors() {
  return hsLoad(HS_VISITORS_KEY, DEFAULT_VISITORS);
}

function addVisitor(visitor) {
  return hsAdd(HS_VISITORS_KEY, visitor, DEFAULT_VISITORS);
}

function updateVisitor(id, patch) {
  return hsUpdate(HS_VISITORS_KEY, id, patch, DEFAULT_VISITORS);
}

function visitorsForRoll(roll) {
  return loadVisitors().filter((v) => v.roll === roll);
}

function visitorStatusChip(status) {
  if (status === "checked_in") return { className: "approved", label: "Checked in" };
  if (status === "completed") return { className: "approved", label: "Done" };
  if (status === "rejected") return { className: "rejected", label: "Denied" };
  return { className: "pending", label: "Expected" };
}

/* ========== Complaints ========== */

const HS_COMPLAINTS_KEY = "hs_complaints";

const DEFAULT_COMPLAINTS = [];

function loadComplaints() {
  return hsLoad(HS_COMPLAINTS_KEY, DEFAULT_COMPLAINTS);
}

function addComplaint(item) {
  return hsAdd(HS_COMPLAINTS_KEY, item, DEFAULT_COMPLAINTS);
}

function updateComplaint(id, patch) {
  return hsUpdate(HS_COMPLAINTS_KEY, id, patch, DEFAULT_COMPLAINTS);
}

function complaintsForRoll(roll) {
  return loadComplaints().filter((c) => c.roll === roll);
}

function complaintStatusChip(status) {
  if (status === "resolved") return { className: "approved", label: "Resolved" };
  if (status === "in_progress") return { className: "pending", label: "In progress" };
  return { className: "pending", label: "Open" };
}

/* ========== Notices ========== */

const HS_NOTICES_KEY = "hs_notices";

const DEFAULT_NOTICES = [
  {
    id: "ntc-demo-1",
    title: "Evening headcount at 9:00 PM",
    body: "All Block C residents must be inside by 9:00 PM tonight. Missing students will auto-flag parents.",
    audience: "all",
    priority: "high",
    author: "Warden office",
    createdAt: "2026-09-10T08:00:00.000Z",
  },
  {
    id: "ntc-demo-2",
    title: "Mess menu update",
    body: "Sunday special dinner will include paneer and fruit dessert.",
    audience: "students",
    priority: "normal",
    author: "Mess committee",
    createdAt: "2026-09-09T16:00:00.000Z",
  },
  {
    id: "ntc-demo-3",
    title: "Parent visiting hours",
    body: "Weekends 10:00 AM – 5:00 PM at the visitor lounge. Carry a photo ID.",
    audience: "parents",
    priority: "normal",
    author: "Hostel admin",
    createdAt: "2026-09-08T11:00:00.000Z",
  },
];

function loadNotices() {
  return hsLoad(HS_NOTICES_KEY, DEFAULT_NOTICES);
}

function addNotice(item) {
  return hsAdd(HS_NOTICES_KEY, item, DEFAULT_NOTICES);
}

function noticesForRole(role) {
  return loadNotices().filter((n) => n.audience === "all" || n.audience === role || !n.audience);
}

function noticeTimeLabel(iso, author) {
  const who = author || "Hostel";
  try {
    const d = new Date(iso);
    const now = new Date();
    const sameDay =
      d.getFullYear() === now.getFullYear() &&
      d.getMonth() === now.getMonth() &&
      d.getDate() === now.getDate();
    if (sameDay) return "Today · " + who;
    const y = new Date(now);
    y.setDate(now.getDate() - 1);
    const yesterday =
      d.getFullYear() === y.getFullYear() &&
      d.getMonth() === y.getMonth() &&
      d.getDate() === y.getDate();
    if (yesterday) return "Yesterday · " + who;
    return formatDay(iso) + " · " + who;
  } catch (_) {
    return iso;
  }
}

function renderNoticeHtml(n) {
  const author = n.author || "Hostel";
  return `<div class="notice">
    <span class="notice-dot${n.priority === "high" ? " amber" : ""}" aria-hidden="true"></span>
    <div>
      <strong>${escapeHtml(n.title)}</strong>
      <p>${escapeHtml(n.body)}</p>
      <time>${escapeHtml(noticeTimeLabel(n.createdAt, author))}</time>
    </div>
  </div>`;
}

/* ========== Attendance (generated demo, not persisted) ========== */

function loadAttendance(roll) {
  const days = [];
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  for (let i = 13; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    const weekday = d.getDay();
    const isWeekend = weekday === 0;
    let status = "present";
    if (isWeekend) status = i === 6 ? "leave" : "present";
    else if (i === 3) status = "late";
    else if (i === 9) status = "absent";

    const events = [];
    if (status === "present" || status === "late") {
      const inHour = status === "late" ? 9 : 7;
      const inMin = status === "late" ? 12 : 42;
      events.push({
        time: `${String(inHour).padStart(2, "0")}:${String(inMin).padStart(2, "0")}`,
        label: "Entry",
        detail: "Main gate · face verified",
        kind: "in",
      });
      if (status === "present" && weekday !== 0) {
        events.push({
          time: "12:15",
          label: "Mess scan",
          detail: "Lunch · Block C mess",
          kind: "in",
        });
      }
      if (i > 0) {
        events.push({
          time: "21:05",
          label: "Evening headcount",
          detail: "Block C sweep · present",
          kind: "in",
        });
      }
    } else if (status === "leave") {
      events.push({
        time: "—",
        label: "Home leave",
        detail: "Approved gate pass",
        kind: "out",
      });
    } else {
      events.push({
        time: "—",
        label: "No scan",
        detail: "Marked absent · parent notified",
        kind: "out",
      });
    }

    days.push({
      date: d.toISOString(),
      roll,
      status,
      events,
    });
  }
  return days;
}

function attendanceChip(status) {
  if (status === "present") return { className: "approved", label: "Present" };
  if (status === "late") return { className: "pending", label: "Late" };
  if (status === "leave") return { className: "pending", label: "Leave" };
  return { className: "rejected", label: "Absent" };
}

/* ========== Student roster ========== */

const DEFAULT_STUDENTS = [];

function loadStudents() {
  return DEFAULT_STUDENTS.slice();
}
