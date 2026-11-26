/**
 * Pathify-AI Resume Analyzer & Intelligence Studio
 * Full frontend integration module for deep-scan ATS parsing,
 * four-pillar diagnostics, JD alignment, AI bullet rewrites, and PDF export.
 */

const resumeState = {
  currentAnalysis: null,
  selectedFile: null,
  extractedData: null,
  correctedSkills: [],
  history: [],
  isProcessing: false,
};

/**
 * Resets all Resume Analyzer state, dropzone file selection, active result cards,
 * and history table to prevent cross-account data leakage upon account switching or signout.
 */
function resetResumeState() {
  resumeState.currentAnalysis = null;
  resumeState.selectedFile = null;
  resumeState.extractedData = null;
  resumeState.correctedSkills = [];
  resumeState.history = [];
  resumeState.isProcessing = false;

  if (typeof removeSelectedResumeFile === "function") {
    removeSelectedResumeFile();
  }

  const jdInput = document.getElementById("resume-target-jd");
  if (jdInput) jdInput.value = "";

  const resultsContainer = document.getElementById("resume-results-container");
  if (resultsContainer) resultsContainer.classList.add("hidden");

  const progressContainer = document.getElementById("resume-progress-container");
  if (progressContainer) progressContainer.classList.add("hidden");

  const tbody = document.getElementById("resume-history-tbody");
  if (tbody) tbody.innerHTML = "";
  const emptyState = document.getElementById("resume-history-empty");
  if (emptyState) emptyState.classList.remove("hidden");
  const tableWrapper = document.getElementById("resume-history-table-wrapper");
  if (tableWrapper) tableWrapper.classList.add("hidden");

  const bulletInput = document.getElementById("ai-bullet-input");
  if (bulletInput) bulletInput.value = "";
  const rewriteResults = document.getElementById("ai-bullet-results");
  if (rewriteResults) rewriteResults.classList.add("hidden");
}
window.resetResumeState = resetResumeState;

// ---------------------------------------------------------------------------
// Initialization & Navigation Hook
// ---------------------------------------------------------------------------
function initResumeView() {
  populateResumeRoleDropdown();
  setupResumeDropzone();
  loadResumeHistory();
  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }
}

function populateResumeRoleDropdown() {
  const select = document.getElementById("resume-target-role");
  if (!select) return;

  const currentVal = select.value || (state && state.selectedRoleId) || "role-1";
  select.innerHTML = '<option value="">-- No specific role (General ATS) --</option>';

  const roles = (state && state.roles && state.roles.length > 0)
    ? state.roles
    : [
        { id: "role-1", slug: "role-1", title: "Full-Stack Developer" },
        { id: "role-2", slug: "role-2", title: "Data Analyst" },
        { id: "role-3", slug: "role-3", title: "AI Engineer" },
      ];

  roles.forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.id || r.slug;
    opt.textContent = r.title;
    if (opt.value === currentVal) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
}

// ---------------------------------------------------------------------------
// Drag-and-Drop & File Selection Handling
// ---------------------------------------------------------------------------
function setupResumeDropzone() {
  const dropzone = document.getElementById("resume-dropzone");
  const fileInput = document.getElementById("resume-file-input");
  if (!dropzone || !fileInput) return;

  // Prevent multiple bindings
  if (dropzone.dataset.bound === "true") return;
  dropzone.dataset.bound = "true";

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("border-indigo-500", "bg-indigo-950/20");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("border-indigo-500", "bg-indigo-950/20");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });
}

function handleFileSelected(file) {
  if (!file) return;

  const validExtensions = [".pdf", ".docx", ".doc", ".txt"];
  const lowerName = file.name.toLowerCase();
  const isValid = validExtensions.some((ext) => lowerName.endsWith(ext));

  if (!isValid) {
    showToast("Invalid format. Please upload a PDF, DOCX, or TXT resume.", "warning");
    return;
  }

  const maxSize = 5 * 1024 * 1024; // 5 MB
  if (file.size > maxSize) {
    showToast("File is too large. Maximum size is 5 MB.", "warning");
    return;
  }

  resumeState.selectedFile = file;

  // Update UI Card
  const fileDetails = document.getElementById("resume-file-details");
  const fileNameEl = document.getElementById("resume-file-name");
  const fileSizeEl = document.getElementById("resume-file-size");
  const promptEl = document.getElementById("resume-dropzone-prompt");

  if (fileNameEl) fileNameEl.textContent = file.name;
  if (fileSizeEl) fileSizeEl.textContent = formatBytes(file.size);

  if (promptEl) promptEl.classList.add("hidden");
  if (fileDetails) fileDetails.classList.remove("hidden");

  showToast(`Selected "${file.name}" for analysis.`, "info");
  if (window.lucide) setTimeout(() => lucide.createIcons(), 50);
}

function removeSelectedResumeFile(e) {
  if (e) e.stopPropagation();
  resumeState.selectedFile = null;
  const fileInput = document.getElementById("resume-file-input");
  if (fileInput) fileInput.value = "";

  const fileDetails = document.getElementById("resume-file-details");
  const promptEl = document.getElementById("resume-dropzone-prompt");

  if (fileDetails) fileDetails.classList.add("hidden");
  if (promptEl) promptEl.classList.remove("hidden");
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// ---------------------------------------------------------------------------
// Resume Analysis Workflow (Zero Mock Data)
// ---------------------------------------------------------------------------
async function startResumeAnalysis() {
  if (resumeState.isProcessing) return;

  if (!resumeState.selectedFile) {
    showToast("Please select or drop a resume file first.", "warning");
    return;
  }

  const targetRoleSelect = document.getElementById("resume-target-role");
  const jdInput = document.getElementById("resume-target-jd");
  const roleId = targetRoleSelect ? targetRoleSelect.value : "";
  const jobDescription = jdInput ? jdInput.value.trim() : "";

  setResumeProcessingState(true);
  updateProcessingStep(1, "Uploading & validating document...");

  try {
    // 1. Upload File
    const formData = new FormData();
    formData.append("file", resumeState.selectedFile);

    const uploadRes = await fetch(`${API_BASE}/api/resume/upload`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders(),
      body: formData,
    });

    if (uploadRes.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!uploadRes.ok) {
      const errDetail = await extractErrorDetail(uploadRes, "Failed to upload and parse resume.");
      throw new Error(errDetail);
    }

    const uploadData = await uploadRes.json();
    updateProcessingStep(2, "Parsing text and structural sections...");

    // 2. Perform 4-Pillar Scoring & Intelligence Analysis
    updateProcessingStep(3, "Evaluating 4 pillars & benchmarking skills...");
    const analyzePayload = {
      filename: uploadData.filename,
      raw_text: uploadData.raw_text,
      file_size_bytes: uploadData.file_size_bytes,
      file_type: uploadData.file_type,
      role_id: roleId || null,
      job_description: jobDescription || null,
    };

    const analyzeRes = await fetch(`${API_BASE}/api/resume/analyze`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(analyzePayload),
    });

    if (analyzeRes.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!analyzeRes.ok) {
      const errDetail = await extractErrorDetail(analyzeRes, "Failed to execute resume analysis.");
      throw new Error(errDetail);
    }

    const analysisData = await analyzeRes.json();
    updateProcessingStep(4, "Analysis finalized! Rendering results...");

    resumeState.currentAnalysis = analysisData;
    resumeState.extractedData = uploadData.parsed;
    resumeState.correctedSkills = [...(analysisData.parsed_data?.extracted_skills || [])];

    // Render all panels
    renderResumeAnalysis(analysisData);
    loadResumeHistory();

    showToast("Resume analysis completed successfully!", "success");

    // Scroll to results
    const resultsContainer = document.getElementById("resume-results-container");
    if (resultsContainer) {
      resultsContainer.classList.remove("hidden");
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (err) {
    console.error("Resume analysis error:", err);
    showToast(err.message || "An unexpected error occurred during resume analysis.", "error");
  } finally {
    setResumeProcessingState(false);
  }
}

function setResumeProcessingState(isProcessing) {
  resumeState.isProcessing = isProcessing;
  const btn = document.getElementById("btn-analyze-resume");
  const spinner = document.getElementById("resume-analyze-spinner");
  const btnText = document.getElementById("resume-analyze-btn-text");
  const stepper = document.getElementById("resume-processing-stepper");

  if (btn) btn.disabled = isProcessing;
  if (spinner) {
    if (isProcessing) spinner.classList.remove("hidden");
    else spinner.classList.add("hidden");
  }
  if (btnText) {
    btnText.textContent = isProcessing ? "Analyzing Resume..." : "Analyze Resume";
  }
  if (stepper) {
    if (isProcessing) stepper.classList.remove("hidden");
    else setTimeout(() => stepper.classList.add("hidden"), 1200);
  }
}

function updateProcessingStep(stepNum, statusText) {
  const statusEl = document.getElementById("resume-stepper-status");
  if (statusEl) statusEl.textContent = statusText;

  for (let i = 1; i <= 4; i++) {
    const dot = document.getElementById(`resume-step-dot-${i}`);
    if (dot) {
      if (i <= stepNum) {
        dot.className = "w-3 h-3 rounded-full bg-indigo-500 ring-4 ring-indigo-500/20";
      } else {
        dot.className = "w-3 h-3 rounded-full bg-slate-700";
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Render Intelligence Dashboard & Four Pillars
// ---------------------------------------------------------------------------
function renderResumeAnalysis(data) {
  if (!data) return;

  // 1. Overall Score & Tier
  const score = Math.round(data.overall_score || 0);
  const scoreEl = document.getElementById("resume-overall-score");
  const tierEl = document.getElementById("resume-score-tier");
  const scoreDescEl = document.getElementById("resume-score-description");
  const circleProgress = document.getElementById("resume-score-circle-progress");

  if (scoreEl) scoreEl.textContent = score;

  // Circular gauge circumference: r=40 => 2 * pi * 40 = ~251.3
  if (circleProgress) {
    const strokeDashoffset = 251.3 - (251.3 * score) / 100;
    circleProgress.style.strokeDashoffset = strokeDashoffset;

    if (score >= 80) circleProgress.setAttribute("stroke", "#10b981"); // emerald
    else if (score >= 65) circleProgress.setAttribute("stroke", "#6366f1"); // indigo
    else if (score >= 50) circleProgress.setAttribute("stroke", "#f59e0b"); // amber
    else circleProgress.setAttribute("stroke", "#ef4444"); // rose
  }

  let tier = "Needs Critical Attention";
  let tierColor = "bg-rose-500/10 text-rose-400 border-rose-500/30";
  let tierDesc = "Your resume exhibits significant gaps in ATS structural formatting, keywords, or quantifiable experience.";

  if (score >= 85) {
    tier = "ATS Ready • Exceptional";
    tierColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    tierDesc = "Outstanding ATS readability and strong alignment with modern industry standards. Ready for high-volume recruiter parsing.";
  } else if (score >= 70) {
    tier = "Strong Profile • Minor Polish Needed";
    tierColor = "bg-indigo-500/10 text-indigo-400 border-indigo-500/30";
    tierDesc = "Strong baseline with solid technical coverage. Closing a few keyword gaps and metric bullets will maximize recruiter callbacks.";
  } else if (score >= 50) {
    tier = "Moderate Baseline • Optimization Required";
    tierColor = "bg-amber-500/10 text-amber-400 border-amber-500/30";
    tierDesc = "Acceptable foundation, but missing important industry-specific technologies and measurable action accomplishments.";
  }

  if (tierEl) {
    tierEl.className = `px-3 py-1 rounded-full text-xs font-bold border ${tierColor}`;
    tierEl.textContent = tier;
  }
  if (scoreDescEl) scoreDescEl.textContent = tierDesc;

  // Quick Stats
  const filenameEl = document.getElementById("resume-stat-filename");
  const targetRoleEl = document.getElementById("resume-stat-role");
  const wordCountEl = document.getElementById("resume-stat-words");
  const matchedSkillsCountEl = document.getElementById("resume-stat-matched-skills");
  const missingSkillsCountEl = document.getElementById("resume-stat-missing-skills");

  if (filenameEl) filenameEl.textContent = data.filename || "Resume Document";
  if (targetRoleEl) targetRoleEl.textContent = (data.role && data.role.title) ? data.role.title : "General ATS Standard";
  if (wordCountEl) wordCountEl.textContent = data.parsed_data?.raw_text ? data.parsed_data.raw_text.split(/\s+/).filter(Boolean).length : "-";
  if (matchedSkillsCountEl) matchedSkillsCountEl.textContent = data.matched_skills ? data.matched_skills.length : 0;
  if (missingSkillsCountEl) missingSkillsCountEl.textContent = data.missing_skills ? data.missing_skills.length : 0;

  // 2. Render Four Pillars
  renderPillarCard("formatting", data.pillar_formatting_score, data.score_breakdown?.formatting);
  renderPillarCard("content", data.pillar_content_score, data.score_breakdown?.content);
  renderPillarCard("skills", data.pillar_skills_score, data.score_breakdown?.skills);
  renderPillarCard("experience", data.pillar_experience_score, data.score_breakdown?.experience);

  // 3. Render Missing Skills & Roadmap Sync Section
  renderMissingSkillsSection(data.missing_skills, data.id);

  // 4. Render Job Description Matcher Section
  renderJdMatchSection(data.jd_match_percentage, data.score_breakdown?.jd_match, data.matched_skills, data.missing_skills);

  // 5. Render Parsed Data & Extraction Studio
  renderExtractionStudio(data.parsed_data, data.id);

  // 6. Pre-fill AI Improvement Studio
  if (data.parsed_data?.bullets && data.parsed_data.bullets.length > 0) {
    const bulletInput = document.getElementById("ai-bullet-input");
    if (bulletInput && !bulletInput.value.trim()) {
      bulletInput.value = data.parsed_data.bullets[0];
    }
  }

  // 7. Enable PDF Download Button
  const btnPdf = document.getElementById("btn-download-pdf");
  if (btnPdf) {
    btnPdf.onclick = () => downloadResumePdfReport(data.id, data.filename);
  }

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }
}

function renderPillarCard(pillarKey, score, details) {
  const scoreVal = Math.round(score || 0);
  const scoreEl = document.getElementById(`pillar-score-${pillarKey}`);
  const barEl = document.getElementById(`pillar-bar-${pillarKey}`);
  const findingsListEl = document.getElementById(`pillar-findings-${pillarKey}`);

  if (scoreEl) scoreEl.textContent = `${scoreVal}/100`;
  if (barEl) {
    barEl.style.width = `${scoreVal}%`;
    if (scoreVal >= 75) barEl.className = "h-2 rounded-full bg-emerald-500 transition-all duration-500";
    else if (scoreVal >= 55) barEl.className = "h-2 rounded-full bg-indigo-500 transition-all duration-500";
    else barEl.className = "h-2 rounded-full bg-amber-500 transition-all duration-500";
  }

  if (findingsListEl && details?.findings) {
    findingsListEl.innerHTML = "";
    details.findings.forEach((f) => {
      const li = document.createElement("li");
      li.className = "flex items-start gap-2 text-xs";

      let iconHtml = '<i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0"></i>';
      let textColor = "text-slate-300";

      if (f.status === "warn") {
        iconHtml = '<i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0"></i>';
        textColor = "text-amber-200/90";
      } else if (f.status === "fail") {
        iconHtml = '<i data-lucide="x-circle" class="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0"></i>';
        textColor = "text-rose-200/90";
      }

      li.innerHTML = `${iconHtml}<span class="${textColor}">${escapeHtml(f.text)}</span>`;
      findingsListEl.appendChild(li);
    });
  }
}

// ---------------------------------------------------------------------------
// Render Missing Skills & Roadmap Sync
// ---------------------------------------------------------------------------
function renderMissingSkillsSection(missingSkills, analysisId) {
  const container = document.getElementById("resume-missing-skills-container");
  const countBadge = document.getElementById("resume-missing-skills-count");
  const syncBtn = document.getElementById("btn-sync-to-roadmap");

  if (countBadge) {
    countBadge.textContent = `${missingSkills?.length || 0} Identified`;
  }

  if (syncBtn) {
    syncBtn.onclick = () => syncMissingSkillsToRoadmap(analysisId);
  }

  if (!container) return;

  if (!missingSkills || missingSkills.length === 0) {
    container.innerHTML = `
      <div class="col-span-full p-6 text-center rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-400 text-xs">
        <i data-lucide="sparkles" class="w-6 h-6 text-emerald-400 mx-auto mb-2"></i>
        <span>No missing critical skills detected! Your technical keywords closely match the benchmark.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = "";
  missingSkills.forEach((skill) => {
    const card = document.createElement("div");
    card.className = "p-4 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-900/60 transition space-y-2";

    const prio = skill.priority || "Medium";
    let badgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/30";
    if (prio === "High") badgeClass = "bg-rose-500/10 text-rose-300 border-rose-500/30";
    else if (prio === "Low") badgeClass = "bg-slate-700/50 text-slate-300 border-slate-600";

    card.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <h4 class="text-sm font-bold text-white">${escapeHtml(skill.name)}</h4>
        <span class="px-2 py-0.5 text-[10px] font-bold rounded-full border ${badgeClass}">${prio} Priority</span>
      </div>
      <p class="text-xs text-slate-400 leading-relaxed">${escapeHtml(skill.learning_goal || `Study and master production usage of ${skill.name}.`)}</p>
      <div class="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800/60">
        <span>Required Level: ${skill.required_level || 3}/5</span>
        <span class="text-indigo-400 font-medium">${skill.category || "Technical"}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

async function syncMissingSkillsToRoadmap(analysisId) {
  if (!analysisId) return;

  const btn = document.getElementById("btn-sync-to-roadmap");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/resume/sync-to-roadmap/${analysisId}`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) {
      const errDetail = await extractErrorDetail(res, "Failed to sync skills to roadmap.");
      throw new Error(errDetail);
    }

    const result = await res.json();
    showToast(result.message || "Successfully synced missing skills to your roadmap!", "success");

    // Automatically transition user to their Roadmap tab
    setTimeout(() => {
      switchTab("roadmap");
    }, 1200);
  } catch (err) {
    console.error("Roadmap sync error:", err);
    showToast(err.message || "Error syncing missing skills.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Render Job Description Matching Section
// ---------------------------------------------------------------------------
function renderJdMatchSection(matchPercentage, jdDetails, matchedSkills, missingSkills) {
  const container = document.getElementById("resume-jd-match-panel");
  if (!container) return;

  const matchScore = matchPercentage !== null && matchPercentage !== undefined ? Math.round(matchPercentage) : null;
  const matchGauge = document.getElementById("resume-jd-match-gauge");
  const matchPercentText = document.getElementById("resume-jd-match-percent");
  const matchedTagsContainer = document.getElementById("resume-jd-matched-tags");
  const missingTagsContainer = document.getElementById("resume-jd-missing-tags");

  if (matchScore !== null) {
    if (matchPercentText) matchPercentText.textContent = `${matchScore}%`;
    if (matchGauge) {
      matchGauge.style.width = `${matchScore}%`;
      if (matchScore >= 70) matchGauge.className = "h-2.5 rounded-full bg-emerald-500 transition-all duration-500";
      else if (matchScore >= 50) matchGauge.className = "h-2.5 rounded-full bg-indigo-500 transition-all duration-500";
      else matchGauge.className = "h-2.5 rounded-full bg-amber-500 transition-all duration-500";
    }
  }

  // Matched Tags
  if (matchedTagsContainer) {
    matchedTagsContainer.innerHTML = "";
    const matchedList = jdDetails?.matched_keywords || (matchedSkills || []).map((s) => s.name);
    if (matchedList && matchedList.length > 0) {
      matchedList.forEach((kw) => {
        const span = document.createElement("span");
        span.className = "inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30";
        span.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> ${escapeHtml(kw)}`;
        matchedTagsContainer.appendChild(span);
      });
    } else {
      matchedTagsContainer.innerHTML = '<span class="text-xs text-slate-500 italic">No direct keyword overlaps detected yet.</span>';
    }
  }

  // Missing Tags
  if (missingTagsContainer) {
    missingTagsContainer.innerHTML = "";
    const missingList = jdDetails?.missing_keywords || (missingSkills || []).map((s) => s.name);
    if (missingList && missingList.length > 0) {
      missingList.forEach((kw) => {
        const span = document.createElement("span");
        span.className = "inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30";
        span.innerHTML = `<i data-lucide="plus" class="w-3 h-3 text-rose-400"></i> ${escapeHtml(kw)}`;
        missingTagsContainer.appendChild(span);
      });
    } else {
      missingTagsContainer.innerHTML = '<span class="text-xs text-slate-500 italic">No missing keywords found for this role description.</span>';
    }
  }
}

// ---------------------------------------------------------------------------
// Render Extraction & Correction Studio
// ---------------------------------------------------------------------------
function renderExtractionStudio(parsed, analysisId) {
  if (!parsed) return;

  const contact = parsed.contact || {};
  const nameInput = document.getElementById("resume-edit-name");
  const emailInput = document.getElementById("resume-edit-email");
  const phoneInput = document.getElementById("resume-edit-phone");
  const linkedinInput = document.getElementById("resume-edit-linkedin");
  const githubInput = document.getElementById("resume-edit-github");

  if (nameInput) nameInput.value = contact.name || "";
  if (emailInput) emailInput.value = contact.email || "";
  if (phoneInput) phoneInput.value = contact.phone || "";
  if (linkedinInput) linkedinInput.value = contact.linkedin || "";
  if (githubInput) githubInput.value = contact.github || "";

  // Render skills tags
  renderSkillTagCloud();

  // Save Corrections Button
  const saveBtn = document.getElementById("btn-save-resume-corrections");
  if (saveBtn) {
    saveBtn.onclick = () => saveResumeCorrections(analysisId);
  }
}

function renderSkillTagCloud() {
  const container = document.getElementById("resume-extracted-skills-cloud");
  if (!container) return;

  container.innerHTML = "";
  if (!resumeState.correctedSkills || resumeState.correctedSkills.length === 0) {
    container.innerHTML = '<span class="text-xs text-slate-500 italic">No skills extracted yet. Add your skills below.</span>';
    return;
  }

  resumeState.correctedSkills.forEach((skill, idx) => {
    const tag = document.createElement("span");
    tag.className = "inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-medium bg-slate-800 text-slate-200 border border-slate-700 hover:border-indigo-500 transition group";
    tag.innerHTML = `
      <span>${escapeHtml(skill)}</span>
      <button type="button" onclick="removeExtractedSkill(${idx})" class="text-slate-400 hover:text-rose-400 transition ml-0.5">
        &times;
      </button>
    `;
    container.appendChild(tag);
  });
}

function removeExtractedSkill(index) {
  if (resumeState.correctedSkills && resumeState.correctedSkills[index] !== undefined) {
    resumeState.correctedSkills.splice(index, 1);
    renderSkillTagCloud();
  }
}

function addCustomSkillToResume() {
  const input = document.getElementById("resume-add-skill-input");
  if (!input) return;

  const val = input.value.trim();
  if (!val) return;

  if (!resumeState.correctedSkills.includes(val)) {
    resumeState.correctedSkills.push(val);
    renderSkillTagCloud();
    input.value = "";
    showToast(`Added "${val}" to extracted skills.`, "info");
  } else {
    showToast(`"${val}" is already included.`, "warning");
  }
}

async function saveResumeCorrections(analysisId) {
  if (!analysisId) return;

  const btn = document.getElementById("btn-save-resume-corrections");
  if (btn) btn.disabled = true;

  try {
    const contactPayload = {
      name: document.getElementById("resume-edit-name")?.value || "",
      email: document.getElementById("resume-edit-email")?.value || "",
      phone: document.getElementById("resume-edit-phone")?.value || "",
      linkedin: document.getElementById("resume-edit-linkedin")?.value || "",
      github: document.getElementById("resume-edit-github")?.value || "",
    };

    const payload = {
      corrected_skills: resumeState.correctedSkills,
      corrected_contact: contactPayload,
    };

    const res = await fetch(`${API_BASE}/api/resume/correct/${analysisId}`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) {
      const errDetail = await extractErrorDetail(res, "Failed to update corrections.");
      throw new Error(errDetail);
    }

    const updated = await res.json();
    resumeState.currentAnalysis = updated;
    renderResumeAnalysis(updated);
    showToast("Corrections saved and scores successfully recalculated!", "success");
  } catch (err) {
    console.error("Correction error:", err);
    showToast(err.message || "Failed to save corrections.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// AI Resume Improvement Studio (XYZ Formula Rewriter)
// ---------------------------------------------------------------------------
async function improveBulletWithAi() {
  const input = document.getElementById("ai-bullet-input");
  const targetRoleInput = document.getElementById("ai-bullet-role");
  const btn = document.getElementById("btn-ai-rewrite-bullet");

  if (!input || !input.value.trim()) {
    showToast("Please enter an experience bullet point to rewrite.", "warning");
    return;
  }

  const bulletText = input.value.trim();
  const targetRole = targetRoleInput ? targetRoleInput.value.trim() : "Software Engineer";

  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/resume/rewrite-bullet`, {
      method: "POST",
      credentials: "include",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        bullet_text: bulletText,
        target_role: targetRole,
      }),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) {
      const errDetail = await extractErrorDetail(res, "Failed to generate AI rewrites.");
      throw new Error(errDetail);
    }

    const data = await res.json();
    renderAiBulletResults(data);
    showToast("Generated high-impact Google XYZ rewrites!", "success");
  } catch (err) {
    console.error("AI rewrite error:", err);
    showToast(err.message || "Error generating AI suggestions.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderAiBulletResults(result) {
  const container = document.getElementById("ai-bullet-results-container");
  if (!container) return;

  container.classList.remove("hidden");

  // Impact Score & Checks
  const impact = result.impact_analysis || {};
  const scoreEl = document.getElementById("ai-bullet-impact-score");
  const scoreBar = document.getElementById("ai-bullet-impact-bar");
  const verbCheck = document.getElementById("ai-check-verb");
  const metricsCheck = document.getElementById("ai-check-metrics");
  const buzzwordNotice = document.getElementById("ai-buzzword-notice");

  const score = Math.round(impact.impact_score || 0);
  if (scoreEl) scoreEl.textContent = `${score}/100`;
  if (scoreBar) {
    scoreBar.style.width = `${score}%`;
    if (score >= 75) scoreBar.className = "h-2 rounded-full bg-emerald-500";
    else if (score >= 50) scoreBar.className = "h-2 rounded-full bg-indigo-500";
    else scoreBar.className = "h-2 rounded-full bg-amber-500";
  }

  if (verbCheck) {
    verbCheck.innerHTML = impact.has_action_verb
      ? '<span class="text-emerald-400 font-semibold flex items-center gap-1"><i data-lucide="check" class="w-3.5 h-3.5"></i> Action Verb Included</span>'
      : '<span class="text-rose-400 font-semibold flex items-center gap-1"><i data-lucide="x" class="w-3.5 h-3.5"></i> Missing Strong Action Verb</span>';
  }

  if (metricsCheck) {
    metricsCheck.innerHTML = impact.has_metrics
      ? '<span class="text-emerald-400 font-semibold flex items-center gap-1"><i data-lucide="check" class="w-3.5 h-3.5"></i> Quantifiable Metrics Found</span>'
      : '<span class="text-amber-400 font-semibold flex items-center gap-1"><i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> Lacks Measurable Impact (%, $, #)</span>';
  }

  if (buzzwordNotice) {
    if (impact.buzzwords_found && impact.buzzwords_found.length > 0) {
      buzzwordNotice.classList.remove("hidden");
      buzzwordNotice.textContent = `Warning: detected weak buzzwords (${impact.buzzwords_found.join(", ")}). Replace with concrete metrics.`;
    } else {
      buzzwordNotice.classList.add("hidden");
    }
  }

  // Rewrites List
  const rewritesList = document.getElementById("ai-rewrites-list");
  if (rewritesList && result.rewrites) {
    rewritesList.innerHTML = "";
    result.rewrites.forEach((rw, idx) => {
      const card = document.createElement("div");
      card.className = "p-4 rounded-xl bg-slate-900 border border-indigo-900/40 space-y-2 relative group";
      card.innerHTML = `
        <div class="flex items-center justify-between text-xs font-semibold text-indigo-400">
          <span>Formula: ${escapeHtml(rw.label || rw.style || "Google XYZ Pattern")}</span>
          <button type="button" onclick="copyRewriteText(this, ${idx})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition flex items-center gap-1">
            <i data-lucide="copy" class="w-3 h-3"></i> Copy
          </button>
        </div>
        <p class="text-xs text-slate-100 leading-relaxed font-mono" id="rewrite-text-${idx}">${escapeHtml(rw.text || rw.rewritten)}</p>
        <p class="text-[11px] text-slate-400 italic">${escapeHtml(rw.rationale || rw.formula_breakdown?.action_z || "")}</p>
      `;
      rewritesList.appendChild(card);
    });
  }

  // Recommended Verbs
  const verbsContainer = document.getElementById("ai-recommended-verbs");
  if (verbsContainer && result.recommended_action_verbs) {
    verbsContainer.innerHTML = "";
    result.recommended_action_verbs.forEach((verb) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 text-indigo-300 border border-slate-700 hover:border-indigo-500 hover:bg-indigo-950/40 transition";
      btn.textContent = verb;
      btn.onclick = () => insertActionVerb(verb);
      verbsContainer.appendChild(btn);
    });
  }

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }
}

function copyRewriteText(btn, idx) {
  const textEl = document.getElementById(`rewrite-text-${idx}`);
  if (!textEl) return;

  navigator.clipboard.writeText(textEl.textContent).then(() => {
    showToast("Copied rewrite to clipboard!", "success");
    btn.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i> Copied';
    if (window.lucide) setTimeout(() => lucide.createIcons(), 50);
    setTimeout(() => {
      btn.innerHTML = '<i data-lucide="copy" class="w-3 h-3"></i> Copy';
      if (window.lucide) setTimeout(() => lucide.createIcons(), 50);
    }, 2000);
  });
}

function insertActionVerb(verb) {
  const input = document.getElementById("ai-bullet-input");
  if (!input) return;

  const current = input.value.trim();
  input.value = `${verb} ${current}`;
  input.focus();
}

// ---------------------------------------------------------------------------
// Resume Analysis History & PDF Export
// ---------------------------------------------------------------------------
async function loadResumeHistory() {
  const container = document.getElementById("resume-history-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/resume/history`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) return;
    if (!res.ok) return;

    const data = await res.json();
    resumeState.history = data.history || [];
    renderHistoryTable(resumeState.history);
  } catch (err) {
    console.error("Failed to load resume history:", err);
  }
}

function renderHistoryTable(historyList) {
  const tbody = document.getElementById("resume-history-tbody");
  const emptyState = document.getElementById("resume-history-empty");
  const tableWrapper = document.getElementById("resume-history-table-wrapper");

  if (!tbody) return;

  if (!historyList || historyList.length === 0) {
    if (emptyState) emptyState.classList.remove("hidden");
    if (tableWrapper) tableWrapper.classList.add("hidden");
    return;
  }

  if (emptyState) emptyState.classList.add("hidden");
  if (tableWrapper) tableWrapper.classList.remove("hidden");

  tbody.innerHTML = "";
  historyList.forEach((item) => {
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-800 hover:bg-slate-800/40 transition text-xs";

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : "-";
    const scoreVal = Math.round(item.overall_score || 0);

    let scoreClass = "text-emerald-400";
    if (scoreVal < 50) scoreClass = "text-rose-400";
    else if (scoreVal < 70) scoreClass = "text-amber-400";

    tr.innerHTML = `
      <td class="py-3 px-4 font-medium text-white flex items-center gap-2">
        <i data-lucide="file-text" class="w-4 h-4 text-indigo-400"></i>
        <span>${escapeHtml(item.filename)}</span>
      </td>
      <td class="py-3 px-4 text-slate-300">${escapeHtml(item.target_role_title || "General")}</td>
      <td class="py-3 px-4 font-bold ${scoreClass}">${scoreVal}/100</td>
      <td class="py-3 px-4 text-slate-400">${item.jd_match_percentage !== null ? `${Math.round(item.jd_match_percentage)}%` : "-"}</td>
      <td class="py-3 px-4 text-slate-500">${dateStr}</td>
      <td class="py-3 px-4 text-right space-x-2">
        <button onclick="loadHistoricalAnalysis('${item.id}')" class="px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600 hover:text-white transition font-medium">
          View
        </button>
        <button onclick="downloadResumePdfReport('${item.id}', '${escapeHtml(item.filename)}')" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition" title="Download ReportLab PDF">
          <i data-lucide="download" class="w-3.5 h-3.5"></i>
        </button>
        <button onclick="deleteResumeHistoryItem('${item.id}')" class="px-2 py-1 text-slate-500 hover:text-rose-400 transition" title="Delete">
          <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  if (window.lucide) {
    setTimeout(() => lucide.createIcons(), 50);
  }
}

async function loadHistoricalAnalysis(analysisId) {
  if (!analysisId) return;

  try {
    const res = await fetch(`${API_BASE}/api/resume/history/${analysisId}`, {
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) throw new Error("Could not retrieve past analysis.");

    const item = await res.json();
    resumeState.currentAnalysis = item;
    resumeState.extractedData = item.parsed_data;
    resumeState.correctedSkills = [...(item.parsed_data?.extracted_skills || [])];

    renderResumeAnalysis(item);

    const resultsContainer = document.getElementById("resume-results-container");
    if (resultsContainer) {
      resultsContainer.classList.remove("hidden");
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    showToast(`Loaded analysis for "${item.filename}".`, "info");
  } catch (err) {
    console.error("Load history error:", err);
    showToast(err.message || "Failed to load past analysis.", "error");
  }
}

async function deleteResumeHistoryItem(analysisId) {
  if (!analysisId) return;
  if (!confirm("Are you sure you want to delete this resume analysis record?")) return;

  try {
    const res = await fetch(`${API_BASE}/api/resume/history/${analysisId}`, {
      method: "DELETE",
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) throw new Error("Failed to delete record.");

    showToast("Resume analysis record removed.", "info");
    loadResumeHistory();
  } catch (err) {
    console.error("Delete error:", err);
    showToast(err.message || "Could not delete record.", "error");
  }
}

async function downloadResumePdfReport(analysisId, filename) {
  if (!analysisId) return;

  showToast("Compiling official ReportLab PDF report...", "info");

  try {
    const res = await fetch(`${API_BASE}/api/resume/report/${analysisId}/download`, {
      method: "GET",
      credentials: "include",
      headers: getAuthHeaders(),
    });

    if (res.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!res.ok) throw new Error("Failed to compile PDF report.");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename || "Resume"}_PathifyAI_Report.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showToast("PDF report downloaded successfully!", "success");
  } catch (err) {
    console.error("PDF download error:", err);
    showToast(err.message || "Failed to download PDF report.", "error");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function extractErrorDetail(res, fallbackMsg) {
  try {
    const data = await res.json();
    return data.detail || data.message || fallbackMsg;
  } catch {
    const text = await res.text().catch(() => "");
    return text || fallbackMsg;
  }
}
