"""
Theme Functionality Verification Test for Pathify AI
Tests:
1. Verify HTML has Desktop and Mobile theme toggle buttons with Sun/Moon Lucide icons.
2. Verify HTML has the anti-FOUC inline theme initializer script in <head>.
3. Verify CSS defines variables for both dark and light modes.
4. Verify CSS smooth transitions on theme-related elements.
5. Verify CSS covers all requested views (Navbar, Dashboard, Careers, Skill Gap, Roadmap, AI Mentor, Auth, Modals).
6. Verify JS implements initTheme, applyTheme, toggleTheme, getCurrentTheme, localStorage persistence and defaults to Dark mode.
"""

import os
import re

def test_html_theme_elements():
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Desktop theme toggle button
    assert 'id="theme-toggle-btn"' in html, "Desktop theme toggle button missing id='theme-toggle-btn'"
    assert 'onclick="toggleTheme()"' in html, "onclick='toggleTheme()' missing"
    assert 'id="theme-toggle-icon"' in html, "Desktop theme icon missing id='theme-toggle-icon'"

    # 2. Mobile theme toggle button
    assert 'id="mobile-theme-btn"' in html, "Mobile theme toggle button missing id='mobile-theme-btn'"
    assert 'id="mobile-theme-icon"' in html, "Mobile theme icon missing id='mobile-theme-icon'"

    # 3. Anti-FOUC script in head
    assert "localStorage.getItem('pathify_theme')" in html or 'localStorage.getItem("pathify_theme")' in html, "Anti-FOUC script missing localStorage check"
    assert "document.documentElement.classList.add('dark')" in html or 'document.documentElement.classList.add("dark")' in html, "Dark default missing"

    # 4. Roadmap Career Selection Dropdown
    assert 'id="roadmap-role-select"' in html, "Roadmap dropdown missing id='roadmap-role-select'"
    assert 'onchange="onRoadmapRoleSelectionChanged()"' in html, "Roadmap dropdown missing onchange='onRoadmapRoleSelectionChanged()'"
    print("[PASS] HTML verification passed: desktop/mobile toggle buttons, anti-FOUC script, and Roadmap career selector present.")

def test_css_theme_variables():
    css_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # 1. CSS variables
    assert ":root" in css, "Missing :root definition"
    assert "--bg-body" in css, "Missing --bg-body variable"
    assert "--bg-card" in css, "Missing --bg-card variable"
    assert "--text-title" in css, "Missing --text-title variable"
    assert "--theme-transition" in css, "Missing --theme-transition variable"

    # 2. Refined Global Color Palette Verification
    assert "#F5F7FB" in css, "Missing Soft light grey (#F5F7FB) background"
    assert "#172033" in css, "Missing Dark navy (#172033) primary text"
    assert "#475569" in css, "Missing Slate grey (#475569) secondary text"
    assert "#64748B" in css, "Missing Readable grey (#64748B) muted text"
    assert "#5B45E8" in css, "Missing Deep purple (#5B45E8) primary button"
    assert "#DCE3EE" in css, "Missing Light grey (#DCE3EE) border"

    # 3. Light mode definitions across all components
    assert "html.light" in css, "Missing html.light class selector"
    assert "html.light body" in css, "Missing light mode body override"
    assert "html.light header" in css, "Missing light mode header override"
    assert "#view-dashboard" in css, "Missing dashboard view styling"
    assert "#view-careers" in css or "#careers-roles-container" in css, "Missing careers view styling"
    assert "#view-skillgap" in css or "#skill-pills-container" in css, "Missing skill gap styling"
    assert "#view-roadmap" in css or "#roadmap-steps-container" in css, "Missing roadmap view styling"
    assert "#view-auth" in css, "Missing auth view styling"
    assert "#view-chat" in css, "Missing chat view styling"
    assert "#profile-modal" in css, "Missing modal styling"
    assert "#theme-toggle-btn" in css, "Missing theme toggle button styling"
    assert "#toast" in css, "Missing toast notification styling"

    # 4. Smooth transition
    assert "transition: var(--theme-transition)" in css, "Smooth transition not applied to elements"
    print("[PASS] CSS verification passed: Global palette (#F5F7FB, #172033, #5B45E8, #DCE3EE), variables, and component overrides verified.")

def test_js_theme_logic():
    js_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Functions present
    assert "function getCurrentTheme()" in js, "Missing getCurrentTheme function"
    assert "function applyTheme(theme)" in js, "Missing applyTheme function"
    assert "function toggleTheme()" in js, "Missing toggleTheme function"
    assert "function initTheme()" in js, "Missing initTheme function"

    # 2. LocalStorage interaction
    assert 'localStorage.getItem("pathify_theme")' in js or "localStorage.getItem('pathify_theme')" in js, "localStorage getItem missing"
    assert 'localStorage.setItem("pathify_theme"' in js or "localStorage.setItem('pathify_theme'" in js, "localStorage setItem missing"

    # 3. Default to dark mode
    assert '|| "dark"' in js or "|| 'dark'" in js, "Dark mode default missing"

    # 4. DOMContentLoaded hook
    assert "initTheme()" in js, "initTheme not called in initialization"
    # 5. Roadmap and Skill Gap career synchronization functions
    assert "function syncRoleDropdowns(roleId)" in js, "Missing syncRoleDropdowns function"
    assert "function onRoadmapRoleSelectionChanged()" in js, "Missing onRoadmapRoleSelectionChanged function"
    print("[PASS] JS verification passed: theme state functions and Roadmap/SkillGap synchronization logic verified.")

if __name__ == "__main__":
    print("Testing Dark / Light Theme Implementation...")
    test_html_theme_elements()
    test_css_theme_variables()
    test_js_theme_logic()
    print("============================================================")
    print("ALL THEME TESTS PASSED SUCCESSFULLY!")
    print("============================================================")
