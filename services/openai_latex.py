import os
import openai
from typing import Dict, Any
import logging

class OpenAILaTeXGenerator:
    """Generate professional LaTeX resumes using OpenAI"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY')
        )
    
    def generate_resume_latex(self, resume_text: str, job_description: str = None) -> str:
        """Generate complete LaTeX resume from text, optionally tailored to job"""
        
        # Strict template the model must follow
        template_text = r"""\documentclass[10pt, letterpaper]{article}

% Packages:
\usepackage[
    ignoreheadfoot,
    top=2 cm,
    bottom=2 cm,
    left=2 cm,
    right=2 cm,
    footskip=1.0 cm,
]{geometry}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{array}
\usepackage[dvipsnames]{xcolor}
\definecolor{primaryColor}{RGB}{0, 0, 0}
\usepackage{enumitem}
\usepackage{fontawesome5}
\usepackage{amsmath}
\usepackage[
    pdftitle={Your Name's CV},
    pdfauthor={Your Name},
    pdfcreator={LaTeX with RenderCV},
    colorlinks=true,
    urlcolor=primaryColor
]{hyperref}
\usepackage[pscoord]{eso-pic}
\usepackage{calc}
\usepackage{bookmark}
\usepackage{lastpage}
\usepackage{changepage}
\usepackage{paracol}
\usepackage{ifthen}
\usepackage{needspace}
\usepackage{iftex}

% Ensure that generated pdf is machine readable/ATS parsable:
\ifPDFTeX
    \input{glyphtounicode}
    \pdfgentounicode=1
    \usepackage[T1]{fontenc}
    \usepackage[utf8]{inputenc}
    \usepackage{lmodern}
\fi

\usepackage{charter}

% Some settings:
\raggedright
\AtBeginEnvironment{adjustwidth}{\partopsep0pt}
\pagestyle{empty}
\setcounter{secnumdepth}{0}
\setlength{\parindent}{0pt}
\setlength{\topskip}{0pt}
\setlength{\columnsep}{0.15cm}
\pagenumbering{gobble}

\titleformat{\section}{\needspace{4\baselineskip}\bfseries\large}{}{0pt}{}[\vspace{1pt}\titlerule]

\titlespacing{\section}{-1pt}{0.3 cm}{0.2 cm}

\renewcommand\labelitemi{$\vcenter{\hbox{\small$\bullet$}}$}
\newenvironment{highlights}{\begin{itemize}[topsep=0.10 cm,parsep=0.10 cm,partopsep=0pt,itemsep=0pt,leftmargin=0 cm + 10pt]}{\end{itemize}}
\newenvironment{highlightsforbulletentries}{\begin{itemize}[topsep=0.10 cm,parsep=0.10 cm,partopsep=0pt,itemsep=0pt,leftmargin=10pt]}{\end{itemize}}
\newenvironment{onecolentry}{\begin{adjustwidth}{0 cm + 0.00001 cm}{0 cm + 0.00001 cm}}{\end{adjustwidth}}
\newenvironment{twocolentry}[2][]{\onecolentry\def\secondColumn{#2}\setcolumnwidth{\fill, 4.5 cm}\begin{paracol}{2}}{\switchcolumn \raggedleft \secondColumn\end{paracol}\endonecolentry}
\newenvironment{threecolentry}[3][]{\onecolentry\def\thirdColumn{#3}\setcolumnwidth{, \fill, 4.5 cm}\begin{paracol}{3}{\raggedright #2} \switchcolumn}{\switchcolumn \raggedleft \thirdColumn\end{paracol}\endonecolentry}
\newenvironment{header}{\setlength{\topsep}{0pt}\par\kern\topsep\centering\linespread{1.5}}{\par\kern\topsep}

\let\hrefWithoutArrow\href

\begin{document}
    \newcommand{\AND}{\unskip\cleaders\copy\ANDbox\hskip\wd\ANDbox\ignorespaces}
    \newsavebox\ANDbox
    \sbox\ANDbox{$|$}

    % Header
    % ... Fill with name, location, email, phone, site, linkedin, github

    % Sections: About Me, Education, Experience, Management and Leadership Skills, Projects,
    % Languages, Technologies/Skills, Volunteering, Certificates and Certifications,
    % Extra-Curricular & Interests

\end{document}"""

        system_prompt = r"""You are an expert LaTeX resume writer.

Follow the EXACT LaTeX template skeleton provided below for every output. Recreate its structure, preamble, packages, environments, and sectioning. Then populate only with content derived from the original resume, tailored to the job description when provided.

Rules:
- Output a single, fully compilable LaTeX document that begins with \documentclass and ends with \end{document}.
- Use the provided article-based template (not moderncv). Keep the same packages, formatting, environments, and typical section structure.
- Tailor by prioritizing and rephrasing content from the original resume that matches the job description. Do not invent any information.
- If any section is missing in the original resume content, omit that section entirely (do not create placeholders).
- Keep formatting ATS-friendly and professional.

TEMPLATE TO FOLLOW STRICTLY:
""" + template_text + r"""
"""

        if job_description:
            user_prompt = (
                "Please tailor the following original resume to the target job description and RETURN a full LaTeX document that strictly follows the template.\n\n"
                "[ORIGINAL RESUME]\n" + resume_text + "\n\n"
                "[TARGET JOB DESCRIPTION]\n" + job_description + "\n\n"
                "Remember: Do not invent content. Omit sections not supported by the original resume."
            )
        else:
            user_prompt = (
                "Please convert the following original resume into a full LaTeX resume that strictly follows the template.\n\n"
                "[ORIGINAL RESUME]\n" + resume_text + "\n\n"
                "Remember: Do not invent content. Omit sections not supported by the original resume."
            )

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            latex_code = response.choices[0].message.content.strip()
            
            # Ensure it starts and ends properly
            if not latex_code.lstrip().startswith('\\documentclass'):
                # If model omitted docclass, prepend the template's docclass line
                latex_code = '\\documentclass[10pt, letterpaper]{article}\n' + latex_code

            if '\\end{document}' not in latex_code:
                latex_code += '\n\\end{document}'
                
            return latex_code
            
        except Exception as e:
            logging.error(f"OpenAI LaTeX generation failed: {e}")
            # Fallback to basic template
            return self._generate_fallback_latex(resume_text)
    
    def _generate_fallback_latex(self, resume_text: str) -> str:
        """Fallback LaTeX template if OpenAI fails (uses the provided article template)."""
        safe_text = (resume_text or "").replace("\\", "\\\\")
        return r"""\documentclass[10pt, letterpaper]{article}
\usepackage[ignoreheadfoot,top=2 cm,bottom=2 cm,left=2 cm,right=2 cm,footskip=1.0 cm]{geometry}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{array}
\usepackage[dvipsnames]{xcolor}
\definecolor{primaryColor}{RGB}{0, 0, 0}
\usepackage{enumitem}
\usepackage{fontawesome5}
\usepackage{amsmath}
\usepackage[pdftitle={Fallback CV},pdfauthor={Candidate},pdfcreator={LaTeX},colorlinks=true,urlcolor=primaryColor]{hyperref}
\usepackage[pscoord]{eso-pic}
\usepackage{calc}
\usepackage{bookmark}
\usepackage{lastpage}
\usepackage{changepage}
\usepackage{paracol}
\usepackage{ifthen}
\usepackage{needspace}
\usepackage{iftex}
\ifPDFTeX
    \input{glyphtounicode}
    \pdfgentounicode=1
    \usepackage[T1]{fontenc}
    \usepackage[utf8]{inputenc}
    \usepackage{lmodern}
\fi
\usepackage{charter}
\raggedright
\AtBeginEnvironment{adjustwidth}{\partopsep0pt}
\pagestyle{empty}
\setcounter{secnumdepth}{0}
\setlength{\parindent}{0pt}
\setlength{\topskip}{0pt}
\setlength{\columnsep}{0.15cm}
\pagenumbering{gobble}
\titleformat{\section}{\needspace{4\baselineskip}\bfseries\large}{}{0pt}{}[\vspace{1pt}\titlerule]
\titlespacing{\section}{-1pt}{0.3 cm}{0.2 cm}
\renewcommand\labelitemi{$\vcenter{\hbox{\small$\bullet$}}$}
\newenvironment{highlights}{\begin{itemize}[topsep=0.10 cm,parsep=0.10 cm,partopsep=0pt,itemsep=0pt,leftmargin=0 cm + 10pt]}{\end{itemize}}
\newenvironment{onecolentry}{\begin{adjustwidth}{0 cm + 0.00001 cm}{0 cm + 0.00001 cm}}{\end{adjustwidth}}
\begin{document}
\begin{header}
    \fontsize{25 pt}{25 pt}\selectfont Candidate Name
\end{header}
\vspace{5 pt}
\section{About Me}
\begin{onecolentry}
Minimal fallback generated because AI failed. Below is extracted resume text snippet.\\\newline
% Snippet from resume text:
""" + safe_text[:600] + r"""
\end{onecolentry}
\end{document}"""

    def generate_job_description_latex(self, job_data: Dict[str, Any]) -> str:
        """Generate LaTeX document for job description"""
        
        system_prompt = r"""You are a document formatting expert. Your task is to convert a job description from plain text into a clean, professional, and readable LaTeX document.

**LaTeX Requirements:**
- Use the `article` document class.
- Use `titlesec` and `geometry` for good typography and layout.
- Structure the document with a main title, author (company), and clear sections for different parts of the job description (e.g., Title, Company, Location, Description, Requirements).
- Ensure the output is a complete, compilable LaTeX document.

Your final output must be **only** the raw LaTeX code."""
        
        user_prompt = f"""Please convert the following job posting details into a complete LaTeX document based on my instructions.

**Job Details:**
- **Title:** {job_data.get('title', 'N/A')}
- **Company:** {job_data.get('company', 'N/A')}
- **Location:** {job_data.get('location', 'N/A')}
- **Description:** {job_data.get('description_text', 'N/A')}
- **Requirements:** {job_data.get('requirements', 'N/A')}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"OpenAI job LaTeX generation failed: {e}")
            return self._generate_fallback_job_latex(job_data)
    
    def _generate_fallback_job_latex(self, job_data: Dict[str, Any]) -> str:
        """Fallback job description LaTeX"""
        return f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{titlesec}}

\\title{{{job_data.get('title', 'Job Description')}}}
\\author{{{job_data.get('company', 'Company')}}}
\\date{{}}

\\begin{{document}}
\\maketitle

\\section{{Position}}
{job_data.get('title', 'N/A')}

\\section{{Company}}
{job_data.get('company', 'N/A')}

\\section{{Location}}
{job_data.get('location', 'N/A')}

\\section{{Description}}
{job_data.get('description_text', 'N/A')}

\\section{{Requirements}}
{job_data.get('requirements', 'N/A')}

\\end{{document}}"""
