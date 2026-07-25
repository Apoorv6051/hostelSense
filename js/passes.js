/* HostelSense — shared gate-pass storage (demo, localStorage) */

const HS_PASSES_KEY = "hs_passes";

const DEFAULT_PASSES = [
  {
    id: "gp-demo-1",
    studentName: "Aarav Sharma",
    roll: "2401641520038",
    type: "home",
    typeLabel: "Home visit",
    destination: "Home — Lucknow",
    reason: "Weekend visit with family",
    from: "2026-07-26T10:00",
    to: "2026-07-27T20:00",
    parentStatus: "approved",
    wardenStatus: "pending",
    createdAt: "2026-07-24T09:00:00.000Z",
  },
  {
    id: "gp-demo-2",
    studentName: "Aarav Sharma",
    roll: "2401641520038",
    type: "outing",
    typeLabel: "City outing",
    destination: "City mall",
    reason: "Personal shopping",
    from: "2026-07-18T16:00",
    to: "2026-07-18T20:30",
    parentStatus: "approved",
    wardenStatus: "approved",
    createdAt: "2026-07-17T11:00:00.000Z",
  },
];

function loadPasses() {
  try {
    const raw = localStorage.getItem(HS_PASSES_KEY);
    if (!raw) {
      localStorage.setItem(HS_PASSES_KEY, JSON.stringify(DEFAULT_PASSES));
      return DEFAULT_PASSES.slice();
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : DEFAULT_PASSES.slice();
  } catch (_) {
    return DEFAULT_PASSES.slice();
  }
}

function savePasses(list) {
  try {
    localStorage.setItem(HS_PASSES_KEY, JSON.stringify(list));
  } catch (_) {
    /* ignore */
  }
}

function addPass(pass) {
  const list = loadPasses();
  list.unshift(pass);
  savePasses(list);
  return list;
}

function updatePass(id, patch) {
  const list = loadPasses().map((p) => (p.id === id ? { ...p, ...patch } : p));
  savePasses(list);
  return list;
}

function passesForRoll(roll) {
  return loadPasses().filter((p) => p.roll === roll);
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

function overallStatus(pass) {
  if (pass.parentStatus === "rejected" || pass.wardenStatus === "rejected") {
    return "rejected";
  }
  if (pass.parentStatus === "approved" && pass.wardenStatus === "approved") {
    return "approved";
  }
  return "pending";
}

function statusLabel(pass) {
  const o = overallStatus(pass);
  if (o === "approved") return "Approved";
  if (o === "rejected") return "Rejected";
  if (pass.parentStatus === "pending") return "Awaiting parent";
  if (pass.wardenStatus === "pending") return "Awaiting warden";
  return "Pending";
}

function typeEmoji(type) {
  const map = { outing: "🏙️", home: "🏠", medical: "🏥", other: "📋" };
  return map[type] || "🎫";
}
