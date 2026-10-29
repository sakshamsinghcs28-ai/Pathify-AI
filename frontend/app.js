/**
 * Pathify-AI Frontend Application Logic
 */

// Application State
const state = {
  roles: [],
  selectedRoleId: "role-1",
  userSkills: new Set(["HTML & CSS", "JavaScript"]),
  gapAnalysisResult: null,
  roadmapData: null,
  chatHistory: [],
  savedProfileId: null,
};

// API Base URL
const API_BASE = "http://127.0.0.1:8000";

// Initialize application on load
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  await checkHealth();
  await loadRoles();
});

// -------------------------------------------------------------
// Navigation Tabs
// -------------------------------------------------------------
function switchTab(tabName) {
  const tabs = ["dashboard", "careers", "skillgap", "roadmap", "chat"];
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

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }

  // Action hook on tab enter
  if (tabName === "skillgap") {
    populateSkillSelector();
    runSkillGapAnalysis();
  } else if (tabName === "roadmap") {
    loadRoadmap();
  }
}

// -------------------------------------------------------------
// Health Check
// -------------------------------------------------------------
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      document.getElementById("health-badge").className =
        "flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/80 border border-emerald-800/60 text-emerald-400";
      document.getElementById("health-text").textContent = "PostgreSQL Online";
    }
  } catch (err) {
    document.getElementById("health-badge").className =
      "flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/80 border border-rose-800/60 text-rose-400";
    document.getElementById("health-text").textContent = "API Disconnected";
  }
}

// -------------------------------------------------------------
// Load Roles from Backend
// -------------------------------------------------------------
async function loadRoles() {
  try {
    const res = await fetch(`${API_BASE}/api/roles`);
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

function populateRoleDropdown(roles) {
  const select = document.getElementById("gap-role-select");
  if (!select) return;
  select.innerHTML = roles
    .map((r) => `<option value="${r.id}" ${r.id === state.selectedRoleId ? "selected" : ""}>${r.title} (${r.category})</option>`)
    .join("");
}

function selectAndAnalyzeRole(roleId) {
  state.selectedRoleId = roleId;
  state.savedProfileId = null;
  state.roadmapData = null;
  const select = document.getElementById("gap-role-select");
  if (select) select.value = roleId;
  switchTab("skillgap");
}

function onRoleSelectionChanged() {
  const select = document.getElementById("gap-role-select");
  state.selectedRoleId = select.value;
  state.savedProfileId = null;
  state.roadmapData = null;
  populateSkillSelector();
  runSkillGapAnalysis();
}

// -------------------------------------------------------------
// Skill Gap Analyzer Logic
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
      return `
      <button type="button" onclick="toggleSkill('${skill}')" class="px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
        active
          ? "bg-emerald-600 text-white border border-emerald-500 shadow-sm"
          : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700"
      }">
        <i data-lucide="${active ? "check" : "plus"}" class="w-3.5 h-3.5"></i>
        <span>${skill}</span>
      </button>`;
    })
    .join("");

  if (window.lucide) lucide.createIcons();
}

function toggleSkill(skillName) {
  if (state.userSkills.has(skillName)) {
    state.userSkills.delete(skillName);
  } else {
    state.userSkills.add(skillName);
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
  state.savedProfileId = null;
  state.roadmapData = null;
  input.value = "";
  populateSkillSelector();
  runSkillGapAnalysis();
  showToast(`Added '${val}' to your skills.`, "success");
}

async function runSkillGapAnalysis() {
  const roleId = state.selectedRoleId;
  const skillsList = Array.from(state.userSkills);

  try {
    const res = await fetch(`${API_BASE}/api/skill-gap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        roleId: roleId,
        skills: skillsList,
      }),
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();
    state.gapAnalysisResult = data;
    renderSkillGapResults(data);
  } catch (err) {
    console.error("Failed to run skill gap", err);
    showToast("Error running skill gap analysis.", "error");
  }
}

function renderSkillGapResults(data) {
  document.getElementById("gap-result-title").textContent = `${data.roleTitle} Readiness`;
  document.getElementById("gap-percent-badge").textContent = data.analysis.matchPercentage;
  document.getElementById("gap-explanation").textContent = data.analysis.explanation;

  document.getElementById("matched-count").textContent = data.analysis.matchedCount;
  document.getElementById("missing-count").textContent = data.analysis.missingCount;

  const matchedContainer = document.getElementById("matched-skills-list");
  if (data.matchedSkills.length === 0) {
    matchedContainer.innerHTML = `<span class="text-xs text-slate-500 italic">No skills matched yet. Select skills from the checklist.</span>`;
  } else {
    matchedContainer.innerHTML = data.matchedSkills
      .map(
        (s) =>
          `<span class="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs font-semibold flex items-center gap-1"><i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> ${s}</span>`
      )
      .join("");
  }

  const missingContainer = document.getElementById("missing-skills-list");
  if (data.missingSkills.length === 0) {
    missingContainer.innerHTML = `<span class="text-xs text-emerald-400 font-semibold">🎉 100% Match! You possess all core requirements!</span>`;
  } else {
    missingContainer.innerHTML = data.missingSkills
      .map(
        (s) =>
          `<span class="px-2.5 py-1 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-semibold flex items-center gap-1"><i data-lucide="alert-circle" class="w-3 h-3 text-rose-400"></i> ${s}</span>`
      )
      .join("");
  }

  if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------
// Roadmap Generation & Fetching Logic
// -------------------------------------------------------------
async function loadRoadmap() {
  if (state.roadmapData) {
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
    // 1. Ensure profile exists in backend
    if (!state.savedProfileId) {
      const pRes = await fetch(`${API_BASE}/api/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Demo Student",
          education: "Computer Science",
          skills: Array.from(state.userSkills),
          targetRoleId: state.selectedRoleId,
        }),
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        if (pData?.profile?.id) {
          state.savedProfileId = pData.profile.id;
        }
      }
    }

    // 2. Fetch roadmap for profile from backend API
    if (state.savedProfileId) {
      const rRes = await fetch(`${API_BASE}/api/profiles/${state.savedProfileId}/roadmap`);
      if (rRes.ok) {
        const rData = await rRes.json();
        state.roadmapData = rData;
        renderRoadmapView();
        return;
      }
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

  document.getElementById("roadmap-heading").textContent = `Roadmap: ${roleTitle}`;
  document.getElementById("roadmap-subheading").textContent = `Targeted step-by-step milestones to bridge your ${summary.missingSkillsCount} skill deficits.`;

  document.getElementById("rm-stat-total").textContent = summary.totalRequiredSkills;
  document.getElementById("rm-stat-acquired").textContent = summary.acquiredSkillsCount;
  document.getElementById("rm-stat-missing").textContent = summary.missingSkillsCount;

  const completedSteps = steps.filter((s) => s.completed).length;
  const pct = steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 100;
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

function toggleStepCompletion(stepIdx) {
  if (!state.roadmapData) return;
  const steps = state.roadmapData.roadmap || state.roadmapData.steps;
  if (!steps || !steps[stepIdx]) return;
  steps[stepIdx].completed = !steps[stepIdx].completed;
  renderRoadmapView();
  showToast(
    steps[stepIdx].completed ? "Milestone completed! Great work." : "Milestone marked pending.",
    "info"
  );
}

// -------------------------------------------------------------
// Save Student Profile (Database persistence)
// -------------------------------------------------------------
function openSaveProfileModal() {
  document.getElementById("profile-modal").classList.remove("hidden");
}

function closeSaveProfileModal() {
  document.getElementById("profile-modal").classList.add("hidden");
}

async function confirmSaveProfile() {
  const name = document.getElementById("modal-name").value.trim() || "Demo Student";
  const edu = document.getElementById("modal-edu").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/profiles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        education: edu,
        skills: Array.from(state.userSkills),
        targetRoleId: state.selectedRoleId,
      }),
    });

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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        history: state.chatHistory,
        contextRoleId: state.selectedRoleId,
      }),
    });

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
