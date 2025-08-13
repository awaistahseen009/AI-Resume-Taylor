from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ContactInfo(BaseModel):
    name: str = Field(description="Full name of the person")
    location: str = Field(description="City, State or location")
    email: str = Field(description="Email address")
    phone: str = Field(description="Phone number")
    website: Optional[str] = Field(default=None, description="Personal website URL")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github: Optional[str] = Field(default=None, description="GitHub profile URL")

class EducationEntry(BaseModel):
    dates: str = Field(description="Date range for education (e.g., '2018-2022')")
    institution: str = Field(description="University or institution name")
    degree: str = Field(description="Degree and major")
    highlights: List[str] = Field(default=[], description="Key achievements or coursework")

class ExperienceEntry(BaseModel):
    dates: str = Field(description="Date range for position (e.g., '2020-2023')")
    job_title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    responsibilities: List[str] = Field(description="Key responsibilities and achievements")

class LeadershipEntry(BaseModel):
    dates: str = Field(description="Date range for leadership role")
    role: str = Field(description="Leadership role title")
    organization: str = Field(description="Organization name")

class ProjectEntry(BaseModel):
    title: str = Field(description="Project title")
    link: Optional[str] = Field(default=None, description="Project URL or link")
    descriptions: List[str] = Field(description="Project descriptions and key features")

class CertificationEntry(BaseModel):
    date: str = Field(description="Date obtained")
    title: str = Field(description="Certificate title")
    issuer: str = Field(description="Issuing organization")
    link: Optional[str] = Field(default=None, description="Certificate verification URL")

class ResumeData(BaseModel):
    contact_info: ContactInfo
    about_me: str = Field(description="Professional summary or about me section")
    education: List[EducationEntry] = Field(default=[])
    experience: List[ExperienceEntry] = Field(default=[])
    leadership: List[LeadershipEntry] = Field(default=[])
    projects: List[ProjectEntry] = Field(default=[])
    languages: str = Field(default="", description="Languages spoken")
    skills: str = Field(default="", description="Technical skills and technologies")
    volunteering: str = Field(default="", description="Volunteer work and community involvement")
    certifications: List[CertificationEntry] = Field(default=[])
    interests: str = Field(default="", description="Extra-curricular activities and interests")
