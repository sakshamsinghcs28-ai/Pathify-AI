"""Automated integration tests for Pathify-AI FastAPI backend and Frontend.

Validates all 7 original endpoints from API.md + new /api/chat endpoint + frontend static serving.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from httpx import AsyncClient, ASGITransport
from backend.app.main import app


async def test_all_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 0. Frontend Static Serving
        print("\n[Test 0] Testing Frontend Static Serving (GET /)...")
        res = await client.get("/")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert "Pathify" in res.text
        print("  -> Passed. Frontend index.html served at root.")

        # 1. Health check
        print("\n[Test 1] Testing GET /api/health...")
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["status"] == "ok"
        assert "message" in data
        assert "timestamp" in data
        print("  -> Passed. Health check response:", data)

        # 2. List career roles
        print("\n[Test 2] Testing GET /api/roles...")
        res = await client.get("/api/roles")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["totalRoles"] >= 3
        roles = {r["id"]: r for r in data["roles"]}
        assert "role-1" in roles
        assert "role-2" in roles
        assert "role-3" in roles
        r1 = roles["role-1"]
        r2 = roles["role-2"]
        r3 = roles["role-3"]
        assert r1["title"] == "Full-Stack Developer"
        assert r2["title"] == "Data Analyst"
        assert r3["title"] == "AI Engineer"
        print(f"  -> Passed. Verified 3 primary roles: {r1['title']}, {r2['title']}, {r3['title']}")

        # 3. Analyze skills for a role (POST /api/skill-gap)
        print("\n[Test 3] Testing POST /api/skill-gap...")
        payload = {
            "roleId": "role-1",
            "skills": ["JavaScript", "React", "Node.js"],
        }
        res = await client.post("/api/skill-gap", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["roleId"] == "role-1"
        assert data["analysis"]["totalRequiredSkills"] == 7
        assert data["analysis"]["matchedCount"] == 3
        assert data["analysis"]["missingCount"] == 4
        assert data["analysis"]["matchPercentage"] == "43%"
        assert len(data["matchedSkills"]) == 3
        assert len(data["missingSkills"]) == 4
        print("  -> Passed. Skill gap analysis match:", data["analysis"]["matchPercentage"])

        # 4. Create student profile (POST /api/profiles)
        print("\n[Test 4] Testing POST /api/profiles...")
        profile_payload = {
            "name": "Demo Student",
            "education": "B.Tech Computer Science",
            "skills": ["Python", "SQL & Relational Databases"],
            "targetRoleId": "role-3",
        }
        res = await client.post("/api/profiles", json=profile_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        profile = data["profile"]
        profile_id = profile["id"]
        assert profile["name"] == "Demo Student"
        assert profile["targetRoleId"] == "role-3"
        assert profile["targetRoleTitle"] == "AI Engineer"
        print(f"  -> Passed. Created profile ID: {profile_id} for target role: {profile['targetRoleTitle']}")

        # 5. Get student profile (GET /api/profiles/:id)
        print("\n[Test 5] Testing GET /api/profiles/:id...")
        res = await client.get(f"/api/profiles/{profile_id}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["profile"]["id"] == profile_id
        print("  -> Passed. Retrieved saved profile correctly.")

        # 6. Get saved profile skill gap (GET /api/profiles/:id/skill-gap)
        print("\n[Test 6] Testing GET /api/profiles/:id/skill-gap...")
        res = await client.get(f"/api/profiles/{profile_id}/skill-gap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["roleTitle"] == "AI Engineer"
        print("  -> Passed. Profile skill gap match:", data["analysis"]["matchPercentage"])

        # 7. Get roadmap for saved profile (GET /api/profiles/:id/roadmap)
        print("\n[Test 7] Testing GET /api/profiles/:id/roadmap...")
        res = await client.get(f"/api/profiles/{profile_id}/roadmap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["targetRoleTitle"] == "AI Engineer"
        assert len(data["roadmap"]) > 0
        print(f"  -> Passed. Roadmap has {len(data['roadmap'])} steps. Step 1: {data['roadmap'][0]['skill']}")

        # 8. Test AI Career Chatbot (POST /api/chat)
        print("\n[Test 8] Testing POST /api/chat...")
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "What skills do I need to become an AI Engineer?",
                "history": [],
                "contextRoleId": "role-3",
            },
        )
        assert chat_res.status_code == 200, f"Expected 200, got {chat_res.status_code}"
        chat_data = chat_res.json()
        assert "reply" in chat_data and len(chat_data["reply"]) > 20
        assert "mode" in chat_data
        assert len(chat_data["suggestedQuestions"]) > 0
        print(f"  -> Passed. Chatbot ({chat_data['mode']}) returned response of {len(chat_data['reply'])} chars.")

    print("\n" + "=" * 60)
    print("ALL 9 TEST SUITES PASSED (FRONTEND + 7 ENDPOINTS + CHATBOT)!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
