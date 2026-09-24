const loginPanel = document.querySelector("#packager-login");
const managerShell = document.querySelector("#manager-shell");
const loginForm = document.querySelector("#packager-login-form");
const loginMessage = document.querySelector("#login-message");
const sessionKey = "triplens_packager_session";
let packagerSession = null;
try {
  packagerSession = JSON.parse(sessionStorage.getItem(sessionKey) || "null");
} catch {
  sessionStorage.removeItem(sessionKey);
}

function formatError(data) {
  if (!data) return "Something went wrong";
  if (typeof data === "string") return data;
  if (data.detail) {
    const detail = data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((e) => {
          const loc = Array.isArray(e && e.loc) ? e.loc.slice(1).join(" → ") : "";
          const message = e && e.msg ? e.msg : JSON.stringify(e);
          return loc ? `${loc}: ${message}` : message;
        })
        .join("\n");
    }
    return JSON.stringify(detail);
  }
  if (typeof data === "object") {
    const errors = Object.entries(data).flatMap(([field, value]) => {
      if (Array.isArray(value)) {
        return value.map((msg) => `${field}: ${typeof msg === "string" ? msg : JSON.stringify(msg)}`);
      }
      if (value && typeof value === "object") {
        return Object.entries(value).map(([nestedField, nestedValue]) => `${field}.${nestedField}: ${Array.isArray(nestedValue) ? nestedValue.join(", ") : nestedValue}`);
      }
      return [`${field}: ${value}`];
    });
    if (errors.length) return errors.join("\n");
  }
  return JSON.stringify(data);
}

function showManager(session) {
  packagerSession = session;
  sessionStorage.setItem(sessionKey, JSON.stringify(session));
  if (loginMessage) {
    loginMessage.textContent = "";
    loginMessage.style.color = "";
  }
  if (loginPanel) loginPanel.hidden = true;
  if (managerShell) managerShell.hidden = false;
  const loggedInAs = document.querySelector("#logged-in-as");
  if (loggedInAs) loggedInAs.textContent = `Signed in as ${session.agency_name || session.email}`;
}

function clearManagerSession() {
  sessionStorage.removeItem(sessionKey);
  packagerSession = null;
  if (managerShell) managerShell.hidden = true;
  if (loginPanel) loginPanel.hidden = false;
  const emailInput = document.querySelector("#packager-email");
  const passwordInput = document.querySelector("#packager-password");
  if (emailInput) emailInput.value = "";
  if (passwordInput) passwordInput.value = "";
  if (loginMessage) {
    loginMessage.textContent = "";
    loginMessage.style.color = "";
  }
}

if (packagerSession && ["packager", "admin"].includes(packagerSession.role) && packagerSession.session_token) showManager(packagerSession);

const packagerLogoutBtn = document.querySelector("#packager-logout");
if (packagerLogoutBtn) packagerLogoutBtn.addEventListener("click", clearManagerSession);

if (loginForm) {
  loginForm.addEventListener("submit", async event => {
    event.preventDefault();
    const emailInput = document.querySelector("#packager-email");
    const passwordInput = document.querySelector("#packager-password");
    if (loginMessage) {
      loginMessage.textContent = "Signing in…";
      loginMessage.style.color = "";
    }
    try {
      const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: emailInput.value, password: passwordInput.value }) });
      const body = await response.json();
      if (!response.ok) throw new Error(formatError(body));
      if (!["packager", "admin"].includes(body.role)) throw new Error("This account is not authorized to manage packages.");
      showManager(body);
    } catch (error) {
      if (loginMessage) {
        loginMessage.style.color = "#B91C1C";
        loginMessage.textContent = error.message || "Authentication failed";
      }
    }
  });
}

const googlePackagerBtn = document.querySelector("#google-packager-sign-in");
if (googlePackagerBtn) {
  googlePackagerBtn.addEventListener("click", async () => {
    try {
      const config = await fetch("/api/auth/google-config").then(response => response.json());
      if (!config.enabled || !window.google) throw new Error("Google sign-in is not configured yet.");
      google.accounts.id.initialize({
        client_id: config.client_id,
        callback: async response => {
          const result = await fetch("/api/auth/google", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ credential: response.credential, role: "packager" }) });
          const body = await result.json();
          if (!result.ok) throw new Error(formatError(body));
          showManager(body);
        }
      });
      google.accounts.id.prompt();
    } catch (error) {
      if (loginMessage) {
        loginMessage.style.color = "#B91C1C";
        loginMessage.textContent = error.message || "Google sign-in failed.";
      }
    }
  });
}

const coreFields = [
  ["package_id", "Package ID (e.g. HP016)", "text"], ["agency_name", "Agency name", "text"], ["package_name", "Package name", "text"],
  ["destinations", "Destinations (comma-separated)", "text"], ["start_location", "Start location", "text"], ["duration_days", "Duration days", "number"],
  ["duration_nights", "Duration nights", "number"], ["price", "Price (₹)", "number"], ["list_price", "List price (₹)", "number"],
  ["transport_type", "Transport type", "text"], ["theme", "Theme", "text"], ["itinerary_pace", "Pace", "text"], ["agency_contact", "Agency contact", "text"]
];
const core = document.querySelector("#core-fields");
const itinerary = document.querySelector("#itinerary-fields");
const stays = document.querySelector("#accommodation-fields");
const packageForm = document.querySelector("#package-form");

if (core) {
  core.innerHTML = coreFields.map(([id,label,type]) => `<div class="form-group"><label class="form-label" for="${id}">${label}</label><input class="form-select" id="${id}" type="${type}" ${type === "number" ? "min=\"0\" step=\"any\"" : ""} required></div>`).join("");
}

const daysInput = document.querySelector("#duration_days");

function dayFields(day) { return `<fieldset class="pref-card" style="margin:.75rem 0"><legend>Day ${day}</legend><div class="pref-grid">${[["stops","Stops"],["activities","Activities"],["activity_type","Activity type"],["distance_km","Distance (km)","number"],["transit_hours","Transit hours","number"],["stops_requiring_separate_drives","Separate drives","number"],["meals_included_today","Meals included"]].map(([key,label,type="text"])=>`<div class="form-group"><label class="form-label">${label}</label><input class="form-select" data-day="${day}" data-key="${key}" type="${type}" ${type==="number"?"min=\"0\" step=\"any\"":""} required></div>`).join("")}</div></fieldset>`; }

function renderDays() {
  if (!daysInput || !itinerary) return;
  const count = Number(daysInput.value) || 0;
  itinerary.innerHTML = count ? Array.from({ length: count }, (_, i) => dayFields(i + 1)).join("") : "<p>Enter duration days to generate itinerary fields.</p>";
}

function ensureItineraryFields() {
  if (!daysInput || !itinerary) return;
  const expectedDays = Number(daysInput.value) || 0;
  const renderedDays = new Set(Array.from(itinerary.querySelectorAll("[data-day]"), (element) => element.dataset.day));
  if (renderedDays.size !== expectedDays) renderDays();
}

if (daysInput) {
  daysInput.addEventListener("input", renderDays);
}
renderDays();
window.addEventListener("load", ensureItineraryFields);
window.addEventListener("pageshow", ensureItineraryFields);
setTimeout(ensureItineraryFields, 0);

function addDay() {
  if (!daysInput) return;
  const count = Number(daysInput.value) || 0;
  daysInput.value = count + 1;
  renderDays();
}

function addStay() {
  if (!stays) return;
  const n = stays.children.length + 1;
  stays.insertAdjacentHTML("beforeend",`<div class="pref-card" style="margin:.75rem 0"><strong>Stay ${n}</strong><div class="pref-grid">${[["destination","Destination"],["accommodation_category","Accommodation category"],["hotel_name","Hotel name"]].map(([k,l])=>`<div class="form-group"><label class="form-label">${l}</label><input class="form-select" data-stay="${n}" data-key="${k}" required></div>`).join("")}<div class="form-group"><label class="form-label">Hotel guaranteed</label><select class="form-select" data-stay="${n}" data-key="hotel_guaranteed"><option>Yes</option><option>No</option></select></div></div></div>`);
}

const addStayBtn = document.querySelector("#add-stay");
if (addStayBtn) addStayBtn.addEventListener("click", addStay);
const addDayBtn = document.querySelector("#add-day");
if (addDayBtn) addDayBtn.addEventListener("click", addDay);
if (stays) addStay();

function lines(id){ const element = document.querySelector(id); return element ? element.value.split("\n").map(x=>x.trim()).filter(Boolean) : []; }

if (packageForm) {
  packageForm.addEventListener("submit", async event => {
    event.preventDefault();
    ensureItineraryFields();
    const payload = Object.fromEntries(coreFields.map(([id]) => [id, document.querySelector(`#${id}`).value]));
    payload.duration_days = Number(payload.duration_days);
    payload.duration_nights = Number(payload.duration_nights);
    payload.price = Number(payload.price);
    payload.list_price = Number(payload.list_price);

    const message = document.querySelector("#form-message");
    const validationErrors = [];

    if (!payload.package_id || !payload.package_id.trim()) validationErrors.push("Package ID is required.");
    if (!payload.agency_name || !payload.agency_name.trim()) validationErrors.push("Agency name is required.");
    if (!payload.package_name || !payload.package_name.trim()) validationErrors.push("Package name is required.");
    if (!payload.destinations || !payload.destinations.trim()) validationErrors.push("Destinations are required.");
    if (!payload.start_location || !payload.start_location.trim()) validationErrors.push("Start location is required.");
    if (!Number.isFinite(payload.duration_days) || payload.duration_days < 1) validationErrors.push("Duration days must be at least 1.");
    if (!Number.isFinite(payload.duration_nights) || payload.duration_nights < 0) validationErrors.push("Duration nights must be 0 or more.");
    if (Number.isFinite(payload.duration_days) && Number.isFinite(payload.duration_nights) && payload.duration_days > 0 && payload.duration_nights !== payload.duration_days - 1) {
      validationErrors.push(`Duration nights must equal duration days - 1 (for ${payload.duration_days} days, nights must be ${payload.duration_days - 1}).`);
    }
    if (!Number.isFinite(payload.price) || payload.price < 0) validationErrors.push("Price must be a valid non-negative number.");
    if (!Number.isFinite(payload.list_price) || payload.list_price < 0) validationErrors.push("List price must be a valid non-negative number.");
    if (payload.list_price < payload.price) validationErrors.push("List price must be greater than or equal to price.");
    if (!payload.transport_type || !payload.transport_type.trim()) validationErrors.push("Transport type is required.");
    if (!payload.theme || !payload.theme.trim()) validationErrors.push("Theme is required.");
    if (!payload.itinerary_pace || !payload.itinerary_pace.trim()) validationErrors.push("Pace is required.");
    if (!payload.agency_contact || !payload.agency_contact.trim()) validationErrors.push("Agency contact is required.");

    payload.itinerary = Array.from({ length: payload.duration_days || 0 }, (_, i) => {
      const d = i + 1;
      const obj = { day_number: d };
      document.querySelectorAll(`[data-day="${d}"]`).forEach((el) => {
        const key = el.dataset.key;
        const value = ["distance_km", "transit_hours", "stops_requiring_separate_drives"].includes(key) ? Number(el.value) : el.value;
        obj[key] = value;
      });
      return obj;
    });

    if (payload.duration_days > 0 && payload.itinerary.length !== payload.duration_days) {
      validationErrors.push("Add one itinerary row for each duration day.");
    }

    if (!payload.duration_days || payload.itinerary.length === 0) {
      validationErrors.push("Add at least one day in the itinerary section.");
    }
    payload.itinerary.forEach((day, index) => {
      ["stops", "activities", "activity_type", "meals_included_today"].forEach((key) => {
        if (!day[key] || !day[key].trim()) validationErrors.push(`Day ${index + 1}: ${key.replaceAll("_", " ")} is required.`);
      });
    });

    payload.accommodation = [];
    const stayPanels = document.querySelectorAll("#accommodation-fields .pref-card");
    stayPanels.forEach((panel) => {
      const obj = {};
      panel.querySelectorAll("[data-stay]").forEach((el) => {
        obj[el.dataset.key] = el.value;
      });
      payload.accommodation.push(obj);
    });

    if (payload.accommodation.length === 0 || payload.accommodation.some((stay) => !stay.destination || !stay.accommodation_category || !stay.hotel_name || !stay.hotel_guaranteed)) {
      validationErrors.push("Complete each stay with destination, accommodation category, hotel name, and hotel guaranteed.");
    }

    payload.inclusions = lines("#inclusions");
    payload.exclusions = lines("#exclusions");
    if (!payload.inclusions.length) validationErrors.push("Add at least one inclusion item.");
    if (!payload.exclusions.length) validationErrors.push("Add at least one exclusion item.");

    if (validationErrors.length) {
      if (message) {
        message.style.color = "#B91C1C";
        message.textContent = validationErrors.join("\n");
      }
      return;
    }

    try {
      const res = await fetch("/api/packages", { method: "POST", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${packagerSession.session_token}` }, body: JSON.stringify(payload) });
      const body = await res.json();
      if (!res.ok) throw new Error(formatError(body));
      if (message) {
        message.style.color = "var(--primary)";
        message.textContent = body.excel_updated
          ? `Saved ${body.package_id}. Database and Excel workbooks updated successfully.`
          : `Saved ${body.package_id}. Database updated, but Excel workbooks were not updated. Close the workbook and save again.`;
      }
      event.target.reset();
      if (stays) {
        stays.innerHTML = "";
        addStay();
      }
      if (daysInput) daysInput.value = "";
      renderDays();
    } catch (error) {
      if (error.message.includes("login required") || error.message.includes("Only packagers")) {
        clearManagerSession();
      }
      if (message) {
        message.style.color = "#B91C1C";
        message.textContent = error.message || "Could not save package";
      }
    }
  });
}
