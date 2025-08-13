from typing import List, Optional
from pydantic import BaseModel, Field
import os

try:
    from openai import OpenAI  # type: ignore
    openai_available = True
except Exception:  # pragma: no cover
    OpenAI = None
    openai_available = False


class CoverLetter(BaseModel):
    title: str = Field(..., description="Short title or focus of the cover letter")
    content: str = Field(..., description="Full cover letter text in plain paragraphs")


class CoverLetterBundle(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    versions: List[CoverLetter]
    notes: Optional[str] = None


class CoverLetterGenerator:
    """Generate up to 3 tailored cover letter versions using OpenAI function calling.
    Falls back to a simple template if OpenAI is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if openai_available and self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def generate(self, resume_text: str, job_description: str, job_title: Optional[str] = None,
                 company: Optional[str] = None, max_versions: int = 3) -> CoverLetterBundle:
        import re
        max_versions = 3  # enforce exactly 3 as requested

        # Simple metadata inference
        if not job_title or not company:
            inferred_title, inferred_company = self._infer_job_metadata(job_description)
            job_title = job_title or inferred_title
            company = company or inferred_company

        candidate_email = self._extract_email(resume_text)
        candidate_phone = self._extract_phone(resume_text)
        candidate_name = self._extract_name(resume_text)

        # Fallback if OpenAI client is not initialized
        if not self.client:
            # Fallback simple versions
            versions = []
            for i in range(max_versions):
                versions.append(CoverLetter(
                    title=f"Version {i+1}",
                    content=self._fallback_template(resume_text, job_description, job_title, company)
                ))
            return CoverLetterBundle(job_title=job_title, company=company, versions=versions,
                                     notes="OpenAI not configured; generated fallback templates.")

        # Function schema
        func_schema = {
            "name": "produce_cover_letters",
            "description": "Produce up to 3 concise professional cover letters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "versions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["title", "content"]
                        },
                        "minItems": 1,
                        "maxItems": max_versions
                    }
                },
                "required": ["versions"]
            }
        }

        system_msg = (
            "You are a helpful assistant that writes ATS-friendly, professional, fully-complete cover letters. "
            "Rules: 1) No placeholders like [Your Name] or [Hiring Manager]; 2) Include candidate email and phone if provided; "
            "3) Address the specific company and job title; 4) 3 distinct versions with different emphasis/tone; "
            "5) Keep content specific and succinct; no emojis."
        )
        user_msg = (
            "CANDIDATE RESUME (extract candidate name, email, phone):\n" + resume_text[:4000] + "\n\n"
            "JOB DESCRIPTION (extract job title/company if missing):\n" + job_description[:4000] + "\n\n"
            f"Known Job Title: {job_title or ''}\nKnown Company: {company or ''}\n" \
            f"Known Candidate Name: {candidate_name or ''}\nKnown Candidate Email: {candidate_email or ''}\nKnown Candidate Phone: {candidate_phone or ''}\n\n" \
            f"Produce exactly {max_versions} complete cover letter versions. "
            "Each version must be a ready-to-send letter including greeting and closing. "
            "Do not invent data not present in resume; if a specific item is unknown, omit it rather than using placeholders."
        )

        try:
            # Use Chat Completions with tool (function) calling
            resp = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": func_schema,
                    }
                ],
                tool_choice={"type": "function", "function": {"name": "produce_cover_letters"}},
            )

            # Try to parse tool call arguments first
            data = {}
            try:
                tool_calls = resp.choices[0].message.tool_calls or []
                if tool_calls:
                    args = tool_calls[0].function.arguments or "{}"
                    import json as _json
                    data = _json.loads(args)
                else:
                    # Fallback: attempt to parse content JSON
                    content = resp.choices[0].message.content or "{}"
                    import json as _json
                    data = _json.loads(content)
            except Exception:
                data = {"versions": []}

            versions = [CoverLetter(**v) for v in data.get("versions", [])]
            # Enforce exactly max_versions by trimming or duplicating last variant if needed
            if len(versions) > max_versions:
                versions = versions[:max_versions]
            elif len(versions) < max_versions:
                while len(versions) < max_versions:
                    # duplicate last with slight title suffix
                    base = versions[-1] if versions else CoverLetter(title="Version 1", content=self._fallback_template(resume_text, job_description, job_title, company, candidate_email, candidate_phone, candidate_name))
                    idx = len(versions) + 1
                    versions.append(CoverLetter(title=f"{base.title} (Alt {idx})", content=base.content))
            if not versions:
                versions = [CoverLetter(title="Version 1",
                                        content=self._fallback_template(resume_text, job_description, job_title, company, candidate_email, candidate_phone, candidate_name))]
            return CoverLetterBundle(job_title=job_title, company=company, versions=versions)
        except Exception:
            versions = []
            for i in range(max_versions):
                versions.append(CoverLetter(
                    title=f"Version {i+1}",
                    content=self._fallback_template(resume_text, job_description, job_title, company, candidate_email, candidate_phone, candidate_name)
                ))
            return CoverLetterBundle(job_title=job_title, company=company, versions=versions,
                                     notes="OpenAI error; fallback used.")

    def _fallback_template(self, resume_text: str, job_description: str, job_title: Optional[str], company: Optional[str], email: Optional[str], phone: Optional[str], name: Optional[str]) -> str:
        header = []
        if email:
            header.append(email)
        if phone:
            header.append(phone)
        header_line = (" | ".join(header)) if header else ""
        return (
            (header_line + "\n\n" if header_line else "") +
            f"Dear Hiring Manager,\n\n"
            f"I am excited to apply for the {job_title or 'position'} at {company or 'your company'}. "
            f"My background aligns with your needs, and I bring strong impact as evidenced in my resume. "
            f"I look forward to the opportunity to contribute to your team.\n\n"
            f"Sincerely,\n"
            f"{name or ''}"
        )

    def _infer_job_metadata(self, job_description: str) -> tuple[Optional[str], Optional[str]]:
        import re
        text = job_description or ""
        # crude patterns
        title = None
        company = None
        m = re.search(r"(?i)\btitle\s*:\s*(.+)", text)
        if m:
            title = m.group(1).strip().split("\n")[0][:120]
        m2 = re.search(r"(?i)\bcompany\s*:\s*(.+)", text)
        if m2:
            company = m2.group(1).strip().split("\n")[0][:120]
        # fallback: look for lines like 'Senior X at Y'
        if not title:
            m3 = re.search(r"(?i)\b(Senior|Lead|Principal|Staff|Junior)?\s*[A-Za-z][A-Za-z\s\-/]{2,40}\b", text)
            if m3:
                title = m3.group(0).strip()[:120]
        if not company:
            m4 = re.search(r"(?i)\bat\s+([A-Z][A-Za-z0-9&.,\-\s]{2,60})", text)
            if m4:
                company = m4.group(1).strip().rstrip('.')[:120]
        return title, company

    def _extract_email(self, resume_text: str) -> Optional[str]:
        import re
        m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text or "")
        return m.group(0) if m else None

    def _extract_phone(self, resume_text: str) -> Optional[str]:
        import re
        m = re.search(r"\+?\d[\d\s().-]{7,}\d", resume_text or "")
        return m.group(0) if m else None

    def _extract_name(self, resume_text: str) -> Optional[str]:
        # Heuristic: use the first non-empty line that doesn't look like contact info
        lines = (resume_text or "").splitlines()
        for line in lines[:10]:
            s = line.strip()
            if not s:
                continue
            if '@' in s or s.lower().startswith(('email', 'phone', 'tel', 'mobile')):
                continue
            # Avoid obviously long lines
            if len(s) <= 80:
                return s
        return None
