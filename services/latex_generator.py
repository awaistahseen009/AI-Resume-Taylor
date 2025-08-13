import re
from typing import Dict, List, Any
from .openai_latex import OpenAILaTeXGenerator
import logging

class LaTeXGenerator:
    """Service for generating LaTeX source from resume data"""
    
    def __init__(self):
        self.openai_generator = OpenAILaTeXGenerator()
    
    def generate_latex(self, resume_text: str, job_description: str = None) -> str:
        """Generate LaTeX source from resume text using OpenAI"""
        try:
            # Use OpenAI to generate complete LaTeX
            latex_code = self.openai_generator.generate_resume_latex(
                resume_text=resume_text,
                job_description=job_description
            )
            return latex_code
        except Exception as e:
            logging.error(f"LaTeX generation failed: {e}")
            # Fallback to basic template
            return self._generate_basic_latex(resume_text)
    
    def _generate_basic_latex(self, resume_text: str) -> str:
        """Fallback basic LaTeX template"""
        return f"""\\documentclass[11pt,a4paper,sans]{{moderncv}}
\\moderncvstyle{{classic}}
\\moderncvcolor{{blue}}

\\usepackage[scale=0.75]{{geometry}}

% Personal data
\\name{{Professional}}{{Resume}}

\\begin{{document}}

\\makecvtitle

\\section{{Content}}
\\cvitem{{}}{{
{resume_text[:1000]}
}}

\\end{{document}}"""
    
    def _parse_resume_sections(self, text: str) -> Dict[str, any]:
        """Parse resume text into structured sections"""
        sections = {
            'name': '',
            'contact': {},
            'summary': '',
            'experience': [],
            'education': [],
            'skills': [],
            'projects': [],
            'certifications': [],
            'other_sections': []
        }
        
        # Extract name (usually first line or prominent text)
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines for name
            line = line.strip()
            if line and len(line.split()) <= 4 and not '@' in line and not any(char.isdigit() for char in line):
                sections['name'] = line
                break
        
        # Extract contact information
        sections['contact'] = self._extract_contact_info(text)
        
        # Split text into sections based on common headers
        section_headers = {
            'experience': ['experience', 'work experience', 'employment', 'work history', 'professional experience'],
            'education': ['education', 'academic background', 'qualifications'],
            'skills': ['skills', 'technical skills', 'core competencies', 'expertise'],
            'projects': ['projects', 'key projects', 'notable projects'],
            'summary': ['summary', 'profile', 'objective', 'about'],
            'certifications': ['certifications', 'certificates', 'licenses']
        }
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            line_lower = line.lower()
            found_section = None
            
            for section_key, headers in section_headers.items():
                if any(header in line_lower for header in headers):
                    found_section = section_key
                    break
            
            if found_section:
                # Save previous section content
                if current_section and current_content:
                    sections[current_section] = self._parse_section_content(current_section, current_content)
                
                current_section = found_section
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections[current_section] = self._parse_section_content(current_section, current_content)
        
        return sections
    
    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extract contact information"""
        contact = {}
        
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            contact['email'] = email_match.group()
        
        # Phone
        phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                contact['phone'] = phone_match.group()
                break
        
        # LinkedIn
        linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text.lower())
        if linkedin_match:
            contact['linkedin'] = linkedin_match.group()
        
        # GitHub
        github_match = re.search(r'github\.com/[\w-]+', text.lower())
        if github_match:
            contact['github'] = github_match.group()
        
        return contact
    
    def _parse_section_content(self, section_type: str, content: List[str]) -> any:
        """Parse content for specific section types"""
        if section_type in ['experience', 'education', 'projects']:
            return self._parse_structured_section(content)
        elif section_type == 'skills':
            return self._parse_skills_section(content)
        elif section_type == 'summary':
            return ' '.join(content)
        else:
            return content
    
    def _parse_structured_section(self, content: List[str]) -> List[Dict[str, str]]:
        """Parse structured sections like experience, education"""
        items = []
        current_item = {}
        
        for line in content:
            line = line.strip()
            if not line:
                continue
            
            # Check if this looks like a new item (company/school name or job title)
            if self._is_new_item_header(line):
                if current_item:
                    items.append(current_item)
                current_item = {'title': line, 'details': []}
            else:
                if current_item:
                    current_item['details'].append(line)
                else:
                    current_item = {'title': line, 'details': []}
        
        if current_item:
            items.append(current_item)
        
        return items
    
    def _is_new_item_header(self, line: str) -> bool:
        """Determine if a line is likely a new item header"""
        # Simple heuristics for detecting headers
        return (
            len(line.split()) <= 6 and  # Short lines are often titles
            not line.startswith('•') and
            not line.startswith('-') and
            not line.startswith('*') and
            not line.lower().startswith('responsible for') and
            not line.lower().startswith('managed') and
            not line.lower().startswith('developed')
        )
    
    def _parse_skills_section(self, content: List[str]) -> List[str]:
        """Parse skills section"""
        skills = []
        for line in content:
            # Split by common delimiters
            line_skills = re.split(r'[,;•\-\n]', line)
            for skill in line_skills:
                skill = skill.strip()
                if skill and len(skill) > 1:
                    skills.append(skill)
        return skills
    
    def _generate_modern_template(self, sections: Dict[str, any]) -> str:
        """Generate modern LaTeX template"""
        latex_content = r"""
\documentclass[11pt,a4paper,sans]{moderncv}

% Modern CV theme
\moderncvstyle{banking}
\moderncvcolor{blue}

% Character encoding
\usepackage[utf8]{inputenc}

% Adjust page margins
\usepackage[scale=0.75]{geometry}

% Personal data
""" + f"\\name{{{self._escape_latex(sections.get('name', 'Your Name'))}}}{{}}\n"

        # Add contact information
        contact = sections.get('contact', {})
        if contact.get('phone'):
            latex_content += f"\\phone[mobile]{{{contact['phone']}}}\n"
        if contact.get('email'):
            latex_content += f"\\email{{{contact['email']}}}\n"
        if contact.get('linkedin'):
            latex_content += f"\\social[linkedin]{{{contact['linkedin']}}}\n"
        if contact.get('github'):
            latex_content += f"\\social[github]{{{contact['github']}}}\n"

        latex_content += r"""
\begin{document}
\makecvtitle

"""

        # Add summary/objective
        if sections.get('summary'):
            latex_content += "\\section{Professional Summary}\n"
            latex_content += f"{self._escape_latex(sections['summary'])}\n\n"

        # Add experience
        if sections.get('experience'):
            latex_content += "\\section{Professional Experience}\n"
            for exp in sections['experience']:
                latex_content += f"\\cventry{{}}{{{self._escape_latex(exp['title'])}}}{{}}{{}}{{}}{{\n"
                for detail in exp.get('details', []):
                    latex_content += f"\\item {self._escape_latex(detail)}\n"
                latex_content += "}\n"

        # Add education
        if sections.get('education'):
            latex_content += "\\section{Education}\n"
            for edu in sections['education']:
                latex_content += f"\\cventry{{}}{{{self._escape_latex(edu['title'])}}}{{}}{{}}{{}}{{\n"
                for detail in edu.get('details', []):
                    latex_content += f"\\item {self._escape_latex(detail)}\n"
                latex_content += "}\n"

        # Add skills
        if sections.get('skills'):
            latex_content += "\\section{Technical Skills}\n"
            skills_text = ", ".join(sections['skills'][:15])  # Limit to 15 skills
            latex_content += f"\\cvitem{{}}{{\\textbf{{{self._escape_latex(skills_text)}}}}}\n\n"

        # Add projects
        if sections.get('projects'):
            latex_content += "\\section{Key Projects}\n"
            for proj in sections['projects']:
                latex_content += f"\\cventry{{}}{{{self._escape_latex(proj['title'])}}}{{}}{{}}{{}}{{\n"
                for detail in proj.get('details', []):
                    latex_content += f"\\item {self._escape_latex(detail)}\n"
                latex_content += "}\n"

        latex_content += r"""
\end{document}
"""
        return latex_content
    
    def _generate_classic_template(self, sections: Dict[str, any]) -> str:
        """Generate classic LaTeX template"""
        latex_content = r"""
\documentclass[11pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.75in]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}

% Custom formatting
\titleformat{\section}{\large\bfseries}{\thesection}{1em}{}[\titlerule]
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{1em}{}

\begin{document}

% Header
""" + f"\\begin{{center}}\n\\textbf{{\\Large {self._escape_latex(sections.get('name', 'Your Name'))}}}\\\\\n"

        # Add contact in header
        contact = sections.get('contact', {})
        contact_parts = []
        if contact.get('phone'):
            contact_parts.append(contact['phone'])
        if contact.get('email'):
            contact_parts.append(contact['email'])
        if contact.get('linkedin'):
            contact_parts.append(contact['linkedin'])
        
        if contact_parts:
            latex_content += " | ".join(contact_parts) + "\\\\\n"

        latex_content += "\\end{center}\n\n"

        # Add sections similar to modern template but with classic formatting
        if sections.get('summary'):
            latex_content += "\\section*{Professional Summary}\n"
            latex_content += f"{self._escape_latex(sections['summary'])}\n\n"

        if sections.get('experience'):
            latex_content += "\\section*{Professional Experience}\n"
            for exp in sections['experience']:
                latex_content += f"\\subsection*{{{self._escape_latex(exp['title'])}}}\n"
                latex_content += "\\begin{itemize}[leftmargin=*]\n"
                for detail in exp.get('details', []):
                    latex_content += f"\\item {self._escape_latex(detail)}\n"
                latex_content += "\\end{itemize}\n\n"

        latex_content += "\\end{document}\n"
        return latex_content
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters"""
        if not text:
            return ""
        
        # Dictionary of LaTeX special characters and their escaped versions
        latex_special_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '^': r'\textasciicircum{}',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '\\': r'\textbackslash{}'
        }
        
        for char, escaped in latex_special_chars.items():
            text = text.replace(char, escaped)
        
        return text
