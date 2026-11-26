"""Resume Text Extraction and Structural Section Parsing Service.

Supports:
- PDF extraction via pypdf
- DOCX extraction via python-docx
- Plain text / UTF-8 extraction
- Section header detection (Experience, Education, Skills, Projects, Summary)
- Contact information extraction (Email, Phone, LinkedIn, GitHub, Portfolio)
- Technical skill entity extraction matching Pathify-AI standardized skills
"""

import io
import re
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import docx


# Standardized Section Header Keywords
SECTION_PATTERNS = {
    "summary": re.compile(
        r"^(professional\s+summary|summary|profile|about\s+me|objective|career\s+objective)\b",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(work\s+experience|professional\s+experience|experience|employment\s+history|career\s+history)\b",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^(education|academic\s+background|academic\s+history|qualifications)\b",
        re.IGNORECASE,
    ),
    "skills": re.compile(
        r"^(skills|technical\s+skills|core\s+competencies|technologies|proficiencies|skills\s+&\s+tools)\b",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(projects|personal\s+projects|key\s+projects|portfolio\s+projects|academic\s+projects)\b",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"^(certifications|licenses|courses|awards\s+&\s+certifications|achievements)\b",
        re.IGNORECASE,
    ),
}

# Regex for Contact Info
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
LINKEDIN_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/([a-zA-Z0-9_-]+)", re.IGNORECASE)
GITHUB_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_-]+)", re.IGNORECASE)
PORTFOLIO_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.(?:dev|me|io|com|org|tech|app))(?:\/[^\s]*)?", re.IGNORECASE)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    text_chunks: List[str] = []
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    except Exception as exc:
        raise ValueError("Failed to extract text from PDF. The document may be corrupted or password-protected.") from exc
    return "\n\n".join(text_chunks)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx."""
    text_chunks: List[str] = []
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                text_chunks.append(text)
        # Also check tables in docx
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_chunks.append(row_text)
    except Exception as exc:
        raise ValueError("Failed to extract text from DOCX. The document may be corrupted or unsupported.") from exc
    return "\n".join(text_chunks)


def extract_raw_text(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Router to extract raw text based on filename extension and content-type."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf") or "pdf" in content_type:
        text = extract_text_from_pdf(file_bytes)
    elif lower_name.endswith(".docx") or "wordprocessingml" in content_type or lower_name.endswith(".doc"):
        text = extract_text_from_docx(file_bytes)
    else:
        # Default fallback to UTF-8 text
        try:
            text = file_bytes.decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError("Unsupported file format or unreadable text encoding. Please upload a standard text, PDF, or DOCX document.") from exc

    clean_text = re.sub(r"\r\n|\r", "\n", text)
    if not clean_text.strip():
        raise ValueError("The uploaded document contains no readable text. It may be an image-only scan or corrupted.")
    return clean_text.strip()


def extract_contact_info(text: str, lines: List[str]) -> Dict[str, Any]:
    """Extract candidate name, email, phone, and links from header lines."""
    contact: Dict[str, Any] = {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
        "location": "",
    }

    # Email
    email_match = EMAIL_REGEX.search(text)
    if email_match:
        contact["email"] = email_match.group(0).strip()

    # Phone
    phone_match = PHONE_REGEX.search(text)
    if phone_match:
        contact["phone"] = phone_match.group(0).strip()

    # LinkedIn
    li_match = LINKEDIN_REGEX.search(text)
    if li_match:
        contact["linkedin"] = li_match.group(0).strip()

    # GitHub
    gh_match = GITHUB_REGEX.search(text)
    if gh_match:
        contact["github"] = gh_match.group(0).strip()

    # Candidate Name heuristic: First non-empty line that does not contain email/phone/url
    for line in lines[:8]:
        trimmed = line.strip()
        if not trimmed:
            continue
        if "@" in trimmed or "http" in trimmed or "linkedin" in trimmed or "github" in trimmed:
            continue
        if len(trimmed.split()) in [2, 3, 4] and not any(char.isdigit() for char in trimmed):
            # Likely full name
            contact["name"] = trimmed
            break

    return contact


def split_into_sections(raw_text: str) -> Dict[str, str]:
    """Split raw text into logical resume sections using heading detection."""
    lines = [line.strip() for line in raw_text.split("\n")]
    sections: Dict[str, List[str]] = {
        "header": [],
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
        "other": [],
    }

    current_section = "header"

    for line in lines:
        if not line:
            continue

        # Check if line matches a known section header
        cleaned_line = re.sub(r"[^\w\s]", "", line).strip()
        matched_section: Optional[str] = None
        for sec_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(cleaned_line):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
            continue

        sections[current_section].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def extract_bullet_points(section_text: str) -> List[str]:
    """Extract individual bullet points or responsibility items from section text."""
    if not section_text:
        return []

    raw_lines = section_text.split("\n")
    bullets: List[str] = []
    current_bullet: List[str] = []

    bullet_prefixes = ("•", "-", "*", "–", "—", "▪", "▫", "►", "✓")

    for line in raw_lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        is_bullet_start = any(line_stripped.startswith(p) for p in bullet_prefixes) or re.match(r"^\d+\.", line_stripped)

        if is_bullet_start:
            if current_bullet:
                bullets.append(" ".join(current_bullet).strip())
                current_bullet = []
            # Strip bullet symbol
            cleaned = re.sub(r"^[•\-*–—▪▫►✓\d\.]+\s*", "", line_stripped)
            current_bullet.append(cleaned)
        else:
            if current_bullet:
                current_bullet.append(line_stripped)
            else:
                # If no bullets exist, treat lines of reasonable length as items
                if len(line_stripped) > 20:
                    bullets.append(line_stripped)

    if current_bullet:
        bullets.append(" ".join(current_bullet).strip())

    return bullets


def extract_skills_from_text(raw_text: str, reference_skills: List[str]) -> List[str]:
    """Identify skills present in the resume by matching against Pathify-AI's reference skills.

    Performs case-insensitive word-boundary token matching.
    """
    found_skills: List[str] = []
    text_lower = f" {raw_text.lower()} "

    for skill in reference_skills:
        skill_lower = skill.lower()
        # Escape special chars for regex like C++, .NET, React.js
        pattern = r"(?:\b|\s)" + re.escape(skill_lower) + r"(?:\b|\s|,|\.)"
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return sorted(list(set(found_skills)))


def parse_resume(
    raw_text: str,
    reference_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute complete structured parsing of raw resume text."""
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    sections = split_into_sections(raw_text)
    contact = extract_contact_info(raw_text, lines)
    bullets = extract_bullet_points(sections.get("experience", "") + "\n" + sections.get("projects", ""))

    known_skills = reference_skills or [
        "JavaScript", "TypeScript", "Python", "HTML & CSS", "React", "Node.js", "Express.js",
        "MongoDB", "PostgreSQL", "SQL", "Git & GitHub", "Docker", "AWS", "Machine Learning",
        "Deep Learning", "PyTorch", "FastAPI", "Pandas", "Scikit-Learn", "Power BI", "Tableau",
        "REST APIs", "CI/CD", "Linux", "Data Structures", "Algorithms", "Redux", "GraphQL",
    ]

    extracted_skills = extract_skills_from_text(raw_text, known_skills)

    return {
        "contact": contact,
        "sections": {
            "summary": sections.get("summary", ""),
            "experience": sections.get("experience", ""),
            "education": sections.get("education", ""),
            "skills": sections.get("skills", ""),
            "projects": sections.get("projects", ""),
            "certifications": sections.get("certifications", ""),
        },
        "bullets": bullets,
        "extracted_skills": extracted_skills,
        "word_count": len(raw_text.split()),
        "line_count": len(lines),
    }
