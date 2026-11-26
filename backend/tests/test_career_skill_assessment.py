"""
Test Suite for Intelligent Career Skill Assessment Engine
Pathify AI
"""
import asyncio
import sys
import uuid
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:5000"


async def run_assessment_tests():
    print("=" * 75)
    print("RUNNING INTELLIGENT CAREER SKILL ASSESSMENT ENGINE TEST SUITE")
    print("=" * 75)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 0. Test unauthenticated request is blocked with 401
        print("\n[0/7] Testing unauthenticated assessment request blocked with 401...")
        unauth_resp = await client.post(
            "/api/skill-gap",
            json={"roleId": "role-1", "skills": ["HTML & CSS", "JavaScript"]},
        )
        assert unauth_resp.status_code == 401, f"Expected 401 Unauthorized, got {unauth_resp.status_code}"
        print("  ✓ Unauthenticated assessment blocked with 401 Unauthorized.")

        # Register authenticated test user
        user_email = f"assessment_user_{uuid.uuid4().hex[:6]}@pathify.test"
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": "Assessment Student",
                "email": user_email,
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
            },
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Test basic authenticated assessment (backward compatible format)
        print("\n[1/7] Testing backward-compatible unweighted request with auth...")
        resp = await client.post(
            "/api/skill-gap",
            headers=auth_headers,
            json={"roleId": "role-1", "skills": ["HTML & CSS", "JavaScript"]},
        )
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        assert data["roleId"] == "role-1"
        assert len(data["matchedSkills"]) >= 2
        assert len(data["missingSkills"]) > 0
        assert "readinessScore" in data["analysis"]
        print(f"  ✓ Backward-compatible payload succeeded: {data['analysis']['matchPercentage']} match.")

        # 2. Test 4 proficiency levels & weighted calculation
        print("\n[2/7] Testing proficiency levels (Beginner, Intermediate, Advanced, Expert) & weights...")
        # For Full-Stack Developer:
        # Case A: Beginner in React vs Advanced in React
        resp_beginner = await client.post(
            "/api/skill-gap",
            headers=auth_headers,
            json={
                "roleId": "role-1",
                "skills": [
                    {"name": "HTML & CSS", "level": "Intermediate"},
                    {"name": "JavaScript", "level": "Intermediate"},
                    {"name": "React", "level": "Beginner"},
                ],
            },
        )
        assert resp_beginner.status_code == 200
        data_beg = resp_beginner.json()

        resp_advanced = await client.post(
            "/api/skill-gap",
            headers=auth_headers,
            json={
                "roleId": "role-1",
                "skills": [
                    {"name": "HTML & CSS", "level": "Intermediate"},
                    {"name": "JavaScript", "level": "Intermediate"},
                    {"name": "React", "level": "Advanced"},
                ],
            },
        )
        assert resp_advanced.status_code == 200
        data_adv = resp_advanced.json()

        score_beg = data_beg["analysis"]["readinessScore"]
        score_adv = data_adv["analysis"]["readinessScore"]
        assert score_adv > score_beg, f"Advanced ({score_adv}) should yield higher score than Beginner ({score_beg})"
        print(f"  ✓ Weighted proficiency score confirmed: Beginner={score_beg}% vs Advanced={score_adv}%.")

        # 3. Test Skills Needing Improvement separation
        print("\n[3/7] Testing separation of Matched, Needs Improvement, and Missing skills...")
        improving_skills = data_beg["improvingSkills"]
        detailed_improving = data_beg["detailedImproving"]
        assert "React" in improving_skills, "React should be categorized as needing improvement for Beginner"
        assert len(detailed_improving) >= 1
        assert detailed_improving[0]["gap"] == 1  # Required 3, user has 2
        print(f"  ✓ Skills needing improvement identified: {improving_skills} (Gap: {detailed_improving[0]['gap']})")
        print(f"  ✓ Matched: {data_beg['matchedSkills']}")
        print(f"  ✓ Missing: {data_beg['missingSkills']}")

        # 4. Test Missing skills priority categorization (High, Medium, Low)
        print("\n[4/7] Testing priority classification of missing skills...")
        missing_details = data_beg["detailedMissing"]
        priorities = {m["name"]: m["priority"] for m in missing_details}
        print(f"  ✓ Missing skill priorities: {priorities}")
        assert any(m["priority"] == "High" for m in missing_details), "Core requirements should be High priority"

        # 5. Test Personalized Learning Recommendations
        print("\n[5/7] Testing personalized learning recommendations generation...")
        recs = data_beg["recommendations"]
        assert len(recs) > 0, "Recommendations must be generated"
        print(f"  ✓ Generated {len(recs)} personalized recommendations.")
        first_rec = recs[0]
        print(f"    Top recommendation: [{first_rec['priority']}] {first_rec['skill']} -> {first_rec['action']} (~{first_rec['estimatedHours']} hrs)")
        assert "estimatedHours" in first_rec and first_rec["estimatedHours"] > 0

        # 6. Test Applied Project and Internship Experience bonus
        print("\n[6/7] Testing optional project & internship experience assessment...")
        resp_no_exp = await client.post(
            "/api/skill-gap",
            headers=auth_headers,
            json={"roleId": "role-1", "skills": [{"name": "JavaScript", "level": "Intermediate"}]},
        )
        resp_with_exp = await client.post(
            "/api/skill-gap",
            headers=auth_headers,
            json={
                "roleId": "role-1",
                "skills": [{"name": "JavaScript", "level": "Intermediate"}],
                "experience": {"projectsCount": 3, "internshipMonths": 4},
            },
        )
        score_no_exp = resp_no_exp.json()["analysis"]["readinessScore"]
        score_with_exp = resp_with_exp.json()["analysis"]["readinessScore"]
        exp_bonus = resp_with_exp.json()["analysis"]["experienceBonus"]
        assert exp_bonus > 0, f"Expected experience bonus > 0, got {exp_bonus}"
        assert score_with_exp > score_no_exp, f"Score with exp ({score_with_exp}) must be > without exp ({score_no_exp})"
        print(f"  ✓ Experience bonus verified: +{exp_bonus}% (Base: {score_no_exp}%, Total: {score_with_exp}%)")

        # 7. Test PostgreSQL persistence & assessment history for authenticated user
        print("\n[7/7] Testing PostgreSQL persistence and history retrieval...")
        user_email = f"assessment_user_{uuid.uuid4().hex[:6]}@pathify.test"
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": "Assessment Student",
                "email": user_email,
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
            },
        )
        assert reg_resp.status_code == 201
        token = reg_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Run assessment with auth headers
        auth_assess_resp = await client.post(
            "/api/skill-gap",
            json={
                "roleId": "role-1",
                "skills": [
                    {"name": "HTML & CSS", "level": "Advanced"},
                    {"name": "JavaScript", "level": "Advanced"},
                    {"name": "React", "level": "Intermediate"},
                ],
                "experience": {"projectsCount": 2, "internshipMonths": 2},
            },
            headers=auth_headers,
        )
        assert auth_assess_resp.status_code == 200
        auth_assess_data = auth_assess_resp.json()
        assert auth_assess_data["assessmentId"] is not None, "assessmentId must be returned for authenticated user"
        saved_id = auth_assess_data["assessmentId"]
        print(f"  ✓ Assessment persisted in PostgreSQL. Assessment ID: {saved_id}")

        # Fetch history
        hist_resp = await client.get("/api/skill-gap/history", headers=auth_headers)
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["total"] >= 1
        assert hist_data["assessments"][0]["id"] == saved_id
        print(f"  ✓ User assessment history retrieved: {hist_data['total']} record(s) found.")

        # Revisit single assessment by ID
        single_resp = await client.get(f"/api/skill-gap/assessments/{saved_id}", headers=auth_headers)
        assert single_resp.status_code == 200
        single_data = single_resp.json()
        assert single_data["roleId"] == "role-1"
        assert single_data["assessmentId"] == saved_id
        assert len(single_data["recommendations"]) > 0
        print(f"  ✓ Successfully revisited past assessment breakdown by ID.")

    print("\n" + "=" * 75)
    print(">>> ALL 7 CAREER SKILL ASSESSMENT TESTS PASSED! <<<")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_assessment_tests())
