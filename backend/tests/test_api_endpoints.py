"""Automated integration tests for the Pathify-AI FastAPI backend.

Validates all 7 endpoints documented in API.md against PostgreSQL pathify_db.
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
        # 1. Health check
        print("\n[Test 1] Testing GET /api/health...")
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["status"] == "ok"
        assert "message" in data
        assert "timestamp" in data
        print("  -> Passed. Response:", data)

        # 2. List career roles
        print("\n[Test 2] Testing GET /api/roles...")
        res = await client.get("/api/roles")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["totalRoles"] >= 3
        roles = {r["id"]: r for r in data["roles"]}
        assert "role-1" in roles
        r1 = roles["role-1"]
        assert r1["title"] == "Full-Stack Web Developer"
        assert len(r1["requiredSkills"]) == 7
        print(f"  -> Passed. Retrieved {data['totalRoles']} roles. Role-1 skills: {r1['requiredSkills']}")

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

        # 3b. Test skill gap 404 for unknown role
        res = await client.post("/api/skill-gap", json={"roleId": "unknown-role", "skills": []})
        assert res.status_code == 404

        # 4. Create student profile (POST /api/profiles)
        print("\n[Test 4] Testing POST /api/profiles...")
        profile_payload = {
            "name": "Demo Student",
            "education": "B.Tech CSE",
            "skills": ["JavaScript", "React"],
            "targetRoleId": "role-1",
        }
        res = await client.post("/api/profiles", json=profile_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        profile = data["profile"]
        profile_id = profile["id"]
        assert profile["name"] == "Demo Student"
        assert profile["targetRoleId"] == "role-1"
        assert profile["targetRoleTitle"] == "Full-Stack Web Developer"
        assert len(profile["skills"]) == 2
        print(f"  -> Passed. Created profile ID: {profile_id}")

        # 5. Get student profile (GET /api/profiles/:id)
        print("\n[Test 5] Testing GET /api/profiles/:id...")
        res = await client.get(f"/api/profiles/{profile_id}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["profile"]["id"] == profile_id
        assert data["profile"]["name"] == "Demo Student"
        print("  -> Passed. Retrieved profile correctly.")

        # 5b. Get student profile 404 for non-existent UUID
        res = await client.get("/api/profiles/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

        # 6. Get saved profile skill gap (GET /api/profiles/:id/skill-gap)
        print("\n[Test 6] Testing GET /api/profiles/:id/skill-gap...")
        res = await client.get(f"/api/profiles/{profile_id}/skill-gap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["profileId"] == profile_id
        assert data["analysis"]["matchedCount"] == 2
        assert data["analysis"]["missingCount"] == 5
        assert data["analysis"]["matchPercentage"] == "29%"
        assert data["matchedSkills"] == ["JavaScript", "React"]
        print("  -> Passed. Profile skill gap match:", data["analysis"]["matchPercentage"])

        # 7. Get roadmap for saved profile (GET /api/profiles/:id/roadmap)
        print("\n[Test 7] Testing GET /api/profiles/:id/roadmap...")
        res = await client.get(f"/api/profiles/{profile_id}/roadmap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["profileId"] == profile_id
        assert data["summary"]["totalRequiredSkills"] == 7
        assert data["summary"]["acquiredSkillsCount"] == 2
        assert data["summary"]["missingSkillsCount"] == 5
        assert data["summary"]["totalRoadmapSteps"] == 5
        assert len(data["roadmap"]) == 5

        # Check step structure matches API.md
        step1 = data["roadmap"][0]
        assert "stepNumber" in step1
        assert "skill" in step1
        assert "learningGoal" in step1
        assert "practiceTask" in step1
        assert "estimatedDuration" in step1
        print("  -> Passed. Roadmap has 5 steps. Step 1:", step1)

    print("\n" + "=" * 60)
    print("ALL 7 ENDPOINTS SUCCESSFULLY VERIFIED AGAINST POSTGRESQL!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
