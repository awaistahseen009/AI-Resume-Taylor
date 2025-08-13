from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re

SKILL_CANDIDATES = {
    # Core technical domains
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "sql", "nosql", "postgres", "mysql", "mongodb", "redis",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
    "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring",
    "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn", "llm", "nlp",
    "graphql", "rest", "microservices", "event-driven", "kafka",
}

class SkillSource(BaseModel):
    skill: str
    url: str
    snippet: Optional[str] = None
    source: Optional[str] = None

class RecommendedSkillsBundle(BaseModel):
    skills: List[str] = Field(default_factory=list, description="Deduplicated recommended skills")
    sources: List[SkillSource] = Field(default_factory=list, description="Evidence and links for each skill")


def _normalize(text: str) -> str:
    return (text or "").lower()


def _extract_skills_from_text(text: str) -> List[str]:
    t = _normalize(text)
    found = []
    for sk in SKILL_CANDIDATES:
        if re.search(rf"\b{re.escape(sk)}\b", t):
            found.append(sk)
    return found


def aggregate_skills_from_web(web_results: List[Dict[str, Any]]) -> RecommendedSkillsBundle:
    skills_set = set()
    sources: List[SkillSource] = []

    for item in web_results or []:
        snippet = item.get("snippet") or ""
        url = item.get("url") or ""
        src = item.get("source") or "web"
        extracted = _extract_skills_from_text(snippet)
        for sk in extracted:
            if sk not in skills_set:
                skills_set.add(sk)
                sources.append(SkillSource(skill=sk, url=url, snippet=snippet[:300], source=src))

    return RecommendedSkillsBundle(skills=sorted(skills_set), sources=sources)
