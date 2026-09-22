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

const DEFAULT_VISITORS = [
  {
    id: "vis-demo-1",
    name: "Mrs. Sharma",
    relation: "parent",
    relationLabel: "Parent",
    studentName: "Aarav Sharma",
    roll: "2401641520038",
    when: "2026-09-10T16:00",
    purpose: "Weekend lounge visit · ID ready",
    phone: "9876543210",
    status: "expected",
    createdBy: "parent",
    createdAt: "2026-09-09T10:00:00.000Z",
  },
  {
    id: "vis-demo-2",
    name: "Courier",
    relation: "other",
    relationLabel: "Package drop",
    studentName: "Aarav Sharma",
    roll: "2401641520038",
    when: "2026-09-10T11:20",
    purpose: "Package left at reception",
    phone: "",
    status: "completed",
    createdBy: "warden",
    createdAt: "2026-09-10T11:15:00.000Z",
  },
];

function loadVisitors() {
  return hsLoad(HS_VISITORS_KEY, DEFAULT_VISITORS);
}

function addVisitor(visitor) {
  return hsAdd(HS_VISITORS_KEY, visitor, DEFAULT_VISITORS);
}

function updateVisitor(id, patch) {
  return hsUpdate(HS_VISITORS_KEY, id, patch, DEFAULT_VISITORS);
}

async function syncVisitorsFromDB(roll) {
  try {
    const endpoint = roll ? `/api/visitors?roll=${encodeURIComponent(roll)}` : "/api/visitors";
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const remote = await response.json();
    const local = loadVisitors();
    const merged = [...remote, ...local.filter((item) => !remote.some((entry) => entry.id === item.id))];
    hsSave(HS_VISITORS_KEY, merged);
    return roll ? visitorsForRoll(roll) : merged;
  } catch (_) {
    return roll ? visitorsForRoll(roll) : loadVisitors();
  }
}

async function addVisitorToDB(visitor) {
  addVisitor(visitor);
  try {
    const response = await fetch("/api/visitors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(visitor),
    });
    if (response.ok) {
      const result = await response.json();
      if (result.visitor) updateVisitor(result.visitor.id, result.visitor);
    }
  } catch (_) {}
  return loadVisitors();
}

async function updateVisitorInDB(id, patch) {
  updateVisitor(id, patch);
  try {
    const response = await fetch(`/api/visitors/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (response.ok) {
      const result = await response.json();
      if (result.visitor) updateVisitor(result.visitor.id, result.visitor);
    }
  } catch (_) {}
  return loadVisitors();
}

async function verifyVisitorEntry(value) {
  const response = await fetch("/api/visitors/verify-entry", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || `HTTP ${response.status}`);
  }
  if (result.visitor) updateVisitor(result.visitor.id, result.visitor);
  return result.visitor;
}

async function issueVisitorQr(visitor) {
  const token = visitor.qrToken || `HS-VISIT-${visitor.id}-${Date.now()}`;
  const payload = {
    type: "hostelsense-visitor",
    token,
    visitorId: visitor.id,
    visitorName: visitor.name,
    visitorPhone: visitor.phone || "",
    studentName: visitor.studentName,
    studentRoll: visitor.roll,
    relationship: visitor.relationLabel || visitor.relation || "Visitor",
    requestedFor: visitor.when,
    purpose: visitor.purpose || "",
  };
  await updateVisitorInDB(visitor.id, {
    status: "expected",
    qrToken: token,
    qrPayload: JSON.stringify(payload),
    qrIssuedAt: new Date().toISOString(),
  });
  return { ...visitor, ...payload, status: "expected", qrToken: token, qrPayload: JSON.stringify(payload) };
}

function visitorsForRoll(roll) {
  const targetRoll = String(roll ?? "").trim();
  if (!targetRoll) return [];
  return loadVisitors().filter(
    (visitor) => String(visitor.roll ?? "").trim() === targetRoll
  );
}

function visitorArrivalNotificationsForRoll(roll) {
  return visitorsForRoll(roll).filter(
    (visitor) => visitor.status === "checked_in" && visitor.arrivedAt
  );
}

function visitorStatusChip(status) {
  if (status === "checked_in") return { className: "approved", label: "Checked in" };
  if (status === "completed") return { className: "approved", label: "Done" };
  if (status === "rejected") return { className: "rejected", label: "Denied" };
  if (status === "pending") return { className: "pending", label: "Awaiting warden" };
  return { className: "pending", label: "Expected" };
}

/* ========== Complaints ========== */

const HS_COMPLAINTS_KEY = "hs_complaints";

const DEFAULT_COMPLAINTS = [
  {
    id: "cmp-demo-1",
    studentName: "Aarav Sharma",
    roll: "2401641520038",
    room: "C-214 · Block C",
    category: "maintenance",
    categoryLabel: "Maintenance",
    title: "AC not cooling",
    body: "Room AC has been weak since yesterday evening. Requesting a check today.",
    status: "open",
    createdAt: "2026-09-09T18:40:00.000Z",
  },
];

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

/* ========== Attendance ========== */

const HS_ATTENDANCE_KEY = "hs_attendance";

function addAttendance(item) {
  const records = hsLoad(HS_ATTENDANCE_KEY, []);
  const alreadyRecorded = records.some(
    (record) => record.roll === item.roll && record.date === item.date && record.type === item.type
  );
  if (!alreadyRecorded) hsSave(HS_ATTENDANCE_KEY, [item, ...records]);
}

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

  hsLoad(HS_ATTENDANCE_KEY, [])
    .filter((record) => record.roll === roll)
    .forEach((record) => {
      const day = days.find((item) => item.date.slice(0, 10) === record.date);
      if (!day) return;
      day.status = "present";
      day.events = day.events.filter((event) => event.label !== "Evening attendance");
      day.events.push({
        time: record.time,
        label: "Evening attendance",
        detail: "Face verified · evening headcount",
        kind: "in",
      });
    });

  return days;
}

function attendanceChip(status) {
  if (status === "present") return { className: "approved", label: "Present" };
  if (status === "late") return { className: "pending", label: "Late" };
  if (status === "leave") return { className: "pending", label: "Leave" };
  return { className: "rejected", label: "Absent" };
}

/* ========== Student roster (warden demo) ========== */

const DEMO_STUDENTS = [
  { name: "Aarav Sharma", roll: "2401641520038", room: "C-214", floor: 2, status: "inside", course: "B.Tech CSE · Year 2" },
  { name: "Diya Kapoor", roll: "2401641520104", room: "C-108", floor: 1, status: "inside", course: "B.Tech ECE · Year 2" },
  { name: "Rohan Mehta", roll: "2401641520211", room: "C-221", floor: 2, status: "out", course: "B.Tech CSE · Year 3" },
  { name: "Isha Nair", roll: "2401641520088", room: "C-305", floor: 3, status: "inside", course: "B.Tech IT · Year 1" },
  { name: "Kabir Singh", roll: "2401641520156", room: "C-412", floor: 4, status: "inside", course: "B.Tech ME · Year 2" },
  { name: "Ananya Rao", roll: "2401641520031", room: "C-119", floor: 1, status: "inside", course: "B.Tech CSE · Year 1" },
  { name: "Vivaan Joshi", roll: "2401641520190", room: "C-330", floor: 3, status: "out", course: "B.Tech ECE · Year 3" },
  { name: "Meera Iyer", roll: "2401641520067", room: "C-207", floor: 2, status: "inside", course: "B.Tech CSE · Year 2" },
];

const HS_STUDENTS_KEY = "hs_students";

function loadStudents() {
  return hsLoad(HS_STUDENTS_KEY, DEMO_STUDENTS);
}

function studentByRoll(roll) {
  return loadStudents().find((s) => String(s.roll) === String(roll));
}

function addStudent(student) {
  const list = loadStudents();
  if (list.some((s) => String(s.roll) === String(student.roll))) {
    return { ok: false, error: "A student with this roll number is already on the roster." };
  }
  list.unshift(student);
  hsSave(HS_STUDENTS_KEY, list);
  return { ok: true, list };
}
