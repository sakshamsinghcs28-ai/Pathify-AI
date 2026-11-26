"""AI Resume Improvement Studio Service.

Implements:
- Google-style XYZ Formula ("Accomplished [X] as measured by [Y] by doing [Z]")
- Action verb suggestions categorized by function
- Fluff / Buzzword detection and replacements
- Bullet point impact analysis & automated rewrite generation
- Role-specific professional summary generator
"""

import re
from typing import Any, Dict, List, Optional


# Action verbs organized by impact category
ACTION_VERBS = {
    "Leadership & Ownership": [
        "Architected", "Spearheaded", "Directed", "Orchestrated", "Pioneered",
        "Championed", "Led", "Overhauled", "Mobilized", "Mentored",
    ],
    "Engineering & Development": [
        "Engineered", "Developed", "Implemented", "Constructed", "Deployed",
        "Refactored", "Automated", "Standardized", "Configured", "Integrated",
    ],
    "Optimization & Performance": [
        "Accelerated", "Optimized", "Enhanced", "Streamlined", "Maximized",
        "Reduced", "Consolidated", "Eliminated", "Mitigated", "Scaled",
    ],
    "Data & Analytics": [
        "Analyzed", "Benchmarked", "Synthesized", "Quantified", "Forecasted",
        "Discovered", "Modeled", "Evaluated", "Validated", "Audited",
    ],
    "Collaboration & Impact": [
        "Co-developed", "Collaborated", "Partnered", "Negotiated", "Delivered",
        "Standardized", "Empowered", "Transformed", "Published", "Resolved",
    ],
}

# Weak Buzzwords & Fluff
BUZZWORD_REPLACEMENTS = {
    "responsible for": ("Spearheaded / Delivered", "Weak passive phrase. State directly what you built or accomplished."),
    "worked on": ("Engineered / Developed", "Vague effort. Specify your specific ownership and technical contribution."),
    "handled": ("Managed / Resolved", "Reactive verb. Highlight proactive leadership or technical resolution."),
    "helped with": ("Collaborated to deliver / Co-developed", "Minimizes contribution. State team collaboration with clear outcome."),
    "duties included": ("Executed / Oversaw", "Job description phrasing. Replace with concrete accomplishments."),
    "hard-working": ("Demonstrated by track record", "Subjective adjective. Prove through quantifiable accomplishments."),
    "team player": ("Cross-functional collaborator", "Cliché. Describe real cross-team alignment and deliverables."),
    "fast learner": ("Rapidly mastered and deployed", "Overused. Demonstrate by mentioning new tech adopted quickly."),
    "detail-oriented": ("Ensured 99.9% accuracy / test coverage", "Replace with precise metrics or quality benchmarks."),
    "passionate": ("Demonstrated through open-source contributions", "Show, don't tell."),
}

# Metric Detection Regex (Percentages, Numbers, Currencies, Multipliers)
METRIC_PATTERNS = [
    re.compile(r"\b\d+%(?=[^a-zA-Z]|$)"),                     # 25%, 42%.
    re.compile(r"\b\d+x(?=[^a-zA-Z]|$)", re.IGNORECASE),       # 2x, 10x
    re.compile(r"\$\d+(?:,\d+)*(?:\.\d+)?\b"),   # $50,000
    re.compile(r"\b\d+\s*(?:ms|seconds|minutes|hours|days|weeks|months|years)\b", re.IGNORECASE),  # 200ms
    re.compile(r"\b\d+\s*(?:users|clients|customers|students|requests|queries|nodes|servers)\b", re.IGNORECASE),
    re.compile(r"\b(?:reduced|increased|improved|boosted|grew|saved)\s+by\s+\d+", re.IGNORECASE),
]


def analyze_bullet_impact(bullet_text: str) -> Dict[str, Any]:
    """Analyze a single bullet point for action verbs, quantifiable metrics, and buzzwords."""
    bullet = bullet_text.strip()
    words = bullet.split()

    # Check for starting action verb
    first_word = re.sub(r"[^\w]", "", words[0]) if words else ""
    all_action_verbs = [v.lower() for sublist in ACTION_VERBS.values() for v in sublist]
    starts_with_action_verb = first_word.lower() in all_action_verbs

    # Check for quantifiable metrics
    has_metrics = any(pattern.search(bullet) for pattern in METRIC_PATTERNS)
    metric_matches = []
    for pat in METRIC_PATTERNS:
        metric_matches.extend(pat.findall(bullet))

    # Check for buzzwords
    detected_buzzwords = []
    for buzzword, (replacement, advice) in BUZZWORD_REPLACEMENTS.items():
        if re.search(r"\b" + re.escape(buzzword) + r"\b", bullet, re.IGNORECASE):
            detected_buzzwords.append({
                "buzzword": buzzword,
                "replacement": replacement,
                "advice": advice,
            })

    # Length & Structure score
    length_ok = 10 <= len(words) <= 30
    length_feedback = "Good length."
    if len(words) < 10:
        length_feedback = "Too brief. Elaborate on the tools used and final outcome."
    elif len(words) > 30:
        length_feedback = "Too verbose. Trim into a punchy single sentence focusing on result."

    # Impact Score (0 - 100)
    score = 40  # base
    if starts_with_action_verb:
        score += 25
    if has_metrics:
        score += 25
    if not detected_buzzwords:
        score += 10
    else:
        score -= 10
    score = max(10, min(100, score))

    return {
        "original_text": bullet,
        "score": score,
        "starts_with_action_verb": starts_with_action_verb,
        "has_metrics": has_metrics,
        "metric_matches": metric_matches,
        "detected_buzzwords": detected_buzzwords,
        "word_count": len(words),
        "length_feedback": length_feedback,
    }


def generate_xyz_rewrites(bullet_text: str, target_role: Optional[str] = None) -> List[Dict[str, str]]:
    """Generate 2-3 improved versions of a bullet point adhering to the XYZ formula:

    'Accomplished [X] as measured by [Y], by doing [Z]'
    """
    clean_bullet = bullet_text.strip()
    # Remove leading passive words
    clean_action = re.sub(r"^(?:responsible for|worked on|handled|helped with|assisted in|participated in)\s+", "", clean_bullet, flags=re.IGNORECASE)

    # Pick top contextual action verbs
    role_lower = (target_role or "").lower()
    if "data" in role_lower or "analyst" in role_lower:
        v1, v2, v3 = "Engineered", "Optimized", "Synthesized"
        metric1, metric2 = "yielding a 35% reduction in query latency", "automating daily reporting for 15+ business stakeholders"
    elif "ai" in role_lower or "machine" in role_lower or "ml" in role_lower:
        v1, v2, v3 = "Architected", "Fine-tuned", "Deployed"
        metric1, metric2 = "improving F1 inference accuracy by 18%", "cutting GPU compute costs by $4,500/month"
    else:
        v1, v2, v3 = "Architected", "Engineered", "Streamlined"
        metric1, metric2 = "boosting end-to-end performance by 40%", "supporting over 10,000+ daily active user interactions"

    rewrites = [
        {
            "label": "High-Impact & Metric Driven (Recommended)",
            "text": f"{v1} {clean_action}, {metric1} by implementing modern modular architecture and automated testing pipelines.",
            "formula_breakdown": {
                "action_z": f"Implemented modern modular architecture and automated testing pipelines",
                "accomplished_x": clean_action,
                "measured_by_y": metric1,
            },
        },
        {
            "label": "Scale & Efficiency Focus",
            "text": f"{v2} {clean_action}, {metric2} across distributed cloud infrastructure.",
            "formula_breakdown": {
                "action_z": "Standardized deployment across distributed cloud infrastructure",
                "accomplished_x": clean_action,
                "measured_by_y": metric2,
            },
        },
        {
            "label": "Concise Technical Delivery",
            "text": f"{v3} end-to-end {clean_action} utilizing industry best practices, slashing defect resolution time by 25%.",
            "formula_breakdown": {
                "action_z": "Applied industry best practices",
                "accomplished_x": f"end-to-end {clean_action}",
                "measured_by_y": "slashed defect resolution time by 25%",
            },
        },
    ]

    return rewrites


def generate_professional_summary(
    full_name: Optional[str],
    target_role_title: str,
    top_skills: List[str],
    years_experience: Optional[int] = None,
) -> str:
    """Generate a high-converting, ATS-friendly professional summary tailored for the target role."""
    name_clause = f"{full_name or 'Results-driven tech professional'} is a" if full_name else "Results-driven"
    skills_str = ", ".join(top_skills[:5]) if top_skills else "modern software engineering and cloud infrastructure"
    exp_str = f"with {years_experience}+ years of hands-on experience" if years_experience and years_experience > 0 else "with a strong background"

    summary = (
        f"{name_clause} passionate {target_role_title} {exp_str} designing, developing, and deploying scalable solutions. "
        f"Proficient across core technologies including {skills_str}. "
        f"Proven track record of delivering high-impact features, optimizing performance, and translating complex business requirements into robust, production-grade applications."
    )
    return summary
