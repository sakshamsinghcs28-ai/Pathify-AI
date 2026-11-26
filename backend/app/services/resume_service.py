"""Resume Analysis and Four-Pillar Scoring Service.

Implements:
1. Four-Pillar ATS Scoring Engine (Formatting, Content, Skills, Experience)
2. Job Description Keyword Matching Matrix
3. Missing Skills Categorization (High/Medium/Low Priority)
4. PostgreSQL Persistence and Multi-Tenant History Isolation
5. Seamless Career Roadmap Integration
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CareerRole, Skill, User, ResumeAnalysis, Roadmap, RoadmapMilestone, RoadmapTask
from backend.app.services.resume_parser import parse_resume, extract_raw_text
from backend.app.services.resume_improver import analyze_bullet_impact, BUZZWORD_REPLACEMENTS, ACTION_VERBS


def score_pillar_formatting(parsed: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Pillar 1: ATS Compatibility & Formatting (0 - 100).

    Evaluates:
    - Standard section headers (Contact, Summary, Experience, Education, Skills)
    - Contact info completeness (Email, Phone, LinkedIn/GitHub)
    - Parseable text flow & length
    """
    sections = parsed.get("sections", {})
    contact = parsed.get("contact", {})
    findings: List[Dict[str, str]] = []
    score = 30.0

    # Contact Info check (max 25 pts)
    contact_pts = 0
    if contact.get("email"):
        contact_pts += 10
        findings.append({"status": "pass", "text": "Email address properly formatted and ATS-readable."})
    else:
        findings.append({"status": "fail", "text": "Missing or unparseable email address."})

    if contact.get("phone"):
        contact_pts += 5
        findings.append({"status": "pass", "text": "Phone number detected."})
    else:
        findings.append({"status": "warn", "text": "Phone number not detected in header."})

    if contact.get("linkedin") or contact.get("github"):
        contact_pts += 10
        findings.append({"status": "pass", "text": "Online professional profile (LinkedIn/GitHub) present."})
    else:
        findings.append({"status": "warn", "text": "Add a clickable LinkedIn or GitHub portfolio URL."})

    score += contact_pts

    # Sections check (max 35 pts)
    required_sections = [
        ("experience", 15, "Work / Experience Section"),
        ("skills", 10, "Skills Section"),
        ("education", 10, "Education Section"),
    ]
    for sec_key, weight, sec_label in required_sections:
        if sections.get(sec_key):
            score += weight
            findings.append({"status": "pass", "text": f"{sec_label} detected with standard header."})
        else:
            findings.append({"status": "fail", "text": f"Missing standard '{sec_label}'. ATS scanners look for this header."})

    # Optional section bonus (max 10 pts)
    if sections.get("summary") or sections.get("projects") or sections.get("certifications"):
        score += 10
        findings.append({"status": "pass", "text": "Supporting sections (Summary / Projects / Certifications) enhance depth."})

    score = min(100.0, max(0.0, score))
    return round(score, 1), {
        "score": score,
        "name": "ATS Compatibility & Formatting",
        "description": "Evaluates section structure, parser readability, and contact completeness.",
        "findings": findings,
    }


def score_pillar_content(parsed: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Pillar 2: Content & Impact (0 - 100).

    Evaluates:
    - Action-verb usage across bullets
    - Quantifiable metrics & results
    - Reduction of vague buzzwords and passive voice
    """
    bullets = parsed.get("bullets", [])
    findings: List[Dict[str, str]] = []

    if not bullets:
        return 35.0, {
            "score": 35.0,
            "name": "Content & Quantified Impact",
            "description": "Evaluates accomplishment framing, action verbs, and quantifiable metrics.",
            "findings": [{"status": "fail", "text": "No distinct bullet points found in experience or projects."}],
        }

    total_bullets = len(bullets)
    action_verb_count = 0
    metric_count = 0
    buzzword_count = 0

    for b in bullets:
        analysis = analyze_bullet_impact(b)
        if analysis["starts_with_action_verb"]:
            action_verb_count += 1
        if analysis["has_metrics"]:
            metric_count += 1
        buzzword_count += len(analysis["detected_buzzwords"])

    action_pct = (action_verb_count / total_bullets) * 100
    metric_pct = (metric_count / total_bullets) * 100

    score = 30.0 + (action_pct * 0.35) + (metric_pct * 0.40) - (min(buzzword_count * 5, 20))
    score = min(100.0, max(15.0, score))

    if action_pct >= 70:
        findings.append({"status": "pass", "text": f"{action_verb_count} of {total_bullets} bullets ({int(action_pct)}%) start with strong active verbs."})
    else:
        findings.append({"status": "warn", "text": f"Only {int(action_pct)}% of bullets start with strong action verbs. Use verbs like 'Architected', 'Deployed', 'Engineered'."})

    if metric_pct >= 50:
        findings.append({"status": "pass", "text": f"{metric_count} of {total_bullets} bullets ({int(metric_pct)}%) include quantifiable metrics or percentages."})
    else:
        findings.append({"status": "warn", "text": f"Only {int(metric_pct)}% of bullets contain numbers or metrics. Use the XYZ formula to quantify your outcomes."})

    if buzzword_count == 0:
        findings.append({"status": "pass", "text": "Zero passive clichés or empty buzzwords detected."})
    else:
        findings.append({"status": "warn", "text": f"Detected {buzzword_count} weak phrases (e.g. 'responsible for', 'worked on'). Replace them with direct accomplishments."})

    return round(score, 1), {
        "score": round(score, 1),
        "name": "Content & Quantified Impact",
        "description": "Evaluates accomplishment framing, action verbs, and quantifiable metrics.",
        "findings": findings,
        "metrics_percentage": round(metric_pct, 1),
        "action_verb_percentage": round(action_pct, 1),
        "total_bullets_analyzed": total_bullets,
    }


def score_pillar_skills(
    extracted_skills: List[str],
    role: Optional[CareerRole],
) -> Tuple[float, Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pillar 3: Skills & Technical Proficiency (0 - 100).

    Matches extracted skills against the target role requirements in PostgreSQL.
    Categorizes skills into matched and missing with priority tags.
    """
    matched_list: List[Dict[str, Any]] = []
    missing_list: List[Dict[str, Any]] = []
    findings: List[Dict[str, str]] = []

    extracted_lower = {s.lower(): s for s in extracted_skills}

    if not role or not role.skill_requirements:
        # Fallback when no role is selected: score based on technical skills density
        count = len(extracted_skills)
        score = min(100.0, max(20.0, count * 7.5))
        findings.append({"status": "pass" if count >= 8 else "warn", "text": f"Detected {count} recognized technical skills."})
        return round(score, 1), {
            "score": round(score, 1),
            "name": "Skills & Technical Coverage",
            "description": "Assesses presence of high-demand technical capabilities and tools.",
            "findings": findings,
        }, [{"name": s, "category": "Technical"} for s in extracted_skills], []

    total_possible_score = 0.0
    earned_score = 0.0

    for req in role.skill_requirements:
        skill_name = req.skill.name
        is_required = req.importance == "required"
        weight = 1.5 if is_required else 1.0
        total_possible_score += weight

        if skill_name.lower() in extracted_lower:
            earned_score += weight
            matched_list.append({
                "name": skill_name,
                "importance": req.importance,
                "category": req.skill.category,
                "required_level": req.required_level,
            })
        else:
            priority = "High" if is_required or req.required_level >= 4 else ("Medium" if req.required_level == 3 else "Low")
            missing_list.append({
                "name": skill_name,
                "importance": req.importance,
                "priority": priority,
                "category": req.skill.category,
                "required_level": req.required_level,
                "learning_goal": f"Master {skill_name} core paradigms and production patterns",
            })

    score = (earned_score / total_possible_score * 100) if total_possible_score > 0 else 50.0
    score = min(100.0, max(0.0, score))

    if score >= 75:
        findings.append({"status": "pass", "text": f"Strong alignment: matched {len(matched_list)} of {len(role.skill_requirements)} key industry skills for {role.title}."})
    elif score >= 50:
        findings.append({"status": "warn", "text": f"Moderate skill coverage ({len(matched_list)}/{len(role.skill_requirements)}). Missing {len(missing_list)} critical requirements."})
    else:
        findings.append({"status": "fail", "text": f"Low skill alignment: missing {len(missing_list)} key technical competencies for {role.title}."})

    return round(score, 1), {
        "score": round(score, 1),
        "name": "Skills & Technical Coverage",
        "description": f"Benchmarks extracted skills directly against verified {role.title} requirements.",
        "findings": findings,
        "matched_count": len(matched_list),
        "missing_count": len(missing_list),
    }, matched_list, missing_list


def score_pillar_experience(
    parsed: Dict[str, Any],
    role: Optional[CareerRole],
) -> Tuple[float, Dict[str, Any]]:
    """Pillar 4: Relevance & Experience Alignment (0 - 100).

    Assesses career trajectory, project depth, and industry relevance.
    """
    sections = parsed.get("sections", {})
    exp_text = sections.get("experience", "")
    proj_text = sections.get("projects", "")
    findings: List[Dict[str, str]] = []

    words = len((exp_text + " " + proj_text).split())
    score = 40.0

    if words >= 250:
        score += 30
        findings.append({"status": "pass", "text": "Thorough experience and project narrative detected."})
    elif words >= 100:
        score += 20
        findings.append({"status": "warn", "text": "Experience section is brief. Detail key deliverables and technologies."})
    else:
        findings.append({"status": "fail", "text": "Very limited experience text detected."})

    # Check for dates / tenure indicator
    has_dates = bool(re.search(r"\b(20\d\d|19\d\d|present|current)\b", exp_text, re.IGNORECASE))
    if has_dates:
        score += 15
        findings.append({"status": "pass", "text": "Clear chronological employment timelines detected."})
    else:
        findings.append({"status": "warn", "text": "Timeline dates not cleanly recognized in work history."})

    # Target role title keyword match
    if role and role.title.lower() in (exp_text + " " + proj_text).lower():
        score += 15
        findings.append({"status": "pass", "text": f"Explicit references to target role domain ({role.title}) found in experience."})

    score = min(100.0, max(20.0, score))
    return round(score, 1), {
        "score": round(score, 1),
        "name": "Relevance & Career Trajectory",
        "description": "Evaluates chronological progression, experience depth, and domain relevance.",
        "findings": findings,
    }


def compute_jd_match(
    resume_text: str,
    job_description: str,
) -> Dict[str, Any]:
    """Compare resume text against a specific target Job Description text.

    Extracts keywords and calculates overlap percentage.
    """
    if not job_description or not job_description.strip():
        return {
            "match_percentage": None,
            "matched_keywords": [],
            "missing_keywords": [],
            "summary": "No job description provided for direct comparison.",
        }

    # Extract alphanumeric words > 3 characters from JD
    stop_words = {
        "with", "from", "that", "this", "will", "have", "been", "were", "what",
        "their", "about", "which", "would", "there", "these", "other", "into",
        "more", "some", "time", "than", "them", "then", "only", "come", "work",
        "experience", "years", "skills", "ability", "strong", "understanding",
        "knowledge", "responsible", "working", "team", "requirements", "candidate",
    }

    jd_words = re.findall(r"\b[a-zA-Z]{3,}\b", job_description.lower())
    keyword_freq: Dict[str, int] = {}
    for w in jd_words:
        if w not in stop_words and len(w) > 3:
            keyword_freq[w] = keyword_freq.get(w, 0) + 1

    # Top keywords in JD (ordered by frequency)
    top_jd_keywords = sorted(keyword_freq.items(), key=lambda item: item[1], reverse=True)[:30]
    total_jd_keywords = len(top_jd_keywords)

    if total_jd_keywords == 0:
        return {"match_percentage": 100.0, "matched_keywords": [], "missing_keywords": [], "summary": "Job description text too short for meaningful keyword analysis."}

    resume_text_lower = resume_text.lower()
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []

    for kw, count in top_jd_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", resume_text_lower):
            matched_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    match_pct = round((len(matched_keywords) / total_jd_keywords) * 100, 1)

    summary = (
        f"Matched {len(matched_keywords)} of {total_jd_keywords} high-frequency job keywords ({match_pct}%). "
        f"Consider incorporating missing keywords like '{', '.join(missing_keywords[:4])}'."
    )

    return {
        "match_percentage": match_pct,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "summary": summary,
    }


def analyze_resume_data(
    raw_text: str,
    filename: str,
    file_size_bytes: int,
    file_type: str,
    role: Optional[CareerRole] = None,
    job_description: Optional[str] = None,
    reference_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute complete 4-pillar analysis and job description matching."""
    parsed = parse_resume(raw_text, reference_skills=reference_skills)

    f_score, f_data = score_pillar_formatting(parsed)
    c_score, c_data = score_pillar_content(parsed)
    s_score, s_data, matched_skills, missing_skills = score_pillar_skills(parsed["extracted_skills"], role)
    e_score, e_data = score_pillar_experience(parsed, role)

    # Weighted Overall Score
    overall_score = round((0.25 * f_score) + (0.30 * c_score) + (0.25 * s_score) + (0.20 * e_score), 1)

    # Job Description Matching
    jd_result = compute_jd_match(raw_text, job_description or "")

    # Top recommendations
    recommendations: List[Dict[str, str]] = []
    if c_score < 70:
        recommendations.append({
            "pillar": "Content & Impact",
            "priority": "High",
            "text": "Quantify accomplishments in your bullets using the XYZ formula (e.g. 'Increased speed by 35% by implementing Redis caching').",
        })
    if s_score < 75 and missing_skills:
        top_missing = [m["name"] for m in missing_skills[:3]]
        recommendations.append({
            "pillar": "Technical Skills",
            "priority": "High",
            "text": f"Add missing core skills for {role.title if role else 'your target role'}: {', '.join(top_missing)}.",
        })
    if f_score < 80:
        recommendations.append({
            "pillar": "ATS Compatibility",
            "priority": "Medium",
            "text": "Ensure clean section headers (Summary, Experience, Education, Skills) and include a direct LinkedIn profile link.",
        })
    if jd_result.get("missing_keywords"):
        recommendations.append({
            "pillar": "Job Match",
            "priority": "Medium",
            "text": f"Incorporate target job description keywords: {', '.join(jd_result['missing_keywords'][:4])}.",
        })

    return {
        "filename": filename,
        "file_size_bytes": file_size_bytes,
        "file_type": file_type,
        "raw_text": raw_text,
        "parsed_data": parsed,
        "overall_score": overall_score,
        "pillar_formatting_score": f_score,
        "pillar_content_score": c_score,
        "pillar_skills_score": s_score,
        "pillar_experience_score": e_score,
        "score_breakdown": {
            "formatting": f_data,
            "content": c_data,
            "skills": s_data,
            "experience": e_data,
        },
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "jd_match": jd_result,
        "improvement_recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Database Persistence Operations
# ---------------------------------------------------------------------------

async def save_resume_analysis(
    session: AsyncSession,
    user_id: uuid.UUID,
    analysis_dict: Dict[str, Any],
    role_id: Optional[uuid.UUID] = None,
    job_description: Optional[str] = None,
) -> ResumeAnalysis:
    """Persist analyzed resume into PostgreSQL with multi-tenant user scoping."""
    analysis_record = ResumeAnalysis(
        user_id=user_id,
        role_id=role_id,
        filename=analysis_dict["filename"],
        file_size_bytes=analysis_dict["file_size_bytes"],
        file_type=analysis_dict["file_type"],
        raw_text=analysis_dict["raw_text"],
        parsed_data=analysis_dict["parsed_data"],
        target_job_description=job_description,
        overall_score=analysis_dict["overall_score"],
        pillar_formatting_score=analysis_dict["pillar_formatting_score"],
        pillar_content_score=analysis_dict["pillar_content_score"],
        pillar_skills_score=analysis_dict["pillar_skills_score"],
        pillar_experience_score=analysis_dict["pillar_experience_score"],
        score_breakdown=analysis_dict["score_breakdown"],
        matched_skills=analysis_dict["matched_skills"],
        missing_skills=analysis_dict["missing_skills"],
        jd_match_percentage=analysis_dict["jd_match"].get("match_percentage"),
        improvement_recommendations=analysis_dict["improvement_recommendations"],
    )
    session.add(analysis_record)
    await session.commit()
    await session.refresh(analysis_record)
    return analysis_record


async def get_user_resume_history(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 15,
) -> List[ResumeAnalysis]:
    """Retrieve history of resume analyses for the authenticated user."""
    stmt = (
        select(ResumeAnalysis)
        .options(selectinload(ResumeAnalysis.role))
        .where(ResumeAnalysis.user_id == user_id)
        .order_by(desc(ResumeAnalysis.created_at))
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_resume_analysis_by_id(
    session: AsyncSession,
    analysis_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[ResumeAnalysis]:
    """Retrieve a single resume analysis verifying ownership."""
    stmt = (
        select(ResumeAnalysis)
        .options(selectinload(ResumeAnalysis.role))
        .where(ResumeAnalysis.id == analysis_id, ResumeAnalysis.user_id == user_id)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def delete_resume_analysis(
    session: AsyncSession,
    analysis_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a resume analysis verifying ownership."""
    stmt = delete(ResumeAnalysis).where(
        ResumeAnalysis.id == analysis_id,
        ResumeAnalysis.user_id == user_id,
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount > 0


async def sync_missing_skills_to_roadmap(
    session: AsyncSession,
    analysis: ResumeAnalysis,
    user: User,
) -> Dict[str, Any]:
    """Integrate missing skills from resume analysis into the user's active Roadmap."""
    if not analysis.role_id:
        raise ValueError("Cannot sync to roadmap: No target role was assigned to this resume analysis.")

    # Find or create active roadmap for role
    stmt = (
        select(Roadmap)
        .options(selectinload(Roadmap.milestones).selectinload(RoadmapMilestone.tasks))
        .where(Roadmap.user_id == user.id, Roadmap.role_id == analysis.role_id)
    )
    res = await session.execute(stmt)
    roadmap = res.scalar_one_or_none()

    if not roadmap:
        # Load role
        role_stmt = select(CareerRole).where(CareerRole.id == analysis.role_id)
        role_res = await session.execute(role_stmt)
        role = role_res.scalar_one_or_none()
        role_title = role.title if role else "Target Career"

        roadmap = Roadmap(
            user_id=user.id,
            role_id=analysis.role_id,
            title=f"Personalized Roadmap: {role_title}",
            status="active",
        )
        session.add(roadmap)
        await session.flush()
        existing_titles = set()
        current_max_order = 0
    else:
        # Get existing milestone titles to avoid duplicate milestones
        existing_titles = {m.title.lower() for m in (roadmap.milestones or [])}
        current_max_order = max([m.sequence_order for m in (roadmap.milestones or [])], default=0)

    added_skills: List[str] = []

    for idx, missing in enumerate(analysis.missing_skills):
        skill_name = missing.get("name", "")
        if not skill_name or skill_name.lower() in existing_titles:
            continue

        current_max_order += 1
        milestone = RoadmapMilestone(
            roadmap_id=roadmap.id,
            title=skill_name,
            sequence_order=current_max_order,
        )
        session.add(milestone)
        await session.flush()

        # Add initial task
        task = RoadmapTask(
            milestone_id=milestone.id,
            title=f"Master foundational concepts and tools for {skill_name}",
            description=f"Close resume gap for {skill_name} identified in ATS intelligence analysis.",
            sequence_order=1,
            estimated_hours=10,
            status="pending",
        )
        session.add(task)
        added_skills.append(skill_name)

    await session.commit()
    return {
        "success": True,
        "roadmap_id": str(roadmap.id),
        "added_milestones": added_skills,
        "message": f"Successfully synced {len(added_skills)} missing skills into your personalized roadmap.",
    }
