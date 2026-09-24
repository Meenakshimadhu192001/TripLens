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

function showManager(session) {
  packagerSession = session;
  sessionStorage.setItem(sessionKey, JSON.stringify(session));
  loginPanel.hidden = true;
  managerShell.hidden = false;
  document.querySelector("#logged-in-as").textContent = `Signed in as ${session.agency_name || session.email}`;
}

function clearManagerSession() {
  sessionStorage.removeItem(sessionKey);
  packagerSession = null;
  managerShell.hidden = true;
  loginPanel.hidden = false;
}

if (packagerSession && ["packager", "admin"].includes(packagerSession.role) && packagerSession.session_token) showManager(packagerSession);
document.querySelector("#packager-logout").addEventListener("click", clearManagerSession);
loginForm.addEventListener("submit", async event => {
  event.preventDefault();
  loginMessage.textContent = "Signing in…";
  try {
    const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: document.querySelector("#packager-email").value, password: document.querySelector("#packager-password").value }) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Invalid login");
    if (!["packager", "admin"].includes(body.role)) throw new Error("This account is not authorized to manage packages.");
    showManager(body);
  } catch (error) {
    loginMessage.style.color = "#B91C1C";
    loginMessage.textContent = error.message;
  }
});

document.querySelector("#google-packager-sign-in").addEventListener("click", async () => {
  try {
    const config = await fetch("/api/auth/google-config").then(response => response.json());
    if (!config.enabled || !window.google) throw new Error("Google sign-in is not configured yet.");
    google.accounts.id.initialize({
      client_id: config.client_id,
      callback: async response => {
        const result = await fetch("/api/auth/google", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ credential: response.credential, role: "packager" }) });
        const body = await result.json();
        if (!result.ok) throw new Error(body.detail || "Google sign-in failed.");
        showManager(body);
      }
    });
    google.accounts.id.prompt();
  } catch (error) {
    loginMessage.style.color = "#B91C1C";
    loginMessage.textContent = error.message;
  }
});

const coreFields = [
  ["package_id", "Package ID (e.g. HP016)", "text"], ["agency_name", "Agency name", "text"], ["package_name", "Package name", "text"],
  ["destinations", "Destinations (comma-separated)", "text"], ["start_location", "Start location", "text"], ["duration_days", "Duration days", "number"],
  ["duration_nights", "Duration nights", "number"], ["price", "Price (₹)", "number"], ["list_price", "List price (₹)", "number"],
  ["transport_type", "Transport type", "text"], ["theme", "Theme", "text"], ["itinerary_pace", "Pace", "text"], ["agency_contact", "Agency contact", "text"]
];
const core = document.querySelector("#core-fields");
core.innerHTML = coreFields.map(([id,label,type]) => `<div class="form-group"><label class="form-label" for="${id}">${label}</label><input class="form-select" id="${id}" type="${type}" ${type === "number" ? "min=\"0\" step=\"any\"" : ""} required></div>`).join("");
const daysInput = document.querySelector("#duration_days");
const itinerary = document.querySelector("#itinerary-fields");
function dayFields(day) { return `<fieldset class="pref-card" style="margin:.75rem 0"><legend>Day ${day}</legend><div class="pref-grid">${[["stops","Stops"],["activities","Activities"],["activity_type","Activity type"],["distance_km","Distance (km)","number"],["transit_hours","Transit hours","number"],["stops_requiring_separate_drives","Separate drives","number"],["meals_included_today","Meals included"]].map(([key,label,type="text"])=>`<div class="form-group"><label class="form-label">${label}</label><input class="form-select" data-day="${day}" data-key="${key}" type="${type}" ${type==="number"?"min=\"0\" step=\"any\"":""} required></div>`).join("")}</div></fieldset>`; }
function renderDays(){ const count=Number(daysInput.value)||0; itinerary.innerHTML=count ? Array.from({length:count},(_,i)=>dayFields(i+1)).join("") : "<p>Enter duration days to generate itinerary fields.</p>"; }
daysInput.addEventListener("input",renderDays);
const stays=document.querySelector("#accommodation-fields");
function addStay(){ const n=stays.children.length+1; stays.insertAdjacentHTML("beforeend",`<div class="pref-card" style="margin:.75rem 0"><strong>Stay ${n}</strong><div class="pref-grid">${[["destination","Destination"],["accommodation_category","Accommodation category"],["hotel_name","Hotel name"]].map(([k,l])=>`<div class="form-group"><label class="form-label">${l}</label><input class="form-select" data-stay="${n}" data-key="${k}" required></div>`).join("")}<div class="form-group"><label class="form-label">Hotel guaranteed</label><select class="form-select" data-stay="${n}" data-key="hotel_guaranteed"><option>Yes</option><option>No</option></select></div></div></div>`); }
document.querySelector("#add-stay").addEventListener("click",addStay); addStay();
function lines(id){ return document.querySelector(id).value.split("\n").map(x=>x.trim()).filter(Boolean); }
document.querySelector("#package-form").addEventListener("submit",async event=>{ event.preventDefault(); const payload=Object.fromEntries(coreFields.map(([id])=>[id,document.querySelector(`#${id}`).value])); ["duration_days","duration_nights","price","list_price"].forEach(k=>payload[k]=Number(payload[k])); payload.itinerary=Array.from({length:payload.duration_days},(_,i)=>{const d=i+1,obj={day_number:d}; document.querySelectorAll(`[data-day="${d}"]`).forEach(el=>obj[el.dataset.key]=["distance_km","transit_hours","stops_requiring_separate_drives"].includes(el.dataset.key)?Number(el.value):el.value); return obj;}); payload.accommodation=[]; for(let i=1;i<=stays.children.length;i++){const obj={};document.querySelectorAll(`[data-stay="${i}"]`).forEach(el=>obj[el.dataset.key]=el.value);payload.accommodation.push(obj);} payload.inclusions=lines("#inclusions");payload.exclusions=lines("#exclusions"); const message=document.querySelector("#form-message"); try{const res=await fetch("/api/packages",{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${packagerSession.session_token}`},body:JSON.stringify(payload)});const body=await res.json();if(!res.ok)throw new Error(body.detail||"Could not save package");message.style.color="var(--primary)";message.textContent=`Saved ${body.package_id}. Database updated successfully.`;event.target.reset();stays.innerHTML="";addStay();renderDays();}catch(error){if(error.message.includes("login required")||error.message.includes("Only packagers")){clearManagerSession();}message.style.color="#B91C1C";message.textContent=error.message;}});
