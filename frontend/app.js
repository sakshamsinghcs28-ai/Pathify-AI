/**
 * Pathify-AI Frontend Application Logic
 */

// Application State
const state = {
  roles: [],
  selectedRoleId: "role-1",
  userSkills: new Set(),
  skillProficiencies: {},
  gapAnalysisResult: null,
  roadmapData: null,
  chatHistory: [],
  savedProfileId: null,
  authToken: localStorage.getItem("pathify_token") || null,
  currentUser: null,
  authMode: "login",
  redirectAfterLogin: null,
};

const PROTECTED_TABS = ["dashboard", "careers", "skillgap", "roadmap", "chat", "resume"];

function getAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (state.authToken) {
    headers["Authorization"] = `Bearer ${state.authToken}`;
  }
  return headers;
}

function isAuthenticated() {
  return !!(state.currentUser && state.authToken);
}

function resetApplicationState() {
  // Clear persistent tokens & profile IDs
  localStorage.removeItem("pathify_token");
  localStorage.removeItem("pathify_profile_id");
  sessionStorage.clear();

  // Reset core auth & user state
  state.authToken = null;
  state.currentUser = null;
  state.savedProfileId = null;
  state.redirectAfterLogin = null;

  // Reset skills and proficiencies to completely clean initial state
  state.userSkills = new Set();
  state.skillProficiencies = {};
  state.selectedRoleId = "role-1";
  state.gapAnalysisResult = null;
  state.roadmapData = null;

  // Reset AI chat history in memory
  state.chatHistory = [];

  // Reset Resume Analyzer state & DOM
  if (typeof window.resetResumeState === "function") {
    window.resetResumeState();
  } else if (typeof resetResumeState === "function") {
    resetResumeState();
  }

  // Clear rendered skills selector
  if (typeof populateSkillSelector === "function") {
    populateSkillSelector();
  }

  // Clear rendered roadmap steps in DOM
  const roadmapContainer = document.getElementById("roadmap-steps-container");
  if (roadmapContainer) roadmapContainer.innerHTML = "";
  const roadmapOverview = document.getElementById("roadmap-overview");
  if (roadmapOverview) roadmapOverview.classList.add("hidden");

  // Clear rendered skill gap results in DOM
  const gapResults = document.getElementById("gap-analysis-results");
  if (gapResults) gapResults.classList.add("hidden");

  // Reset chat messages in DOM
  const chatMessages = document.getElementById("chat-messages");
  if (chatMessages) {
    chatMessages.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
          <i data-lucide="bot" class="w-4 h-4"></i>
        </div>
        <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl rounded-tl-sm p-4 text-xs sm:text-sm text-slate-200 space-y-2 max-w-[85%]">
          <p>👋 <strong>Welcome to Pathify-AI Career & Skill Advisor!</strong></p>
          <p class="text-slate-400">Ask me anything about tech roles, required skills, interview prep, or career roadmap milestones.</p>
        </div>
      </div>
    `;
    if (window.lucide) setTimeout(() => lucide.createIcons(), 50);
  }

  updateNavAuthUI();
}

async function loadUserProfile() {
  if (!state.authToken || !state.currentUser) return;

  try {
    const res = await fetch(`${API_BASE}/api/profiles/me`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (res.ok) {
      const data = await res.json();
      if (data && data.profile) {
        const p = data.profile;
        state.savedProfileId = p.id;
        try {
          localStorage.setItem("pathify_profile_id", p.id);
        } catch (_) {}

        if (p.targetRoleId) {
          state.selectedRoleId = p.targetRoleId;
          const roleSelect = document.getElementById("gap-role-select");
          if (roleSelect) roleSelect.value = p.targetRoleId;
          const resumeRoleSelect = document.getElementById("resume-target-role");
          if (resumeRoleSelect) resumeRoleSelect.value = p.targetRoleId;
        }

        // Restore user's own saved skills
        if (Array.isArray(p.skills) && p.skills.length > 0) {
          state.userSkills = new Set(p.skills);
          p.skills.forEach((s) => {
            if (!state.skillProficiencies[s]) {
              state.skillProficiencies[s] = "Intermediate";
            }
          });
        } else {
          state.userSkills = new Set();
          state.skillProficiencies = {};
        }

        if (typeof populateSkillSelector === "function") {
          populateSkillSelector();
        }

        await loadCurrentRoadmap();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load user profile:", err);
  }

  // Brand-new account with no profile saved yet:
  state.savedProfileId = null;
  state.userSkills = new Set();
  state.skillProficiencies = {};
  if (typeof populateSkillSelector === "function") {
    populateSkillSelector();
  }
}

async function loadCurrentRoadmap() {
  if (!state.authToken || !state.currentUser) return;
  try {
    const roadmapUrl = state.savedProfileId
      ? `${API_BASE}/api/profiles/${state.savedProfileId}/roadmap?roleId=${encodeURIComponent(state.selectedRoleId || "role-1")}`
      : `${API_BASE}/api/profiles/me/roadmap?roleId=${encodeURIComponent(state.selectedRoleId || "role-1")}`;

    const res = await fetch(roadmapUrl, {
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.ok) {
      const data = await res.json();
      if (data && data.roadmap && data.roadmap.length > 0) {
        state.roadmapData = data;
        if (typeof renderRoadmapView === "function") {
          renderRoadmapView();
        }
      }
    }
  } catch (err) {
    console.warn("Could not load current roadmap:", err);
  }
}

function handleUnauthorized() {
  if (state.authToken || state.currentUser) {
    resetApplicationState();
    showToast("Your session has expired. Please sign in again.", "warning");
    openAuthView("login");
  }
}

function getTabDisplayName(tab) {
  const names = {
    dashboard: "Dashboard",
    careers: "Careers",
    skillgap: "Skill Gap Analysis",
    resume: "Resume Analyzer",
    roadmap: "Personalized Roadmap",
    chat: "AI Mentor",
  };
  return names[tab] || tab;
}

// Determine API Base URL intelligently:
// - If loaded over HTTP/HTTPS in a browser, use window.location.origin (works for production Render domains, custom domains, and local unified port 5000/8000).
// - If loaded from a separate frontend dev server (e.g. Live Server on 5500 or 3000), point to backend on 5000.
// - If loaded via file:// protocol or non-browser, fall back to http://127.0.0.1:5000.
function determineApiBase() {
  if (typeof window !== "undefined" && window.location && window.location.origin) {
    const protocol = window.location.protocol;
    if (protocol === "http:" || protocol === "https:") {
      const port = window.location.port;
      if (port === "5500" || port === "3000") {
        return "http://127.0.0.1:5000";
      }
      return window.location.origin;
    }
  }
  return "http://127.0.0.1:5000";
}

let API_BASE = determineApiBase();

// -------------------------------------------------------------
// Theme Management (Dark Mode & Light Mode)
// -------------------------------------------------------------
function getCurrentTheme() {
  return localStorage.getItem("pathify_theme") || "dark";
}

function applyTheme(theme) {
  const root = document.documentElement;
  const isLight = theme === "light";

  if (isLight) {
    root.classList.remove("dark");
    root.classList.add("light");
  } else {
    root.classList.remove("light");
    root.classList.add("dark");
  }

  // Update desktop toggle button
  const desktopBtn = document.getElementById("theme-toggle-btn");
  if (desktopBtn) {
    desktopBtn.setAttribute("title", isLight ? "Switch to Dark Mode" : "Switch to Light Mode");
    desktopBtn.setAttribute("aria-label", isLight ? "Switch to Dark Mode" : "Switch to Light Mode");
    desktopBtn.innerHTML = isLight
      ? '<i data-lucide="moon" class="w-4 h-4 text-indigo-600"></i>'
      : '<i data-lucide="sun" class="w-4 h-4 text-amber-400"></i>';
  }

  // Update mobile toggle button
  const mobileBtn = document.getElementById("mobile-theme-btn");
  if (mobileBtn) {
    mobileBtn.setAttribute("title", isLight ? "Switch to Dark Mode" : "Switch to Light Mode");
    mobileBtn.innerHTML = isLight
      ? '<i data-lucide="moon" class="w-4 h-4 text-indigo-600"></i><span id="mobile-theme-text" class="text-[10px]">Dark</span>'
      : '<i data-lucide="sun" class="w-4 h-4 text-amber-400"></i><span id="mobile-theme-text" class="text-[10px]">Light</span>';
  }

  if (window.lucide) {
    lucide.createIcons();
  }
}

function toggleTheme() {
  const currentTheme = getCurrentTheme();
  const nextTheme = currentTheme === "light" ? "dark" : "light";
  localStorage.setItem("pathify_theme", nextTheme);
  applyTheme(nextTheme);
}

function initTheme() {
  const savedTheme = getCurrentTheme();
  applyTheme(savedTheme);
}

// Initialize application on load
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  if (window.lucide) {
    lucide.createIcons();
  }

  // Handle URL deep-links (e.g. ?token=... or ?mode=forgot)
  if (typeof window !== "undefined" && window.location) {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      window.location.href = `reset-password.html?token=${encodeURIComponent(token)}`;
      return;
    }
  }

  await checkHealth();
  await restoreUserSession();

  const params = (typeof window !== "undefined" && window.location)
    ? new URLSearchParams(window.location.search)
    : new URLSearchParams();
  const modeParam = params.get("mode");
  const hash = (typeof window !== "undefined" && window.location.hash)
    ? window.location.hash.replace(/^#/, "")
    : "";

  // If user is authenticated, load roles and open requested or dashboard tab
  if (isAuthenticated()) {
    await loadRoles();
    if (PROTECTED_TABS.includes(hash)) {
      switchTab(hash, false);
    } else {
      switchTab("dashboard", false);
    }
  } else {
    // Unauthenticated: inspect query params (?mode=...) or hash for desired auth mode or protected page
    if (PROTECTED_TABS.includes(hash)) {
      state.redirectAfterLogin = hash;
      showToast(`Please sign in to access ${getTabDisplayName(hash)}.`, "info");
      openAuthView("login");
    } else if (modeParam === "register" || hash === "register") {
      openAuthView("register");
    } else if (modeParam === "forgot" || hash === "forgot") {
      openAuthView("forgot");
    } else {
      openAuthView("login");
    }
  }

  // Route listeners for URL hash changes, browser back/forward, and bfcache restoration
  window.addEventListener("hashchange", handleRoute);
  window.addEventListener("popstate", handleRoute);
  window.addEventListener("pageshow", (event) => {
    if (event.persisted && !isAuthenticated()) {
      openAuthView("login");
    }
  });

  // Periodic health check every 15 seconds to ensure status stays accurate
  setInterval(checkHealth, 15000);
});

// Centralized Route Handler for browser navigation & hash changes
function handleRoute() {
  const params = (typeof window !== "undefined" && window.location)
    ? new URLSearchParams(window.location.search)
    : new URLSearchParams();
  const modeParam = params.get("mode");
  const hash = (typeof window !== "undefined" && window.location.hash)
    ? window.location.hash.replace(/^#/, "")
    : "";

  if (PROTECTED_TABS.includes(hash)) {
    if (!isAuthenticated()) {
      state.redirectAfterLogin = hash;
      showToast(`Please sign in to access ${getTabDisplayName(hash)}.`, "info");
      openAuthView("login");
    } else {
      switchTab(hash, false);
    }
  } else if (modeParam === "register" || hash === "register") {
    openAuthView("register");
  } else if (modeParam === "forgot" || hash === "forgot") {
    openAuthView("forgot");
  } else if (modeParam === "login" || hash === "login" || hash === "auth") {
    openAuthView("login");
  }
}

// -------------------------------------------------------------
// Navigation Tabs & Centralized Route Guard
// -------------------------------------------------------------
function getAuthUrl(mode = "login") {
  if (typeof window === "undefined" || !window.location) return `index.html?mode=${mode}`;
  const path = window.location.pathname || "/";
  const basePath = path.endsWith(".html")
    ? path
    : (path.endsWith("/") ? `${path}index.html` : `${path}/index.html`);
  return `${basePath}?mode=${mode}`;
}

function switchTab(tabName, updateHash = true) {
  // Enforce authentication guard for protected tabs
  if (PROTECTED_TABS.includes(tabName) && !isAuthenticated()) {
    state.redirectAfterLogin = tabName;
    showToast(`Please sign in to access ${getTabDisplayName(tabName)}.`, "info");
    openAuthView("login");
    return;
  }

  const tabs = ["dashboard", "careers", "skillgap", "resume", "roadmap", "chat", "auth"];
  tabs.forEach((tab) => {
    const viewEl = document.getElementById(`view-${tab}`);
    const navBtn = document.getElementById(`nav-${tab}`);
    if (viewEl) {
      if (tab === tabName) {
        viewEl.classList.remove("hidden");
      } else {
        viewEl.classList.add("hidden");
      }
    }
    if (navBtn) {
      if (tab === tabName) {
        navBtn.className = "nav-btn px-3 py-2 text-sm font-medium rounded-lg text-indigo-400 bg-slate-800/80 flex items-center gap-1.5 transition";
      } else {
        navBtn.className = "nav-btn px-3 py-2 text-sm font-medium rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 flex items-center gap-1.5 transition";
      }
    }
  });

  if (updateHash && typeof window !== "undefined" && window.location) {
    const path = window.location.pathname || "/";
    const basePath = path.endsWith(".html")
      ? path
      : (path.endsWith("/") ? `${path}index.html` : `${path}/index.html`);
    const targetUrl = tabName === "auth"
      ? `${basePath}?mode=${state.authMode || "login"}`
      : `${basePath}#${tabName}`;
    if (window.history && window.history.pushState) {
      window.history.pushState(null, "", targetUrl);
    }
  }

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }

  // Scroll to top smoothly
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Action hook on tab enter
  if (tabName === "skillgap") {
    syncRoleDropdowns(state.selectedRoleId);
    populateSkillSelector();
    runSkillGapAnalysis();
  } else if (tabName === "roadmap") {
    syncRoleDropdowns(state.selectedRoleId);
    loadRoadmap();
  } else if (tabName === "resume") {
    if (typeof initResumeView === "function") {
      initResumeView();
    }
  }
}

// -------------------------------------------------------------
// Health Check with Multi-Port Auto-Discovery
// -------------------------------------------------------------
function setHealthIndicator(connected) {
  const badge = document.getElementById("health-badge");
  const text = document.getElementById("health-text");
  const dot = document.getElementById("health-dot") || (badge ? badge.querySelector("span:first-child") : null);

  if (connected) {
    if (badge) {
      badge.className = "flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/80 border border-emerald-800/60 text-emerald-400";
    }
    if (dot) {
      dot.className = "w-2 h-2 rounded-full bg-emerald-400 animate-pulse";
    }
    if (text) {
      text.textContent = "API Connected";
    }
  } else {
    if (badge) {
      badge.className = "flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/80 border border-rose-800/60 text-rose-400";
    }
    if (dot) {
      dot.className = "w-2 h-2 rounded-full bg-rose-400";
    }
    if (text) {
      text.textContent = "API Disconnected";
    }
  }
}

async function checkHealth() {
  const candidates = [];
  if (typeof window !== "undefined" && window.location) {
    const port = window.location.port;
    if (port === "5000" || port === "8000") {
      candidates.push(window.location.origin);
    }
  }
  candidates.push("http://127.0.0.1:5000");
  candidates.push("http://localhost:5000");
  candidates.push("http://127.0.0.1:8000");
  candidates.push("http://localhost:8000");

  const uniqueCandidates = [...new Set(candidates.filter(Boolean))];

  for (const base of uniqueCandidates) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${base}/api/health`, {
        method: "GET",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json().catch(() => null);
        // Verify both API responsiveness and live database connectivity
        if (data && data.status === "ok" && (data.database === undefined || data.database === "connected")) {
          const previousBase = API_BASE;
          API_BASE = base;
          setHealthIndicator(true);
          if (previousBase !== base && state.roles.length === 0 && isAuthenticated()) {
            loadRoles();
          }
          return true;
        }
      }
    } catch (err) {
      // Candidate unreachable, continue probe
    }
  }

  // If all probes failed or database connection could not be verified
  setHealthIndicator(false);
  return false;
}

// -------------------------------------------------------------
// Load Roles from Backend
// -------------------------------------------------------------
async function loadRoles() {
  if (!isAuthenticated()) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/roles`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });
    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    const data = await res.json();
    if (data.success && data.roles) {
      state.roles = data.roles;
      renderDashboardRoles(data.roles);
      renderCareersCards(data.roles);
      populateRoleDropdown(data.roles);
    }
  } catch (err) {
    console.error("Failed to load roles from API", err);
    showToast("Error loading career roles from database.", "error");
  }
}

function getRoleIcon(slug) {
  if (slug === "role-1") return "code-2";
  if (slug === "role-2") return "bar-chart-3";
  if (slug === "role-3") return "cpu";
  return "briefcase";
}

function renderDashboardRoles(roles) {
  const container = document.getElementById("dashboard-roles-grid");
  if (!container) return;
  container.innerHTML = roles
    .map((role) => {
      const icon = getRoleIcon(role.id);
      return `
      <div class="bg-slate-900/60 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 transition flex flex-col justify-between glow-card">
        <div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <i data-lucide="${icon}" class="w-5 h-5"></i>
            </div>
            <span class="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-medium">${role.category}</span>
          </div>
          <h3 class="text-lg font-bold text-white">${role.title}</h3>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">${role.description}</p>
          <div class="mt-4 flex flex-wrap gap-1.5">
            ${role.requiredSkills.slice(0, 4).map((s) => `<span class="text-[11px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/50">${s}</span>`).join("")}
            ${role.requiredSkills.length > 4 ? `<span class="text-[11px] px-2 py-0.5 text-slate-500">+${role.requiredSkills.length - 4} more</span>` : ""}
          </div>
        </div>
        <button onclick="selectAndAnalyzeRole('${role.id}')" class="mt-5 w-full py-2.5 bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5">
          <span>Analyze Skill Gap</span>
          <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
        </button>
      </div>`;
    })
    .join("");

  if (window.lucide) lucide.createIcons();
}

function renderCareersCards(roles) {
  const container = document.getElementById("careers-roles-container");
  if (!container) return;
  container.innerHTML = roles
    .map((role) => {
      const icon = getRoleIcon(role.id);
      return `
      <div class="bg-slate-900/70 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 transition flex flex-col justify-between">
        <div>
          <div class="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4">
            <i data-lucide="${icon}" class="w-6 h-6"></i>
          </div>
          <span class="text-xs px-2.5 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 font-semibold">${role.category}</span>
          <h3 class="text-xl font-bold text-white mt-2">${role.title}</h3>
          <p class="text-sm text-slate-400 mt-2">${role.description}</p>
          <div class="mt-5">
            <div class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Required Core Skills (${role.requiredSkills.length}):</div>
            <div class="flex flex-wrap gap-1.5">
              ${role.requiredSkills.map((s) => `<span class="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700/60 font-medium">${s}</span>`).join("")}
            </div>
          </div>
        </div>
        <div class="pt-6 border-t border-slate-800 mt-6">
          <button onclick="selectAndAnalyzeRole('${role.id}')" class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-sm transition flex items-center justify-center gap-2">
            <i data-lucide="git-compare" class="w-4 h-4"></i> Check My Gaps for this Role
          </button>
        </div>
      </div>`;
    })
    .join("");

  if (window.lucide) lucide.createIcons();
}

function syncRoleDropdowns(roleId) {
  const gapSelect = document.getElementById("gap-role-select");
  const roadmapSelect = document.getElementById("roadmap-role-select");
  if (gapSelect && gapSelect.value !== roleId) gapSelect.value = roleId;
  if (roadmapSelect && roadmapSelect.value !== roleId) roadmapSelect.value = roleId;
}

function populateRoleDropdown(roles) {
  const gapSelect = document.getElementById("gap-role-select");
  const roadmapSelect = document.getElementById("roadmap-role-select");

  const optionsHtml = roles
    .map(
      (r) =>
        `<option value="${r.id}" ${
          r.id === state.selectedRoleId ? "selected" : ""
        }>${r.title} (${r.category})</option>`
    )
    .join("");

  if (gapSelect) gapSelect.innerHTML = optionsHtml;
  if (roadmapSelect) roadmapSelect.innerHTML = optionsHtml;
}

function selectAndAnalyzeRole(roleId) {
  state.selectedRoleId = roleId;
  syncRoleDropdowns(roleId);
  state.roadmapData = null;
  switchTab("skillgap");
}

function onRoleSelectionChanged() {
  const select = document.getElementById("gap-role-select");
  if (!select) return;
  state.selectedRoleId = select.value;
  syncRoleDropdowns(select.value);
  state.roadmapData = null;
  populateSkillSelector();
  runSkillGapAnalysis();
}

async function onRoadmapRoleSelectionChanged() {
  const select = document.getElementById("roadmap-role-select");
  if (!select) return;
  const newRoleId = select.value;
  state.selectedRoleId = newRoleId;
  syncRoleDropdowns(newRoleId);
  state.roadmapData = null;
  populateSkillSelector();
  runSkillGapAnalysis();
  await loadRoadmap(true);
}

// -------------------------------------------------------------
// Skill Gap Analyzer Logic & Career Assessment Engine
// -------------------------------------------------------------
function populateSkillSelector() {
  const currentRole = state.roles.find((r) => r.id === state.selectedRoleId);
  if (!currentRole) return;

  // Gather all unique skills from all roles for a rich pill checklist
  const allSkills = new Set();
  state.roles.forEach((r) => r.requiredSkills.forEach((s) => allSkills.add(s)));
  // Add any user custom skills
  state.userSkills.forEach((s) => allSkills.add(s));

  const container = document.getElementById("skill-pills-container");
  if (!container) return;

  container.innerHTML = Array.from(allSkills)
    .sort()
    .map((skill) => {
      const active = state.userSkills.has(skill);
      const currentLvl = (state.skillProficiencies && state.skillProficiencies[skill]) || "Intermediate";
      if (active) {
        return `
        <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-950/90 border border-emerald-600 text-emerald-200 text-xs font-medium shadow-sm transition">
          <i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i>
          <span class="font-semibold">${skill}</span>
          <select onchange="setSkillProficiency('${skill}', this.value)" class="ml-1 bg-slate-900 border border-emerald-600 text-emerald-300 text-[10px] font-bold rounded-lg px-1.5 py-0.5 focus:outline-none cursor-pointer">
            <option value="Beginner" ${currentLvl === "Beginner" ? "selected" : ""}>Beginner</option>
            <option value="Intermediate" ${currentLvl === "Intermediate" ? "selected" : ""}>Intermediate</option>
            <option value="Advanced" ${currentLvl === "Advanced" ? "selected" : ""}>Advanced</option>
            <option value="Expert" ${currentLvl === "Expert" ? "selected" : ""}>Expert</option>
          </select>
          <button type="button" onclick="toggleSkill('${skill}')" class="text-emerald-400 hover:text-rose-400 ml-0.5 p-0.5 transition" title="Remove skill">
            <i data-lucide="x" class="w-3 h-3"></i>
          </button>
        </div>`;
      } else {
        return `
        <button type="button" onclick="toggleSkill('${skill}')" class="px-2.5 py-1.5 rounded-xl text-xs font-medium transition flex items-center gap-1.5 bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700">
          <i data-lucide="plus" class="w-3 h-3 text-slate-400 shrink-0"></i>
          <span>${skill}</span>
        </button>`;
      }
    })
    .join("");

  if (window.lucide) lucide.createIcons();
}

function setSkillProficiency(skillName, level) {
  if (!state.skillProficiencies) state.skillProficiencies = {};
  state.skillProficiencies[skillName] = level;
  state.userSkills.add(skillName);
  state.savedProfileId = null;
  state.roadmapData = null;
  runSkillGapAnalysis();
}

function toggleSkill(skillName) {
  if (state.userSkills.has(skillName)) {
    state.userSkills.delete(skillName);
    if (state.skillProficiencies) delete state.skillProficiencies[skillName];
  } else {
    state.userSkills.add(skillName);
    if (!state.skillProficiencies) state.skillProficiencies = {};
    state.skillProficiencies[skillName] = "Intermediate";
  }
  state.savedProfileId = null;
  state.roadmapData = null;
  populateSkillSelector();
  runSkillGapAnalysis();
}

function addCustomSkill() {
  const input = document.getElementById("custom-skill-input");
  const val = input.value.trim();
  if (!val) return;
  state.userSkills.add(val);
  if (!state.skillProficiencies) state.skillProficiencies = {};
  state.skillProficiencies[val] = "Intermediate";
  state.savedProfileId = null;
  state.roadmapData = null;
  input.value = "";
  populateSkillSelector();
  runSkillGapAnalysis();
  showToast(`Added '${val}' to your skills.`, "success");
}

async function runSkillGapAnalysis(isUserClick = false) {
  const btn = document.getElementById("run-skillgap-btn");
  const spinner = document.getElementById("skillgap-btn-spinner");
  const icon = document.getElementById("skillgap-btn-icon");
  const text = document.getElementById("skillgap-btn-text");
  const errAlert = document.getElementById("gap-error-alert");
  const errText = document.getElementById("gap-error-text");

  // 1. Capture target career role
  const roleSelect = document.getElementById("gap-role-select");
  const roleId = (roleSelect && roleSelect.value) ? roleSelect.value : (state.selectedRoleId || "role-1");
  state.selectedRoleId = roleId;

  // 2. Capture custom skill if entered in input but not yet added
  const customInput = document.getElementById("custom-skill-input");
  if (customInput && customInput.value.trim()) {
    const val = customInput.value.trim();
    state.userSkills.add(val);
    if (!state.skillProficiencies) state.skillProficiencies = {};
    state.skillProficiencies[val] = "Intermediate";
    customInput.value = "";
    populateSkillSelector();
  }

  // 3. Capture structured skills with proficiency levels
  const skillsPayload = Array.from(state.userSkills).map((s) => ({
    name: s,
    level: (state.skillProficiencies && state.skillProficiencies[s]) || "Intermediate",
  }));

  // 4. Capture optional applied project and internship experience
  const projInput = document.getElementById("exp-projects-count");
  const internInput = document.getElementById("exp-internship-months");
  const projectsCount = parseInt(projInput?.value || "0", 10) || 0;
  const internshipMonths = parseInt(internInput?.value || "0", 10) || 0;
  const experiencePayload = {
    projectsCount: Math.max(0, projectsCount),
    internshipMonths: Math.max(0, internshipMonths),
  };

  // 5. Display loading indicator
  if (btn) {
    btn.disabled = true;
    btn.classList.add("opacity-80", "cursor-wait");
  }
  if (spinner) spinner.classList.remove("hidden");
  if (icon) icon.classList.add("hidden");
  if (text) text.textContent = "Analyzing Skill Gap...";
  if (errAlert) errAlert.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/skill-gap`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        roleId: roleId,
        skills: skillsPayload,
        experience: experiencePayload,
      }),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) {
      let errMsg = `Server returned ${res.status}`;
      try {
        const errJson = await res.json();
        errMsg = errJson.detail || errJson.message || errMsg;
      } catch (e) {}
      throw new Error(errMsg);
    }

    const data = await res.json();
    state.gapAnalysisResult = data;
    renderSkillGapResults(data);

    if (isUserClick) {
      showToast(`Assessment complete: ${data.analysis.matchPercentage} weighted readiness!`, "success");
    }
  } catch (err) {
    console.error("Failed to run skill gap:", err);
    const detailMsg = err.message || "Failed to communicate with Career Assessment API.";
    showToast(detailMsg, "error");

    if (errAlert && errText) {
      errText.textContent = detailMsg;
      errAlert.classList.remove("hidden");
      if (window.lucide) lucide.createIcons();
    }
    const explanation = document.getElementById("gap-explanation");
    if (explanation) {
      explanation.textContent = `Analysis could not be completed: ${detailMsg}`;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.classList.remove("opacity-80", "cursor-wait");
    }
    if (spinner) spinner.classList.add("hidden");
    if (icon) icon.classList.remove("hidden");
    if (text) text.textContent = "Run Skill-Gap Analysis";
    if (window.lucide) lucide.createIcons();
  }
}

function renderSkillGapResults(data) {
  const titleEl = document.getElementById("gap-result-title");
  const badgeEl = document.getElementById("gap-percent-badge");
  const breakdownEl = document.getElementById("gap-score-breakdown");
  const explanationEl = document.getElementById("gap-explanation");
  const matchedCountEl = document.getElementById("matched-count");
  const improvingCountEl = document.getElementById("improving-count");
  const missingCountEl = document.getElementById("missing-count");
  const matchedContainer = document.getElementById("matched-skills-list");
  const improvingContainer = document.getElementById("improving-skills-list");
  const missingContainer = document.getElementById("missing-skills-list");
  const recContainer = document.getElementById("recommendations-list");

  if (titleEl) titleEl.textContent = `${data.roleTitle} Readiness`;
  if (explanationEl) explanationEl.textContent = data.analysis.explanation;
  if (matchedCountEl) matchedCountEl.textContent = data.analysis.matchedCount;
  if (improvingCountEl) improvingCountEl.textContent = data.analysis.improvingCount || 0;
  if (missingCountEl) missingCountEl.textContent = data.analysis.missingCount;

  // Breakdown subtitle
  if (breakdownEl) {
    const expText = data.analysis.experienceBonus > 0 ? ` • +${data.analysis.experienceBonus}% Experience Bonus` : "";
    breakdownEl.textContent = `Technical Base: ${data.analysis.baseTechnicalScore}%${expText} • Weighted PostgreSQL Scoring`;
  }

  // Format percentage & dynamic badge styling
  if (badgeEl) {
    const pctNum = parseInt(data.analysis.matchPercentage.replace("%", ""), 10) || 0;
    badgeEl.textContent = `${pctNum}% Match`;
    badgeEl.className = "px-3.5 py-1.5 rounded-full text-base font-extrabold transition shadow-md";
    if (pctNum >= 80) {
      badgeEl.classList.add("bg-emerald-950", "border", "border-emerald-600", "text-emerald-300");
    } else if (pctNum >= 45) {
      badgeEl.classList.add("bg-indigo-950", "border", "border-indigo-600", "text-indigo-300");
    } else {
      badgeEl.classList.add("bg-amber-950", "border", "border-amber-700", "text-amber-300");
    }
  }

  // 1. Matched Skills
  if (matchedContainer) {
    const matchedList = data.detailedMatched || [];
    if (matchedList.length === 0) {
      matchedContainer.innerHTML = `<span class="text-xs text-slate-500 italic">No skills matched yet. Select your known skills from the checklist.</span>`;
    } else {
      matchedContainer.innerHTML = matchedList
        .map(
          (m) =>
            `<span class="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 shadow-sm">
              <i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i>
              <span>${m.name}</span>
              <span class="px-1.5 py-0.2 bg-emerald-900/90 text-emerald-200 text-[10px] rounded font-bold">${m.userLevel}</span>
            </span>`
        )
        .join("");
    }
  }

  // 2. Skills Needing Improvement
  if (improvingContainer) {
    const improvingList = data.detailedImproving || [];
    if (improvingList.length === 0) {
      improvingContainer.innerHTML = `<span class="text-xs text-slate-500 italic">None. All your matched skills meet target requirement levels!</span>`;
    } else {
      improvingContainer.innerHTML = improvingList
        .map(
          (imp) =>
            `<span class="px-2.5 py-1 rounded-lg bg-amber-950/80 border border-amber-800 text-amber-300 text-xs font-semibold flex items-center gap-1.5 shadow-sm">
              <i data-lucide="trending-up" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i>
              <span>${imp.name}</span>
              <span class="text-[10px] text-amber-200 bg-amber-900/90 px-1.5 py-0.5 rounded font-bold">${imp.userLevel} &rarr; Req: ${imp.requiredLevel}</span>
            </span>`
        )
        .join("");
    }
  }

  // 3. Missing Skills Categorized into High, Medium, Low Priority
  if (missingContainer) {
    const missingList = data.detailedMissing || [];
    if (missingList.length === 0) {
      missingContainer.innerHTML = `<span class="text-xs text-emerald-400 font-semibold flex items-center gap-1"><i data-lucide="award" class="w-4 h-4 text-emerald-400"></i> 🎉 100% Industry Benchmark! You possess all required skills!</span>`;
    } else {
      const high = missingList.filter((m) => m.priority === "High");
      const med = missingList.filter((m) => m.priority === "Medium");
      const low = missingList.filter((m) => m.priority === "Low");

      let html = "";
      if (high.length > 0) {
        html += `
          <div class="space-y-1.5">
            <div class="text-[11px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-rose-500"></span> High Priority Core Requirements (${high.length})
            </div>
            <div class="flex flex-wrap gap-1.5">
              ${high
                .map(
                  (m) =>
                    `<span class="px-2.5 py-1 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-semibold flex items-center gap-1 shadow-sm"><i data-lucide="alert-circle" class="w-3 h-3 text-rose-400 shrink-0"></i> ${m.name} <span class="text-[10px] text-rose-200 bg-rose-900/80 px-1 rounded">${m.requiredLevel}</span></span>`
                )
                .join("")}
            </div>
          </div>`;
      }
      if (med.length > 0) {
        html += `
          <div class="space-y-1.5 pt-1">
            <div class="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-amber-500"></span> Medium Priority Recommended (${med.length})
            </div>
            <div class="flex flex-wrap gap-1.5">
              ${med
                .map(
                  (m) =>
                    `<span class="px-2.5 py-1 rounded-lg bg-amber-950/60 border border-amber-800 text-amber-300 text-xs font-semibold flex items-center gap-1"><i data-lucide="alert-triangle" class="w-3 h-3 text-amber-400 shrink-0"></i> ${m.name}</span>`
                )
                .join("")}
            </div>
          </div>`;
      }
      if (low.length > 0) {
        html += `
          <div class="space-y-1.5 pt-1">
            <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-slate-500"></span> Low Priority Electives (${low.length})
            </div>
            <div class="flex flex-wrap gap-1.5">
              ${low
                .map(
                  (m) =>
                    `<span class="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-xs font-medium">${m.name}</span>`
                )
                .join("")}
            </div>
          </div>`;
      }
      missingContainer.innerHTML = html;
    }
  }

  // 4. Personalized Recommendations
  if (recContainer) {
    const recList = data.recommendations || [];
    if (recList.length === 0) {
      recContainer.innerHTML = `<span class="text-xs text-slate-500 italic">No recommendations. Ready for target career!</span>`;
    } else {
      recContainer.innerHTML = recList
        .map((r) => {
          const badgeClass =
            r.priority === "High"
              ? "bg-rose-900/80 text-rose-200 border border-rose-700"
              : r.priority === "Medium"
              ? "bg-amber-900/80 text-amber-200 border border-amber-700"
              : "bg-slate-800 text-slate-300 border border-slate-700";
          return `
            <div class="p-2.5 rounded-xl bg-slate-950/40 border border-slate-800 flex items-start justify-between gap-3">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${badgeClass}">${r.priority}</span>
                  <span class="text-xs font-bold text-white">${r.skill}</span>
                </div>
                <p class="text-xs text-slate-300">${r.action}</p>
              </div>
              <div class="text-[11px] font-semibold text-indigo-400 shrink-0 whitespace-nowrap">
                ~${r.estimatedHours} hrs
              </div>
            </div>`;
        })
        .join("");
    }
  }

  if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// Past Assessment History Modal Logic
// -------------------------------------------------------------
function toggleAssessmentHistoryModal() {
  const modal = document.getElementById("assessment-history-modal");
  if (!modal) return;
  const isHidden = modal.classList.contains("hidden");
  if (isHidden) {
    modal.classList.remove("hidden");
    loadAssessmentHistory();
  } else {
    modal.classList.add("hidden");
  }
  if (window.lucide) lucide.createIcons();
}

async function loadAssessmentHistory() {
  const container = document.getElementById("assessment-history-container");
  if (!container) return;

  if (!state.authToken) {
    container.innerHTML = `
      <div class="text-center py-8 space-y-3">
        <i data-lucide="lock" class="w-8 h-8 text-slate-500 mx-auto"></i>
        <p class="text-xs text-slate-400">Sign in to your Pathify AI student account to automatically save and revisit previous skill assessments.</p>
        <button onclick="toggleAssessmentHistoryModal(); switchTab('auth')" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition">Sign In / Register</button>
      </div>`;
    if (window.lucide) lucide.createIcons();
    return;
  }

  container.innerHTML = `<div class="text-center py-8 text-xs text-slate-400 flex items-center justify-center gap-2"><div class="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div> Loading past assessments...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/skill-gap/history`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });
    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    if (!res.ok) throw new Error("Could not fetch assessment history");
    const data = await res.json();

    if (!data.assessments || data.assessments.length === 0) {
      container.innerHTML = `<div class="text-center py-8 text-xs text-slate-500">No previous assessments found for your account. Run your first assessment on the left!</div>`;
      return;
    }

    container.innerHTML = data.assessments
      .map((item) => {
        const date = new Date(item.createdAt).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
        return `
          <div class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition flex items-center justify-between gap-3">
            <div>
              <div class="flex items-center gap-2">
                <h4 class="text-sm font-bold text-white">${item.roleTitle}</h4>
                <span class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-indigo-950 border border-indigo-700 text-indigo-300">${item.matchPercentage}</span>
              </div>
              <div class="text-[11px] text-slate-400 mt-1 flex flex-wrap items-center gap-2.5">
                <span>${date}</span>
                <span class="text-emerald-400">✓ ${item.matchedCount} Matched</span>
                <span class="text-amber-400">▲ ${item.improvingCount} Level-Up</span>
                <span class="text-rose-400">✕ ${item.missingCount} Missing</span>
              </div>
            </div>
            <button onclick="revisitAssessment('${item.id}', '${item.roleId}')" class="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shrink-0 transition shadow-sm">
              View
            </button>
          </div>`;
      })
      .join("");

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="text-center py-8 text-xs text-rose-400">Failed to load history: ${err.message}</div>`;
  }
}

async function revisitAssessment(assessmentId, roleId) {
  try {
    const res = await fetch(`${API_BASE}/api/skill-gap/assessments/${assessmentId}`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });
    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    if (!res.ok) throw new Error("Failed to load assessment breakdown");
    const data = await res.json();

    state.selectedRoleId = data.roleId || roleId;
    syncRoleDropdowns(state.selectedRoleId);
    state.gapAnalysisResult = data;
    renderSkillGapResults(data);
    toggleAssessmentHistoryModal();
    showToast(`Loaded assessment for ${data.roleTitle} (${data.analysis.matchPercentage})`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -------------------------------------------------------------
// Roadmap Generation & Fetching Logic
// -------------------------------------------------------------
async function loadRoadmap(forceRefresh = false) {
  const currentRole = state.selectedRoleId;
  syncRoleDropdowns(currentRole);

  const cachedRoleId = state.roadmapData?.targetRoleId || state.roadmapData?.roleId;
  if (state.roadmapData && cachedRoleId === currentRole && !forceRefresh) {
    renderRoadmapView();
    return;
  }

  const container = document.getElementById("roadmap-steps-container");
  if (container) {
    container.innerHTML = `
      <div class="p-8 text-center bg-slate-900 border border-slate-800 rounded-2xl text-slate-400 flex items-center justify-center gap-3">
        <div class="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
        <span>Loading learning roadmap from database...</span>
      </div>`;
  }

  try {
    // 1. Ensure profile exists in backend for current user and selected target role
    const profilePayload = {
      name: state.currentUser?.full_name || "Student",
      education: state.currentUser?.education || "Computer Science",
      skills: Array.from(state.userSkills),
      targetRoleId: state.selectedRoleId,
    };
    if (state.savedProfileId) {
      profilePayload.profileId = state.savedProfileId;
    }

    const pRes = await fetch(`${API_BASE}/api/profiles`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(profilePayload),
    });
    if (pRes.status === 401) {
      handleUnauthorized();
      return;
    }
    if (pRes.ok) {
      const pData = await pRes.json();
      if (pData?.profile?.id) {
        state.savedProfileId = pData.profile.id;
        try {
          localStorage.setItem("pathify_profile_id", pData.profile.id);
        } catch (_) {}
      }
    }

    // 2. Fetch roadmap for profile and selected target role from backend API
    const roadmapUrl = state.savedProfileId
      ? `${API_BASE}/api/profiles/${state.savedProfileId}/roadmap?roleId=${encodeURIComponent(state.selectedRoleId)}`
      : `${API_BASE}/api/profiles/me/roadmap?roleId=${encodeURIComponent(state.selectedRoleId)}`;

    const rRes = await fetch(roadmapUrl, {
      credentials: "include",
      headers: getAuthHeaders(),
    });
    if (rRes.status === 401) {
      handleUnauthorized();
      return;
    }
    if (rRes.ok) {
      const rData = await rRes.json();
      state.roadmapData = rData;
      renderRoadmapView();
      return;
    }
  } catch (err) {
    console.warn("Backend roadmap API unavailable, using fallback:", err);
  }

  // Fallback to local computation if backend is unreachable
  fallbackGenerateRoadmap();
}

function fallbackGenerateRoadmap() {
  const role = state.roles.find((r) => r.id === state.selectedRoleId);
  const userSkillSet = new Set(Array.from(state.userSkills).map((s) => s.toLowerCase().trim()));
  const required = role ? role.requiredSkills : [];
  const missing = required.filter((s) => !userSkillSet.has(s.toLowerCase().trim()));
  const acquiredCount = required.length - missing.length;

  const steps = missing.map((skillName, idx) => ({
    stepNumber: idx + 1,
    skill: skillName,
    learningGoal: `Master core principles, syntax, and industry best practices for ${skillName}.`,
    practiceTask: `Build a practical hands-on project or component demonstrating proficiency in ${skillName}.`,
    estimatedDuration: "1-2 weeks",
    completed: false,
  }));

  state.roadmapData = {
    targetRoleTitle: role ? role.title : "Career Path",
    summary: {
      totalRequiredSkills: required.length,
      acquiredSkillsCount: acquiredCount,
      missingSkillsCount: missing.length,
      totalRoadmapSteps: steps.length,
    },
    roadmap: steps,
  };

  renderRoadmapView();
}

async function generateRoadmapFromGap() {
  state.roadmapData = null;
  syncRoleDropdowns(state.selectedRoleId);
  switchTab("roadmap");
}

function renderRoadmapView() {
  if (!state.roadmapData) return;
  const data = state.roadmapData;

  const roleTitle = data.targetRoleTitle || data.roleTitle || "Target Career";
  const summary = data.summary || {
    totalRequiredSkills: data.totalRequiredSkills || 0,
    acquiredSkillsCount: data.acquiredSkillsCount || 0,
    missingSkillsCount: data.missingSkillsCount || 0,
  };
  const steps = data.roadmap || data.steps || [];

  const totalMilestones = steps.length;
  const completedMilestones = steps.filter((s) => s.completed).length;
  const missingSteps = Math.max(0, totalMilestones - completedMilestones);
  const pct = totalMilestones > 0 ? Math.round((completedMilestones / totalMilestones) * 100) : 100;

  document.getElementById("roadmap-heading").textContent = `Roadmap: ${roleTitle}`;
  document.getElementById("roadmap-subheading").textContent = `Targeted step-by-step milestones to bridge your ${missingSteps} skill deficits.`;

  document.getElementById("rm-stat-total").textContent = summary.totalRequiredSkills;
  document.getElementById("rm-stat-acquired").textContent = summary.acquiredSkillsCount;
  document.getElementById("rm-stat-missing").textContent = missingSteps;
  document.getElementById("rm-stat-completed").textContent = `${pct}%`;

  const container = document.getElementById("roadmap-steps-container");
  if (steps.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center bg-slate-900 border border-slate-800 rounded-2xl space-y-3">
        <i data-lucide="award" class="w-12 h-12 text-emerald-400 mx-auto"></i>
        <h3 class="text-xl font-bold text-white">Full Proficiency Achieved!</h3>
        <p class="text-slate-400 text-sm">You already have all required skills for ${roleTitle}. Explore another role or practice mock interviews!</p>
      </div>`;
  } else {
    container.innerHTML = steps
      .map((step, idx) => {
        return `
      <div class="bg-slate-900/80 border ${step.completed ? "border-emerald-700/60 bg-emerald-950/20" : "border-slate-800 hover:border-slate-700"} rounded-2xl p-6 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl ${step.completed ? "bg-emerald-600 text-white" : "bg-indigo-600/20 border border-indigo-500/40 text-indigo-400"} flex items-center justify-center font-bold text-base shrink-0">
            ${step.completed ? `<i data-lucide="check" class="w-5 h-5"></i>` : step.stepNumber}
          </div>
          <div class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs px-2.5 py-0.5 rounded-full font-bold ${step.completed ? "bg-emerald-900/60 text-emerald-300" : "bg-indigo-950 text-indigo-300 border border-indigo-800/50"}">
                ${step.skill}
              </span>
              ${step.priority ? `<span class="text-[10px] px-2 py-0.5 rounded font-extrabold ${step.priority === "High" ? "bg-rose-950 text-rose-300 border border-rose-800" : (step.priority === "Medium" ? "bg-amber-950 text-amber-300 border border-amber-800" : "bg-slate-800 text-slate-300 border border-slate-700")}">${step.priority} Priority</span>` : ""}
              <span class="text-xs text-slate-400 flex items-center gap-1">
                <i data-lucide="clock" class="w-3.5 h-3.5"></i> ${step.estimatedDuration}
              </span>
            </div>
            <div class="text-sm font-semibold text-white pt-1">${step.learningGoal}</div>
            <div class="text-xs text-slate-400 flex items-center gap-1.5 pt-0.5">
              <i data-lucide="code" class="w-3.5 h-3.5 text-cyan-400"></i>
              <span><strong>Practical Task:</strong> ${step.practiceTask}</span>
            </div>
          </div>
        </div>

        <div class="shrink-0 self-end sm:self-center">
          <button onclick="toggleStepCompletion(${idx})" class="px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
            step.completed
              ? "bg-emerald-900/40 text-emerald-400 border border-emerald-800"
              : "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
          }">
            <i data-lucide="${step.completed ? "check-circle-2" : "circle"}" class="w-4 h-4"></i>
            <span>${step.completed ? "Completed" : "Mark Done"}</span>
          </button>
        </div>
      </div>`;
      })
      .join("");
  }

  if (window.lucide) lucide.createIcons();
}

async function toggleStepCompletion(stepIdx) {
  if (!state.roadmapData) return;
  const steps = state.roadmapData.roadmap || state.roadmapData.steps;
  if (!steps || !steps[stepIdx]) return;

  const currentStep = steps[stepIdx];
  // Optimistically toggle completion status and immediately recompute summary statistics
  currentStep.completed = !currentStep.completed;
  renderRoadmapView();

  const isCompleted = currentStep.completed;
  showToast(
    isCompleted ? "Milestone completed! Great work." : "Milestone marked pending.",
    isCompleted ? "success" : "info"
  );

  // Persist milestone status to PostgreSQL backend
  try {
    const toggleUrl = state.savedProfileId
      ? `${API_BASE}/api/profiles/${state.savedProfileId}/roadmap/toggle-step`
      : `${API_BASE}/api/profiles/me/roadmap/toggle-step`;

    const res = await fetch(toggleUrl, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        roleId: state.selectedRoleId,
        stepNumber: currentStep.stepNumber || stepIdx + 1,
        completed: isCompleted,
      }),
    });
    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    if (res.ok) {
      const updatedData = await res.json();
      if (updatedData && updatedData.roadmap) {
        state.roadmapData = updatedData;
        renderRoadmapView();
      }
    }
  } catch (err) {
    console.warn("Could not persist milestone toggle to backend:", err);
  }
}

// -------------------------------------------------------------
// Save Student Profile (Database persistence)
// -------------------------------------------------------------
function openSaveProfileModal() {
  if (state.currentUser && state.currentUser.full_name) {
    const nameInput = document.getElementById("modal-name");
    if (nameInput) nameInput.value = state.currentUser.full_name;
  }
  document.getElementById("profile-modal").classList.remove("hidden");
}

function closeSaveProfileModal() {
  document.getElementById("profile-modal").classList.add("hidden");
}

async function confirmSaveProfile() {
  const name = document.getElementById("modal-name").value.trim() || (state.currentUser?.full_name || "Student");
  const edu = document.getElementById("modal-edu").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/profiles`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        name: name,
        education: edu,
        skills: Array.from(state.userSkills),
        targetRoleId: state.selectedRoleId,
      }),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (data?.profile?.id) {
      state.savedProfileId = data.profile.id;
    }
    state.roadmapData = null;
    closeSaveProfileModal();
    showToast(`Profile saved in PostgreSQL! ID: ${data.profile.id.slice(0, 8)}...`, "success");
    loadRoadmap();
  } catch (err) {
    console.error("Save profile error", err);
    showToast("Failed to save profile to database.", "error");
  }
}

// -------------------------------------------------------------
// AI Career Chatbot Logic
// -------------------------------------------------------------
async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendChatMessage("user", msg);

  // Disable send button while answering
  const btn = document.getElementById("chat-send-btn");
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        message: msg,
        history: state.chatHistory,
        contextRoleId: state.selectedRoleId,
      }),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    appendChatMessage("assistant", data.reply, data.suggestedQuestions);

    if (data.modelName) {
      document.getElementById("chat-mode-label").textContent = data.modelName;
    }

    state.chatHistory.push({ role: "user", content: msg });
    state.chatHistory.push({ role: "assistant", content: data.reply });
  } catch (err) {
    console.error("Chat error", err);
    appendChatMessage(
      "assistant",
      "I am currently experiencing a connection hiccup with the advisor service. Please try asking again in a moment."
    );
  } finally {
    btn.disabled = false;
  }
}

function sendQuickPrompt(promptText) {
  document.getElementById("chat-input").value = promptText;
  document.getElementById("chat-send-btn").click();
}

function appendChatMessage(role, text, suggestions = []) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  // Simple Markdown formatting parser (bold, bullet points)
  let formattedText = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n- /g, "<br>&bull; ")
    .replace(/\n1\. /g, "<br>1. ");

  const isUser = role === "user";

  const msgDiv = document.createElement("div");
  msgDiv.className = `flex items-start gap-3 ${isUser ? "justify-end" : "max-w-2xl"}`;

  if (isUser) {
    msgDiv.innerHTML = `
      <div class="bg-indigo-600 text-white rounded-2xl rounded-tr-none p-4 text-sm leading-relaxed shadow-md">
        ${text}
      </div>
      <div class="w-8 h-8 rounded-lg bg-indigo-900 border border-indigo-700 flex items-center justify-center text-indigo-300 shrink-0">
        <i data-lucide="user" class="w-4 h-4"></i>
      </div>`;
  } else {
    let suggestionsHtml = "";
    if (suggestions && suggestions.length > 0) {
      suggestionsHtml = `
        <div class="mt-3 pt-3 border-t border-slate-700/60 flex flex-wrap gap-1.5">
          ${suggestions
            .map(
              (s) =>
                `<button onclick="sendQuickPrompt('${s}')" class="text-xs px-2.5 py-1 rounded-lg bg-slate-700/80 hover:bg-slate-600 text-indigo-300 transition text-left">${s}</button>`
            )
            .join("")}
        </div>`;
    }

    msgDiv.innerHTML = `
      <div class="w-8 h-8 rounded-lg bg-cyan-600 flex items-center justify-center shrink-0">
        <i data-lucide="bot" class="w-4 h-4 text-white"></i>
      </div>
      <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl rounded-tl-none p-4 text-sm text-slate-200 leading-relaxed shadow-sm">
        <div>${formattedText}</div>
        ${suggestionsHtml}
      </div>`;
  }

  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;

  if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// Toast Notifications
// -------------------------------------------------------------
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  const msg = document.getElementById("toast-msg");
  if (!toast || !msg) return;

  msg.textContent = message;
  toast.classList.remove("translate-y-20", "opacity-0");

  setTimeout(() => {
    toast.classList.add("translate-y-20", "opacity-0");
  }, 3500);
}

// -------------------------------------------------------------
// Authentication System Logic
// -------------------------------------------------------------

function openAuthView(mode = "login") {
  const tabs = ["dashboard", "careers", "skillgap", "roadmap", "chat", "auth"];
  tabs.forEach((tab) => {
    const viewEl = document.getElementById(`view-${tab}`);
    const navBtn = document.getElementById(`nav-${tab}`);
    if (viewEl) {
      if (tab === "auth") {
        viewEl.classList.remove("hidden");
      } else {
        viewEl.classList.add("hidden");
      }
    }
    if (navBtn) {
      navBtn.className = "nav-btn px-3 py-2 text-sm font-medium rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 flex items-center gap-1.5 transition";
    }
  });
  setAuthMode(mode);
  if (typeof window !== "undefined" && window.location) {
    const targetUrl = getAuthUrl(mode);
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", targetUrl);
    }
  }
  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 30);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setAuthMode(mode) {
  state.authMode = mode;
  clearAuthAlert();

  const tabLogin = document.getElementById("auth-tab-btn-login");
  const tabRegister = document.getElementById("auth-tab-btn-register");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");
  const formForgot = document.getElementById("form-forgot");
  const title = document.getElementById("auth-heading-title");
  const desc = document.getElementById("auth-heading-desc");
  const promptText = document.getElementById("auth-switch-prompt-text");
  const promptBtn = document.getElementById("auth-switch-prompt-btn");

  if (mode === "login") {
    if (tabLogin) tabLogin.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 bg-indigo-600 text-white shadow-md shadow-indigo-600/30";
    if (tabRegister) tabRegister.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    if (formLogin) formLogin.classList.remove("hidden");
    if (formRegister) formRegister.classList.add("hidden");
    if (formForgot) formForgot.classList.add("hidden");
    if (title) title.textContent = "Welcome back";
    if (desc) desc.textContent = "Sign in with your email and password to access your career roadmaps and saved skill assessments.";
    if (promptText) promptText.textContent = "Don't have an account?";
    if (promptBtn) promptBtn.textContent = "Create an account →";
    requestBrowserAutofill();
  } else if (mode === "register") {
    if (tabRegister) tabRegister.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-600/30";
    if (tabLogin) tabLogin.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    if (formLogin) formLogin.classList.add("hidden");
    if (formRegister) formRegister.classList.remove("hidden");
    if (formForgot) formForgot.classList.add("hidden");
    if (title) title.textContent = "Create Student Account";
    if (desc) desc.textContent = "Sign up to track your skill gaps, generate custom career roadmaps, and chat with your AI mentor.";
    if (promptText) promptText.textContent = "Already have an account?";
    if (promptBtn) promptBtn.textContent = "Sign In →";
  } else if (mode === "forgot") {
    if (tabLogin) tabLogin.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    if (tabRegister) tabRegister.className = "flex-1 py-2.5 text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    if (formLogin) formLogin.classList.add("hidden");
    if (formRegister) formRegister.classList.add("hidden");
    if (formForgot) formForgot.classList.remove("hidden");
    if (title) title.textContent = "Recover Your Password";
    if (desc) desc.textContent = "Enter your registered email address and we will dispatch a single-use 20-minute reset link via Resend.";
    if (promptText) promptText.textContent = "Remembered your credentials?";
    if (promptBtn) promptBtn.textContent = "Sign In →";
  }

  if (typeof window !== "undefined" && window.location && window.history && window.history.replaceState) {
    const targetUrl = getAuthUrl(mode);
    window.history.replaceState(null, "", targetUrl);
  }

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 30);
  }
}

function toggleAuthMode() {
  if (state.authMode === "login") {
    setAuthMode("register");
  } else {
    setAuthMode("login");
  }
}

async function handleForgotPasswordSubmit(e) {
  e.preventDefault();
  clearAuthAlert();

  const emailInput = document.getElementById("forgot-email");
  const email = emailInput ? emailInput.value.trim() : "";
  const btn = document.getElementById("forgot-submit-btn");
  const spinner = document.getElementById("forgot-btn-spinner");
  const icon = document.getElementById("forgot-btn-icon");
  const text = document.getElementById("forgot-btn-text");

  if (!email) {
    showAuthAlert("Please provide your registered email address.");
    return;
  }

  btn.disabled = true;
  if (spinner) spinner.classList.remove("hidden");
  if (icon) icon.classList.add("hidden");
  if (text) text.textContent = "Dispatching Reset Link...";

  try {
    const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to send password reset email.");
    }

    showAuthAlert(
      data.message || "A real password reset link has been dispatched to your email! Please check your inbox (valid for 20 minutes).",
      "success"
    );
    if (emailInput) emailInput.value = "";
  } catch (err) {
    console.error("Forgot password error:", err);
    const msg = (err.name === "TypeError" && err.message.includes("fetch"))
      ? `Cannot reach backend API at ${API_BASE}. Please ensure FastAPI is running on port 5000.`
      : (err.message || "Failed to dispatch reset email. Please verify the email or try again later.");
    showAuthAlert(msg, "error");
  } finally {
    btn.disabled = false;
    if (spinner) spinner.classList.add("hidden");
    if (icon) icon.classList.remove("hidden");
    if (text) text.textContent = "Send Password Reset Link";
    if (window.lucide) lucide.createIcons();
  }
}

function togglePasswordVisibility(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (!input || !icon) return;

  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";
  icon.setAttribute("data-lucide", isPassword ? "eye-off" : "eye");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function validatePasswordMatch() {
  const pwdInput = document.getElementById("register-password");
  const confirmInput = document.getElementById("register-confirm-password");
  const hint = document.getElementById("pwd-match-hint");
  const hintText = document.getElementById("pwd-match-hint-text");
  if (!pwdInput || !confirmInput || !hint) return;

  const pwd = pwdInput.value;
  const confirm = confirmInput.value;

  if (confirm.length === 0) {
    hint.classList.add("hidden");
    confirmInput.classList.remove("auth-input-valid", "auth-input-invalid");
    return;
  }

  hint.classList.remove("hidden");
  if (pwd === confirm) {
    hint.className = "text-[11px] text-emerald-400 mt-1 flex items-center gap-1";
    hintText.textContent = "Passwords match perfectly";
    confirmInput.classList.add("auth-input-valid");
    confirmInput.classList.remove("auth-input-invalid");
  } else {
    hint.className = "text-[11px] text-rose-400 mt-1 flex items-center gap-1";
    hintText.textContent = "Passwords do not match yet";
    confirmInput.classList.add("auth-input-invalid");
    confirmInput.classList.remove("auth-input-valid");
  }

  if (window.lucide) lucide.createIcons();
}

function showAuthAlert(message, type = "error") {
  const alert = document.getElementById("auth-alert");
  const alertText = document.getElementById("auth-alert-text");
  const alertIcon = document.getElementById("auth-alert-icon");
  if (!alert || !alertText) return;

  alertText.textContent = message;
  alert.classList.remove("hidden");

  if (type === "success") {
    alert.className = "mb-6 p-3.5 rounded-xl text-xs font-medium border flex items-start gap-2.5 bg-emerald-950/80 border-emerald-800 text-emerald-300";
    if (alertIcon) alertIcon.setAttribute("data-lucide", "check-circle");
  } else {
    alert.className = "mb-6 p-3.5 rounded-xl text-xs font-medium border flex items-start gap-2.5 bg-rose-950/80 border-rose-800 text-rose-300";
    if (alertIcon) alertIcon.setAttribute("data-lucide", "alert-circle");
  }

  if (window.lucide) lucide.createIcons();
}

function clearAuthAlert() {
  const alert = document.getElementById("auth-alert");
  if (alert) alert.classList.add("hidden");
}

// -------------------------------------------------------------
// Chrome Password Manager & Credential Management API Helpers
// -------------------------------------------------------------
function storeBrowserCredentials(formId) {
  if (typeof window === "undefined" || !window.PasswordCredential || !navigator.credentials || !navigator.credentials.store) {
    return;
  }
  try {
    const formEl = document.getElementById(formId);
    if (formEl) {
      const cred = new PasswordCredential(formEl);
      navigator.credentials.store(cred).catch((err) => {
        console.debug("PasswordCredential store notification:", err);
      });
    }
  } catch (err) {
    console.debug("PasswordCredential could not be constructed:", err);
  }
}

async function requestBrowserAutofill() {
  if (typeof window === "undefined" || !navigator.credentials || !navigator.credentials.get) {
    return;
  }
  try {
    const cred = await navigator.credentials.get({
      password: true,
      mediation: "optional",
    });
    if (cred && cred.id) {
      const emailEl = document.getElementById("login-email");
      const pwdEl = document.getElementById("login-password");
      if (emailEl && !emailEl.value) {
        emailEl.value = cred.id;
      }
      if (pwdEl && cred.password && !pwdEl.value) {
        pwdEl.value = cred.password;
      }
    }
  } catch (err) {
    console.debug("Browser autofill query:", err);
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  clearAuthAlert();

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const btn = document.getElementById("login-submit-btn");
  const spinner = document.getElementById("login-btn-spinner");
  const icon = document.getElementById("login-btn-icon");
  const text = document.getElementById("login-btn-text");

  if (!email || !password) {
    showAuthAlert("Please provide both email and password.");
    return;
  }

  btn.disabled = true;
  if (spinner) spinner.classList.remove("hidden");
  if (icon) icon.classList.add("hidden");
  if (text) text.textContent = "Authenticating...";

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Invalid email or password");
    }

    // Reset previous account state before attaching authenticated user
    resetApplicationState();

    // Success: save token and user state
    localStorage.setItem("pathify_token", data.access_token);
    state.authToken = data.access_token;
    state.currentUser = data.user;

    // Trigger Chrome Password Manager prompt via Credential Management API
    storeBrowserCredentials("form-login");

    updateNavAuthUI();
    showToast(`Welcome back, ${data.user.full_name || data.user.email}!`, "success");

    // Defer clearing login input so Chrome's password manager captures the credentials
    setTimeout(() => {
      const pwdInput = document.getElementById("login-password");
      if (pwdInput) pwdInput.value = "";
    }, 1000);

    await loadRoles();
    await loadUserProfile();
    if (typeof loadResumeHistory === "function") {
      await loadResumeHistory();
    }

    // Redirect user to their originally requested tab or dashboard
    const targetTab = state.redirectAfterLogin || "dashboard";
    state.redirectAfterLogin = null;
    switchTab(targetTab);
  } catch (err) {
    console.error("Login error:", err);
    const msg = (err.name === "TypeError" && err.message.includes("fetch"))
      ? `Cannot reach backend API at ${API_BASE}. Please ensure FastAPI is running on port 8000 or 5000.`
      : (err.message || "Failed to sign in. Please verify your credentials.");
    showAuthAlert(msg);
  } finally {
    btn.disabled = false;
    if (spinner) spinner.classList.add("hidden");
    if (icon) icon.classList.remove("hidden");
    if (text) text.textContent = "Sign In to Pathify AI";
    if (window.lucide) lucide.createIcons();
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  clearAuthAlert();

  const nameInput = document.getElementById("register-name") || document.getElementById("register-fullname");
  const fullName = nameInput ? nameInput.value.trim() : "";
  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;
  const confirmPassword = document.getElementById("register-confirm-password").value;

  if (password.length < 6) {
    showAuthAlert("Password must be at least 6 characters in length.");
    return;
  }

  if (password !== confirmPassword) {
    showAuthAlert("Passwords do not match. Please re-enter.");
    return;
  }

  const btn = document.getElementById("register-submit-btn");
  const spinner = document.getElementById("register-btn-spinner");
  const icon = document.getElementById("register-btn-icon");
  const text = document.getElementById("register-btn-text");

  btn.disabled = true;
  if (spinner) spinner.classList.remove("hidden");
  if (icon) icon.classList.add("hidden");
  if (text) text.textContent = "Creating Account...";

  try {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        email: email,
        password: password,
        confirm_password: confirmPassword,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Registration failed");
    }

    // Reset any previous session data before initializing new account
    resetApplicationState();

    // Success: auto-login with token
    localStorage.setItem("pathify_token", data.access_token);
    state.authToken = data.access_token;
    state.currentUser = data.user;

    // Trigger Chrome Password Manager prompt to save the new credentials
    storeBrowserCredentials("form-register");

    updateNavAuthUI();
    showToast(`Account created! Welcome to Pathify-AI, ${data.user.full_name}!`, "success");

    // Defer clearing register inputs so Chrome Password Manager captures the submission
    setTimeout(() => {
      const p1 = document.getElementById("register-password");
      const p2 = document.getElementById("register-confirm-password");
      if (p1) p1.value = "";
      if (p2) p2.value = "";
    }, 1000);

    await loadRoles();
    if (typeof populateSkillSelector === "function") {
      populateSkillSelector();
    }

    // Redirect user to their originally requested tab or dashboard
    const targetTab = state.redirectAfterLogin || "dashboard";
    state.redirectAfterLogin = null;
    switchTab(targetTab);
  } catch (err) {
    console.error("Registration error:", err);
    const msg = (err.name === "TypeError" && err.message.includes("fetch"))
      ? `Cannot reach backend API at ${API_BASE}. Please ensure FastAPI is running on port 8000 or 5000.`
      : (err.message || "Failed to create account. Email may already be in use.");
    showAuthAlert(msg);
  } finally {
    btn.disabled = false;
    if (spinner) spinner.classList.add("hidden");
    if (icon) icon.classList.remove("hidden");
    if (text) text.textContent = "Create Student Account";
    if (window.lucide) lucide.createIcons();
  }
}

function updateNavAuthUI() {
  const loggedOutGroup = document.getElementById("auth-nav-logged-out");
  const loggedInGroup = document.getElementById("auth-nav-logged-in");
  const userNameEl = document.getElementById("auth-user-name");
  const userAvatarEl = document.getElementById("auth-user-avatar");
  const userRoleEl = document.getElementById("auth-user-role");
  const mobileAuthText = document.getElementById("mobile-auth-text");
  const protectedDesktopNav = document.getElementById("protected-nav-links");
  const protectedMobileNav = document.getElementById("mobile-protected-links");
  const authBackNav = document.getElementById("auth-back-nav");

  if (state.currentUser && state.authToken) {
    if (loggedOutGroup) loggedOutGroup.classList.add("hidden");
    if (loggedInGroup) loggedInGroup.classList.remove("hidden");
    if (protectedDesktopNav) protectedDesktopNav.classList.remove("hidden");
    if (protectedMobileNav) protectedMobileNav.classList.remove("hidden");
    if (authBackNav) {
      authBackNav.classList.remove("hidden");
      authBackNav.classList.add("flex");
    }

    const displayName = state.currentUser.full_name || state.currentUser.email.split("@")[0];
    if (userNameEl) userNameEl.textContent = displayName;
    if (userRoleEl) userRoleEl.textContent = state.currentUser.role || "Student";

    // Set initials in avatar
    if (userAvatarEl) {
      const parts = displayName.split(" ");
      const initials = parts.length > 1
        ? (parts[0][0] + parts[1][0]).toUpperCase()
        : displayName.slice(0, 2).toUpperCase();
      userAvatarEl.textContent = initials;
    }

    if (mobileAuthText) mobileAuthText.textContent = displayName.split(" ")[0];
  } else {
    if (loggedOutGroup) loggedOutGroup.classList.remove("hidden");
    if (loggedInGroup) loggedInGroup.classList.add("hidden");
    if (protectedDesktopNav) protectedDesktopNav.classList.add("hidden");
    if (protectedMobileNav) protectedMobileNav.classList.add("hidden");
    if (authBackNav) {
      authBackNav.classList.add("hidden");
      authBackNav.classList.remove("flex");
    }
    if (mobileAuthText) mobileAuthText.textContent = "Sign In";
  }

  if (window.lucide) {
    lucide.createIcons();
  }
}

async function restoreUserSession() {
  if (!state.authToken) {
    resetApplicationState();
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.ok) {
      const data = await res.json();
      state.currentUser = data.user;
      updateNavAuthUI();
      console.log("Restored user session:", data.user.email);
      await loadRoles();
      await loadUserProfile();
      if (typeof loadResumeHistory === "function") {
        await loadResumeHistory();
      }
    } else {
      // Token expired or invalid
      console.warn("Session token expired or invalid, clearing local session.");
      resetApplicationState();
    }
  } catch (err) {
    console.warn("Could not reach auth verify endpoint, clearing unverified session.", err);
    resetApplicationState();
  }
}

async function logoutUser() {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders(),
    });
  } catch (err) {
    console.warn("Logout request failed:", err);
  }

  resetApplicationState();
  showToast("You have been signed out.", "info");

  openAuthView("login");
}
