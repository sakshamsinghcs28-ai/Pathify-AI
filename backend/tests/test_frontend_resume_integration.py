"""Integration test for Resume Analyzer Frontend Integration in Pathify AI.

Verifies:
1. index.html contains the desktop navigation button `#nav-resume`
2. index.html contains mobile navigation link for Resume
3. index.html contains `#view-resume` with all required submodules:
   - Dashboard Top Banner with circular score gauge
   - Drag-and-drop upload zone
   - Four-Pillar ATS diagnostic cards
   - Missing skills and roadmap sync
   - Job description keyword alignment
   - Parsed resume extraction and correction studio
   - AI bullet improvement studio
   - Resume history and PDF export
4. `js/resume.js` is included in `index.html` and static files are served properly
5. `app.js` registers `resume` in `PROTECTED_TABS` and tab switching logic
6. FastAPI backend serves `frontend/js/resume.js` with HTTP 200 OK
"""

import sys
from pathlib import Path
import httpx
from httpx import ASGITransport

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def test_index_html_structure():
    index_path = PROJECT_ROOT / "frontend" / "index.html"
    assert index_path.exists(), "frontend/index.html not found"

    html = index_path.read_text(encoding="utf-8")

    # 1. Navigation items
    assert 'id="nav-resume"' in html, "Missing #nav-resume in desktop nav"
    assert "switchTab('resume')" in html, "Missing switchTab('resume') in nav"

    # 2. Section view
    assert 'id="view-resume"' in html, "Missing #view-resume section"

    # 3. Upload & Dropzone
    assert 'id="resume-dropzone"' in html, "Missing #resume-dropzone"
    assert 'id="resume-file-input"' in html, "Missing #resume-file-input"
    assert 'id="btn-analyze-resume"' in html, "Missing #btn-analyze-resume"

    # 4. Intelligence Dashboard & Gauge
    assert 'id="resume-overall-score"' in html, "Missing #resume-overall-score"
    assert 'id="resume-score-circle-progress"' in html, "Missing circular score gauge"
    assert 'id="btn-download-pdf"' in html, "Missing #btn-download-pdf"

    # 5. Four Pillars
    for pillar in ["formatting", "content", "skills", "experience"]:
        assert f'id="pillar-score-{pillar}"' in html, f"Missing #pillar-score-{pillar}"
        assert f'id="pillar-bar-{pillar}"' in html, f"Missing #pillar-bar-{pillar}"
        assert f'id="pillar-findings-{pillar}"' in html, f"Missing #pillar-findings-{pillar}"

    # 6. Missing Skills & Roadmap Sync
    assert 'id="btn-sync-to-roadmap"' in html, "Missing #btn-sync-to-roadmap"
    assert 'id="resume-missing-skills-container"' in html, "Missing #resume-missing-skills-container"

    # 7. Job Description Matcher
    assert 'id="resume-jd-match-panel"' in html, "Missing #resume-jd-match-panel"
    assert 'id="resume-jd-matched-tags"' in html, "Missing #resume-jd-matched-tags"
    assert 'id="resume-jd-missing-tags"' in html, "Missing #resume-jd-missing-tags"

    # 8. Extraction & Correction Studio
    assert 'id="resume-extraction-studio"' in html, "Missing #resume-extraction-studio"
    assert 'id="btn-save-resume-corrections"' in html, "Missing #btn-save-resume-corrections"
    assert 'id="resume-edit-name"' in html, "Missing #resume-edit-name"
    assert 'id="resume-edit-email"' in html, "Missing #resume-edit-email"

    # 9. AI Bullet Studio
    assert 'id="ai-improvement-studio"' in html, "Missing #ai-improvement-studio"
    assert 'id="ai-bullet-input"' in html, "Missing #ai-bullet-input"
    assert 'id="btn-ai-rewrite-bullet"' in html, "Missing #btn-ai-rewrite-bullet"

    # 10. History
    assert 'id="resume-history-section"' in html, "Missing #resume-history-section"
    assert 'id="resume-history-tbody"' in html, "Missing #resume-history-tbody"

    # 11. Script tag
    assert 'src="js/resume.js"' in html, "Missing script tag for js/resume.js"

    print("  ✓ index.html DOM structure completely verified with all 11 UI components.")


def test_app_js_integration():
    app_js_path = PROJECT_ROOT / "frontend" / "app.js"
    assert app_js_path.exists(), "frontend/app.js not found"

    app_js = app_js_path.read_text(encoding="utf-8")

    assert '"resume"' in app_js, "resume not registered in app.js"
    assert 'PROTECTED_TABS = ["dashboard", "careers", "skillgap", "roadmap", "chat", "resume"]' in app_js, "resume not in PROTECTED_TABS"
    assert 'resume: "Resume Analyzer"' in app_js, "resume not in getTabDisplayName"
    assert 'initResumeView' in app_js, "initResumeView hook missing from switchTab"

    print("  ✓ app.js protected tabs and route guard hooks verified.")


async def test_static_serving_of_resume_module():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root index.html serves resume elements
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "view-resume" in res_root.text
        assert "nav-resume" in res_root.text

        # 2. js/resume.js served properly
        res_js = await client.get("/js/resume.js")
        assert res_js.status_code == 200, f"Expected 200 for /js/resume.js, got {res_js.status_code}"
        assert "resumeState" in res_js.text
        assert "startResumeAnalysis" in res_js.text

    print("  ✓ Static files served correctly through FastAPI ASGI mount.")


def main():
    print("=" * 80)
    print("RUNNING FRONTEND RESUME ANALYZER INTEGRATION TESTS")
    print("=" * 80)
    test_index_html_structure()
    test_app_js_integration()
    import asyncio
    asyncio.run(test_static_serving_of_resume_module())
    print("=" * 80)
    print(">>> ALL FRONTEND RESUME INTEGRATION TESTS PASSED! <<<")
    print("=" * 80)


if __name__ == "__main__":
    main()
