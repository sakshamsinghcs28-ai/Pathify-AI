import urllib.request
import urllib.error
import json

def verify_live():
    # 1. Health
    with urllib.request.urlopen("http://127.0.0.1:5000/api/health") as resp:
        data = json.loads(resp.read().decode())
        print("1. Health Check:", data["status"], "-", data["message"])
        assert data["status"] == "ok"

    # 2. Frontend Root
    with urllib.request.urlopen("http://127.0.0.1:5000/") as resp:
        html = resp.read().decode()
        print("2. Frontend Root length:", len(html))
        assert 'id="nav-resume"' in html, "Missing #nav-resume in live index.html"
        assert 'id="view-resume"' in html, "Missing #view-resume in live index.html"
        assert 'js/resume.js' in html, "Missing js/resume.js in live index.html"
        print("  ✓ Live index.html with Resume Analyzer confirmed!")

    # 3. Static JS
    with urllib.request.urlopen("http://127.0.0.1:5000/js/resume.js") as resp:
        js_code = resp.read().decode()
        assert "startResumeAnalysis" in js_code
        print(f"3. js/resume.js static asset confirmed (length: {len(js_code)} bytes)")

    # 4. Protected endpoint 401
    try:
        urllib.request.urlopen("http://127.0.0.1:5000/api/resume/history")
        raise AssertionError("Expected 401 Unauthorized for /api/resume/history without auth")
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print(f"4. Protected endpoint /api/resume/history returned expected HTTP {e.code} Unauthorized")

    print("\n>>> LIVE SERVER VERIFICATION SUCCESSFUL! <<<")

if __name__ == "__main__":
    verify_live()
