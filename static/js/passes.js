/* HostelSense — gate-pass storage with Flask API + localStorage fallback */

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
    /* ignore quota / private mode */
  }
}

function addPass(pass) {
  const list = loadPasses();
  if (!list.some((p) => String(p.id) === String(pass.id))) {
    list.unshift(pass);
    savePasses(list);
  }
  return list;
}

function updatePass(id, patch) {
  const list = loadPasses().map((p) =>
    String(p.id) === String(id) ? { ...p, ...patch } : p
  );
  savePasses(list);
  return list;
}

function passesForRoll(roll) {
  return loadPasses().filter((p) => String(p.roll) === String(roll));
}

async function fetchPassesFromDB(roll) {
  try {
    const endpoint = roll
      ? `/api/passes?roll=${encodeURIComponent(roll)}`
      : "/api/passes";
    const res = await fetch(endpoint, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    if (Array.isArray(data)) {
      savePasses(data);
      return data;
    }
    return loadPasses();
  } catch (_) {
    return loadPasses();
  }
}

async function addPassToDB(pass) {
  const res = await fetch("/api/passes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pass),
  });
  if (!res.ok) {
    throw new Error("HTTP " + res.status);
  }
  const result = await res.json();
  if (!result.pass) throw new Error("Pass was not returned by the server");
  addPass(result.pass);
  return loadPasses();
}

async function updatePassStatusInDB(id, patch) {
  try {
    const response = await fetch(`/api/passes/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const result = await response.json();
    if (result.pass) {
      updatePass(id, result.pass);
      return result.pass;
    }
  } catch (_) {
    updatePass(id, patch);
  }
  return loadPasses();
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
  return "";
}

async function checkGeofence() {
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by this browser.");
    return null;
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const res = await fetch("/api/verify-location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
            }),
          });
          if (!res.ok) {
            alert("Could not verify location with the hostel server.");
            resolve(null);
            return;
          }
          const result = await res.json();
          resolve(result);
        } catch (_) {
          alert("Could not reach the hostel server to verify location.");
          resolve(null);
        }
      },
      (error) => {
        alert("Location permission is needed to verify you are on campus.");
        console.warn(error);
        resolve(null);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });
}

window.checkGeofence = window.checkGeoFence = checkGeofence;
