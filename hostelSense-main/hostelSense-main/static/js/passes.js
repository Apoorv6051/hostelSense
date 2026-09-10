// ==========================================
// HostelSense — Central Passes Engine
// ==========================================

const LOCAL_STORAGE_KEY = "hs_passes_store";

// --- Fallback Default Passes ---
function defaultPasses() {
  return [
    {
      id: "gp-101",
      studentName: "Aarav Sharma",
      roll: "2401641520038",
      type: "home",
      typeLabel: "Home visit",
      destination: "Lucknow",
      reason: "Family function",
      from: "2026-09-12T17:00",
      to: "2026-09-14T20:00",
      parentStatus: "approved",
      wardenStatus: "pending",
      createdAt: new Date().toISOString()
    }
  ];
}

// ==========================================
// 1. Backend SQLite API Functions (Async)
// ==========================================

// Fetch passes from Flask Backend / SQLite Database
async function fetchPassesFromDB(roll = null) {
  try {
    const endpoint = roll ? `/api/passes?roll=${encodeURIComponent(roll)}` : "/api/passes";
    const res = await fetch(endpoint);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const data = await res.json();
    
    // Sync to localStorage as a client-side cache
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(data));
    return data;
  } catch (err) {
    console.warn("DB Fetch failed, falling back to localStorage cache:", err);
    return loadPasses();
  }
}

// Insert new pass into Flask SQLite Database
async function addPassToDB(passData) {
  try {
    const res = await fetch("/api/passes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(passData)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const result = await res.json();
    
    // Also save in local cache
    addPass(result.pass || passData);
    return result;
  } catch (err) {
    console.warn("DB Post failed, saving locally:", err);
    addPass(passData);
  }
}

// Update status (Approve / Reject) in Database
async function updatePassStatusInDB(passId, updates) {
  try {
    const res = await fetch(`/api/passes/${passId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const result = await res.json();
    
    // Keep local cache updated
    updatePass(passId, updates);
    return result;
  } catch (err) {
    console.warn("DB Patch failed, updating locally:", err);
    updatePass(passId, updates);
  }
}

// ==========================================
// 2. Synchronous Helpers (Used by HTML pages)
// ==========================================

// Load passes from memory / localStorage
function loadPasses() {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) {
      const initial = defaultPasses();
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(initial));
      return initial;
    }
    return JSON.parse(raw);
  } catch (_) {
    return defaultPasses();
  }
}

// Filter passes by student roll number
function passesForRoll(roll) {
  return loadPasses().filter((p) => String(p.roll) === String(roll));
}

// Save a list to localStorage
function savePasses(list) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(list));
  } catch (_) {}
}

// Add a pass to localStorage and notify backend
function addPass(pass) {
  const list = loadPasses();
  list.unshift(pass);
  savePasses(list);

  // Background sync to DB if not already triggered
  fetch("/api/passes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pass)
  }).catch(() => {});
}

// Update an existing pass in local store and sync with backend
function updatePass(id, updates) {
  const list = loadPasses();
  const index = list.findIndex((p) => String(p.id) === String(id));
  if (index !== -1) {
    list[index] = { ...list[index], ...updates };
    savePasses(list);

    // Background sync to DB
    fetch(`/api/passes/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    }).catch(() => {});
  }
}

// ==========================================
// 3. UI Status & Formatting Helpers
// ==========================================

function overallStatus(p) {
  if (p.parentStatus === "rejected" || p.wardenStatus === "rejected") return "rejected";
  if (p.parentStatus === "approved" && p.wardenStatus === "approved") return "approved";
  return "pending";
}

function statusLabel(p) {
  const st = overallStatus(p);
  if (st === "approved") return "Approved";
  if (st === "rejected") return "Rejected";
  return "Pending review";
}

function typeEmoji(type) {
  switch (type) {
    case "outing":
      return "🏙️";
    case "home":
      return "🏠";
    case "medical":
      return "🏥";
    default:
      return "📋";
  }
}

function formatWhen(dtStr) {
  if (!dtStr) return "";
  try {
    const d = new Date(dtStr);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch (_) {
    return dtStr;
  }
}

// ==========================================
// 4. Geofencing Engine
// ==========================================

window.checkGeofence = window.checkGeoFence = window.executeGeofence = async function () {
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async function (position) {
      const payload = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      };

      try {
        const res = await fetch("/api/verify-location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          alert("Server Error: " + (errData.error || res.statusText));
          return;
        }

        const result = await res.json();
        if (result.inside) {
          alert(`Verified: You are inside the hostel perimeter (${result.distance_meters}m from center).`);
        } else {
          alert(`Outside Perimeter: You are ${result.distance_meters}m away. Must be within ${result.allowed_radius}m.`);
        }
      } catch (err) {
        alert("Connection error: Could not reach Flask backend.");
        console.error(err);
      }
    },
    function (error) {
      alert(`Location error (${error.code}): ${error.message}\nPlease ensure location permission is allowed.`);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
};

// Initial background sync with DB on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchPassesFromDB();
});