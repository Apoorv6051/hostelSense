document.addEventListener("DOMContentLoaded", () => {
    fetchAndDisplayPasses();
    attachPassFormListener();
});

// 1. Fetch & display passes dynamically
async function fetchAndDisplayPasses() {
    const listContainer = document.querySelector(".list") || document.querySelector("#pass-list");
    if (!listContainer) return;

    try {
        const response = await fetch("/api/passes");
        const data = await response.json();
        
        listContainer.innerHTML = "";

        if (data.length === 0) {
            listContainer.innerHTML = `<div class="empty-state">No active pass requests.</div>`;
            return;
        }

        const isWarden = window.location.pathname.includes("warden");

        data.forEach(p => {
            const item = document.createElement("li");
            item.className = "list-item list-item-stack";

            let wardenControls = "";
            if (isWarden && p.status === "pending") {
                wardenControls = `
                    <div class="btn-row">
                        <button class="btn-approve" onclick="changePassStatus(${p.id}, 'approved')">Approve</button>
                        <button class="btn-reject" onclick="changePassStatus(${p.id}, 'rejected')">Reject</button>
                    </div>
                `;
            }

            item.innerHTML = `
                <div class="list-item-top">
                    <div class="list-item-main">
                        <strong>${p.type} — ${p.student_name} (${p.room})</strong>
                        <span>Reason: ${p.reason}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <span class="chip ${p.status}">${p.status.toUpperCase()}</span>${wardenControls}
                    </div>
                </div>
                <div class="meta-row">
                    <span class="meta-pill">Out: ${p.out_time}</span>
                    <span class="meta-pill">In: ${p.in_time}</span>
                    <span class="meta-pill">Destination: ${p.destination}</span>
                </div>
            `;
            listContainer.appendChild(item);
        });
    } catch (err) {
        console.error("Failed to load passes:", err);
    }
}

// 2. Submit a new pass request
function attachPassFormListener() {
    const form = document.querySelector("form");
    if (!form || window.location.pathname.includes("index") || window.location.pathname === "/") return;

    let selectedType = "Day Pass";
    const pills = document.querySelectorAll(".type-pill");
    pills.forEach(pill => {
        pill.addEventListener("click", () => {
            pills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            selectedType = pill.innerText.trim();
        });
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const getVal = (name) => {
            const el = form.querySelector(`[name='${name}']`);
            return el ? el.value : "";
        };

        const payload = {
            type: selectedType,
            reason: getVal("reason") || "Personal work",
            destination: getVal("destination") || "Local",
            out_time: getVal("out_time") || "Today",
            in_time: getVal("in_time") || "Today",
            student_name: getVal("student_name") || "Student",
            room: getVal("room") || "B-204"
        };

        try {
            const res = await fetch("/api/passes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert("Pass submitted to warden successfully!");
                window.location.href = "/student";
            }
        } catch (err) {
            console.error("Submission failed:", err);
        }
    });
}

// 3. Warden approval action
window.changePassStatus = async function(passId, status) {
    try {
        const res = await fetch(`/api/passes/${passId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status })
        });
        if (res.ok) {
            fetchAndDisplayPasses();
        }
    } catch (err) {
        console.error("Status update failed:", err);
    }
};