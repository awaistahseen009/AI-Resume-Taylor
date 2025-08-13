from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app, make_response, session
from dateutil.parser import parse as parse_date
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import db
from services.latex_generator import LaTeXGenerator
from xhtml2pdf import pisa
import io
from services.ai_workflow import ResumeAIWorkflow
from services.vector_db import PineconeVectorDB
from services.resume_processor import ResumeProcessor
from services.resume_generator import ResumeContentGenerator
from services.resume_schema import ResumeData
from services.cover_letter_generator import CoverLetterGenerator
from services.tavily_client import TavilyClient
from pydantic import BaseModel, Field
import os
import tempfile
import logging
import json
import re
from datetime import datetime

resume_bp = Blueprint('resume', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

# Initialize vector DB client once
vector_db = PineconeVectorDB()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@resume_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload and process resume"""
    if request.method == 'POST':
        title = request.form.get('title')
        # Accept file from either 'resume_file' (template) or 'file'
        file = request.files.get('resume_file') or request.files.get('file')
        
        if not title:
            flash('Please provide a title for your resume', 'error')
            return render_template('resume/upload.html')
        
        # Require file-only uploads
        if not file or not file.filename:
            flash('Please upload a resume file (PDF, DOCX, or TXT).', 'error')
            return render_template('resume/upload.html')
        
        file_path = None
        file_type = None
        resume_text = ''
        
        # Process uploaded file
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Invalid file type. Please upload PDF, DOCX, or TXT files.', 'error')
                return render_template('resume/upload.html')
            
            filename = secure_filename(file.filename)
            # Ensure uploads directory exists
            os.makedirs('uploads', exist_ok=True)
            file_path = os.path.join('uploads', filename)
            file.save(file_path)
            file_type = file.filename.split('.')[-1].lower()
            
            # Extract text from file
            processor = ResumeProcessor()
            try:
                resume_text = processor.extract_text_from_file(file_path)
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                return render_template('resume/upload.html')
        
        # Create resume record in Supabase
        try:
            resume_data = db.create_resume(
                user_id=current_user.id,
                title=title,
                original_text=(resume_text or '').strip(),
                file_path=file_path,
                file_type=file_type
            )
            
            if resume_data:
                # Prepare metadata without nulls
                metadata = {'title': title}
                if file_type:
                    metadata['file_type'] = file_type
                
                # Store resume embedding in Pinecone
                try:
                    vector_db.store_resume_embedding(
                        resume_id=resume_data['id'],
                        user_id=current_user.id,
                        resume_text=(resume_text or '').strip(),
                        metadata=metadata
                    )
                except Exception as ve:
                    # Non-fatal if vector storage fails
                    logging.warning(f"Pinecone upsert failed: {ve}")
                
                flash('Resume uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                logging.error('Supabase insert returned no data for resume create')
                flash('Failed to save resume. Please try again. (DB insert returned no data)', 'error')
        except Exception as e:
            logging.error(f"Exception during resume save: {e}", exc_info=True)
            flash(f'Failed to save resume: {str(e)}', 'error')
    
    return render_template('resume/upload.html')

@resume_bp.route('/tailor/<int:resume_id>', methods=['POST'])
@login_required
def tailor(resume_id):
    """Tailor resume for specific job description"""
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        return jsonify({'error': 'Resume not found'}), 404
    
    job_description = request.json.get('job_description')
    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400
    # Ensure it's a string
    job_description = str(job_description)
    
    logging.info(f"Resume object for tailoring: {resume}")

    try:
        # Run AI workflow to tailor resume
        try:
            workflow = ResumeAIWorkflow()
            result = workflow.tailor_resume(resume.get('original_text', ''), job_description)
        except Exception as e:
            logging.error(f"Error in AI tailoring stage: {e}", exc_info=True)
            return jsonify({'error': f'AI tailoring failed: {str(e)}'}), 500

        # Validate result structure
        if not isinstance(result, dict) or 'tailored_resume' not in result:
            return jsonify({'error': 'AI tailoring returned invalid result'}), 500

        # Use AI-returned LaTeX directly
        try:
            latex_source = result['tailored_resume']
            if not isinstance(latex_source, str) or '\\documentclass' not in latex_source:
                raise ValueError('AI did not return full LaTeX source')
        except Exception as e:
            logging.error(f"Invalid LaTeX from AI: {e}", exc_info=True)
        
        # Extract tailored resume and handle errors
        tailored_resume_text = result.get('tailored_resume')
        if result.get('error'):
            flash(f"Error during tailoring: {result['error']}", 'error')

        # Cover letters are now part of the workflow result
        cover_letters_data = {"cover_letters": result.get("cover_letters", [])}

        # Update resume with tailored content (only safe, known columns)
        updates = {
            'tailored_text': tailored_resume_text,
            'is_tailored': True,
            'job_description': job_description,
            'cover_letters': cover_letters_data if cover_letters_data else None  # Save JSON (dict) to JSONB column
        }

        # Conditional similar job search via Tavily, controlled by profile toggle stored in session
        similar_on = bool(session.get('similar_jobs_enabled'))
        recommended_bundle = None
        if similar_on and job_description:
            try:
                from services.recommended_skills import RecommendedSkillsBundle, aggregate_skills_from_web
                tav = TavilyClient(api_key=current_app.config.get('TAVILY_API_KEY'))
                # Build a simple query; in real use, would extract job title via LLM or regex
                query = (resume.get('title') or '').strip() or job_description.split('\n', 1)[0][:120]
                web_results = tav.search_jobs(query, max_results=5)
                recommended_bundle = aggregate_skills_from_web(web_results)
                updates['recommended_skills'] = recommended_bundle.model_dump()
            except Exception as e:
                logging.warning(f"Similar job search aggregation failed: {e}")

        # Attempt update; if schema cache missing optional columns, drop and retry
        try:
            updated_resume = db.update_resume(resume_id, current_user.id, updates)
        except Exception as e:
            # If specific column missing, remove and retry up to a few times
            import re
            msg = str(getattr(e, 'args', [e])[0])
            logging.error(f"Error updating resume in DB: {msg}", exc_info=True)
            removed_any = False
            for _ in range(3):
                m = re.search(r"Could not find the '([^']+)' column of 'resumes'", msg)
                if not m:
                    break
                missing_col = m.group(1)
                if missing_col in updates:
                    updates.pop(missing_col, None)
                    removed_any = True
                try:
                    updated_resume = db.update_resume(resume_id, current_user.id, updates)
                    break
                except Exception as e2:
                    msg = str(getattr(e2, 'args', [e2])[0])
                    logging.error(f"Retry update failed: {msg}")
                    continue
            else:
                # loop exhausted
                return jsonify({'error': f'Database update failed: {msg}'}), 500
            if not removed_any and not updated_resume:
                return jsonify({'error': f'Database update failed: {msg}'}), 500
        
        if updated_resume:
            # Update embedding in Pinecone with tailored content
            # Ensure metadata values are simple types for Pinecone
            pinecone_metadata = {
                'title': str(resume.get('title', '')),
                'is_tailored': True
            }
            file_type = resume.get('file_type')
            if file_type and not isinstance(file_type, (dict, list)):
                pinecone_metadata['file_type'] = str(file_type)

            logging.info(f"Pinecone metadata: {pinecone_metadata}")

            try:
                vector_db.store_resume_embedding(
                    resume_id=resume_id,
                    user_id=current_user.id,
                    resume_text=result['tailored_resume'],
                    metadata=pinecone_metadata
                )
            except Exception as e:
                logging.error(f"Error storing embedding in Pinecone: {e}", exc_info=True)
                # Do not fail the request solely due to embedding storage; continue
        
        return jsonify({
            'success': True,
            'tailored_resume': result['tailored_resume'],
            'latex_source': latex_source,
            'keywords': result.get('keywords', [])
        })
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Unhandled error in tailor route: {e}\n{tb}")
        return jsonify({'error': str(e), 'traceback': tb}), 500

@resume_bp.route('/preview/<int:resume_id>')
@login_required
def preview_resume(resume_id):
    """Preview resume in browser using strict HTML template with generated content."""
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        flash('Resume not found', 'error')
        return redirect(url_for('dashboard'))

    # If resume is tailored or we have a job description, generate structured content; otherwise show original resume text
    job_description = resume.get('job_description', '') or ''
    is_tailored = bool(resume.get('is_tailored'))
    existing_text = resume.get('tailored_text') or resume.get('original_text', '')

    if is_tailored or job_description.strip():
        resume_content = None
        try:
            generator = ResumeContentGenerator()
            resume_content = generator.generate_resume_content(job_description, existing_text)
        except Exception as e:
            logging.error(f"Error generating resume content: {e}")
            resume_content = None
        html_content = build_resume_html_template(resume_content)
    else:
        # Render original resume as readable HTML
        html_content = convert_text_to_html(resume.get('original_text', '') or '')
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@resume_bp.route('/preview-pdf/<int:resume_id>')
@login_required
def preview_pdf(resume_id):
    """Deprecated: PDF preview disabled. Use HTML preview route instead."""
    return 'PDF preview is disabled. Use /preview-html/<id> instead.', 410

@resume_bp.route('/preview-html/<int:resume_id>')
@login_required
def preview_resume_html(resume_id):
    """Generate HTML preview of resume using strict provided template with generated content."""
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        return '<div class="text-center text-red-600"><p>Resume not found</p></div>', 404

    # Generate resume content if we have tailored text or job description
    resume_content = None
    job_description = resume.get('job_description', '')
    existing_text = resume.get('tailored_text') or resume.get('original_text', '')
    
    if job_description or existing_text:
        try:
            generator = ResumeContentGenerator()
            resume_content = generator.generate_resume_content(job_description, existing_text)
        except Exception as e:
            logging.error(f"Error generating resume content: {e}")
            resume_content = None

    html_content = build_resume_html_template(resume_content)
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@resume_bp.route('/download/<int:resume_id>')
@login_required
def download_resume(resume_id):
    """Download resume as PDF. Falls back to HTML if PDF generation is unavailable."""
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        flash('Resume not found', 'error')
        return redirect(url_for('dashboard'))

    # Decide what content to render (tailored vs original)
    job_description = resume.get('job_description', '') or ''
    is_tailored = bool(resume.get('is_tailored'))
    existing_text = resume.get('tailored_text') or resume.get('original_text', '')
    if is_tailored or job_description.strip():
        resume_content = None
        try:
            generator = ResumeContentGenerator()
            resume_content = generator.generate_resume_content(job_description, existing_text)
        except Exception as e:
            logging.error(f"Error generating resume content: {e}")
            resume_content = None
        html_content = build_resume_html_template(resume_content)
    else:
        html_content = convert_text_to_html(resume.get('original_text', '') or '')

    # Try to generate PDF via xhtml2pdf if available
    pdf_bytes = None
    try:
        from xhtml2pdf import pisa
        import io

        # Define a link callback to resolve static file paths
        def link_callback(uri, rel):
            # Handle static files (e.g., CSS)
            if uri.startswith(url_for('static', filename='')):
                path = os.path.join(current_app.static_folder, uri.split('/static/')[1])
                if os.path.exists(path):
                    return path
            # Handle external URLs
            if uri.startswith('http://') or uri.startswith('https://'):
                return uri
            return None

        pdf_io = io.BytesIO()
        try:
            # Create PDF with the link_callback to handle CSS
            pisa_status = pisa.CreatePDF(
                src=html_content,
                dest=pdf_io,
                link_callback=link_callback
            )

            if pisa_status.err:
                raise Exception(f"PDF generation error: {pisa_status.err}")

            pdf_bytes = pdf_io.getvalue()
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename="{resume.get("title", "resume").replace(" ", "_")}.pdf"'
            return response

        except Exception as e:
            logging.error(f"PDF generation with xhtml2pdf failed: {e}")
            # Fallback to sending HTML content if PDF generation fails
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = f'attachment; filename={resume.get("title", "resume")}.html'
            flash('PDF generation failed. Downloading as HTML instead.', 'warning')
            return response

    except Exception as e:
        logging.error(f"PDF generation with WeasyPrint failed: {e}")
        # Fallback to sending HTML content if PDF generation fails
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename={resume.get("title", "resume")}.html'
        flash('PDF generation failed. Downloading as HTML instead.', 'warning')
        return response

@resume_bp.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    """Delete resume"""
    # Fetch via Supabase
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        return jsonify({'error': 'Resume not found'}), 404

    # Delete local file if present
    try:
        file_path = resume.get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        # Non-fatal if local file removal fails
        pass

    # Delete from Supabase
    try:
        ok = db.delete_resume(resume_id, current_user.id)
        if not ok:
            return jsonify({'error': 'Failed to delete resume'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'success': True})


# Similar job search toggle APIs (stored in session for simplicity)
@resume_bp.route('/api/profile/similar-jobs-toggle', methods=['GET', 'POST'])
@login_required
def similar_jobs_toggle():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled'))
        session['similar_jobs_enabled'] = enabled
        return jsonify({'success': True, 'enabled': enabled})
    else:
        return jsonify({'success': True, 'enabled': bool(session.get('similar_jobs_enabled'))})


@resume_bp.route('/cover-letters/<int:resume_id>', methods=['GET', 'POST'])
@login_required
def cover_letters(resume_id):
    """Generate (POST) and/or display (GET) up to 3 cover letter versions for a resume."""
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        if request.method == 'POST':
            return jsonify({'error': 'Resume not found'}), 404
        flash('Resume not found', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        job_description = (resume.get('job_description') or '').strip()
        resume_text = (resume.get('tailored_text') or resume.get('original_text') or '').strip()
        if not job_description or not resume_text:
            flash('Missing job description or resume text for cover letter generation.', 'error')
            return redirect(url_for('resume.cover_letters', resume_id=resume_id))

        try:
            gen = CoverLetterGenerator(api_key=current_app.config.get('OPENAI_API_KEY'))
            bundle = gen.generate(resume_text=resume_text, job_description=job_description)
            # Persist JSON bundle under 'cover_letters'
            updates = {'cover_letters': bundle.model_dump()}
            try:
                db.update_resume(resume_id, current_user.id, updates)
            except Exception as e:
                # If column missing, ignore and proceed
                logging.warning(f"Could not persist cover_letters: {e}")
            flash('Generated cover letters successfully.', 'success')
            return redirect(url_for('resume.cover_letters', resume_id=resume_id))
        except Exception as e:
            logging.error(f"Cover letter generation failed: {e}")
            flash('Cover letter generation failed.', 'error')
            return redirect(url_for('resume.cover_letters', resume_id=resume_id))

    # GET: display cover letters if present
    letters = resume.get('cover_letters') or {}
    # If stored as a JSON string, parse it
    if isinstance(letters, str):
        try:
            letters = json.loads(letters)
        except Exception:
            letters = {}
    return render_template('cover_letters.html', resume=resume, cover_letters=letters)


@resume_bp.route('/jobs')
@login_required
def jobs_list():
    """List all resumes that have an associated job description (targets)."""
    try:
        # Fetch user's resumes then filter
        all_resumes = db.get_user_resumes(current_user.id) or []
        resumes = [
            r for r in all_resumes
            if r.get('is_tailored') or r.get('job_description')
        ]
    except Exception as e:
        logging.error(f"Error fetching resumes: {e}")
        resumes = []
    # Filter those targeted: has job_description OR is_tailored True
    jobs = [r for r in (resumes or []) if ((r or {}).get('job_description')) or bool((r or {}).get('is_tailored'))]
    return render_template('jobs_list.html', jobs=jobs)

# Alias as requested
@resume_bp.route('/job')
@login_required
def job_list_alias():
    return jobs_list()


@resume_bp.route('/recommended-skills/<int:resume_id>')
@login_required
def get_recommended_skills(resume_id):
    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        return jsonify({'error': 'Resume not found'}), 404
    data = resume.get('recommended_skills') or {}
    return jsonify({'success': True, 'recommended_skills': data})

def convert_text_to_html(text: str) -> str:
    """Convert plain text resume to formatted HTML"""
    if not text:
        return '<p>No content available</p>'
    
    # Split into lines and process
    lines = text.split('\n')
    html_parts = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section headers (all caps, or ending with colon)
        if (line.isupper() and len(line) > 3) or line.endswith(':'):
            if current_section:
                html_parts.append('</div>')
            html_parts.append(f'<div class="mb-6"><h2 class="text-xl font-bold text-gray-800 mb-3 border-b-2 border-blue-600 pb-1">{line.rstrip(":")}</h2>')
            current_section = line
        # Detect contact info (email, phone)
        elif '@' in line or any(char.isdigit() for char in line.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')):
            html_parts.append(f'<p class="text-gray-600 mb-1">{line}</p>')
        # Detect dates (years)
        elif re.search(r'\b(19|20)\d{2}\b', line):
            html_parts.append(f'<p class="text-gray-700 font-medium mb-2">{line}</p>')
        # Regular content
        else:
            # Check if it looks like a job title or company
            if any(word in line.lower() for word in ['engineer', 'manager', 'developer', 'analyst', 'specialist', 'coordinator', 'director', 'inc', 'llc', 'corp', 'company']):
                html_parts.append(f'<h3 class="text-lg font-semibold text-gray-800 mt-3 mb-1">{line}</h3>')
            else:
                html_parts.append(f'<p class="text-gray-700 mb-2">{line}</p>')
    
    if current_section:
        html_parts.append('</div>')
    
    return f'<div class="max-w-4xl mx-auto p-6">{"".join(html_parts)}</div>'

def build_resume_html_template(resume_data: ResumeData = None) -> str:
    """Return the strict HTML resume template populated with actual content or placeholders. No emojis. """
    last_updated = datetime.now().strftime('%B %Y')
    
    # Use provided data or fallback to placeholders
    if resume_data:
        contact = resume_data.contact_info
        name = contact.name
        location = contact.location
        email = contact.email
        phone = contact.phone
        website = contact.website or "[website-url]"
        linkedin = contact.linkedin or "[linkedin-url]"
        github = contact.github or "[github-url]"
        about_me = resume_data.about_me
        
        # Build education section
        education_html = ""
        for edu in resume_data.education:
            highlights_html = "".join([f"<li>{highlight}</li>" for highlight in edu.highlights])
            education_html += f"""
        <div class="twocolentry">
            <div class="left">{edu.dates}</div>
            <div class="right">{edu.institution} & {edu.degree}</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    {highlights_html}
                </ul>
            </div>
        </div>"""
        
        # Build experience section
        experience_html = ""
        for exp in resume_data.experience:
            responsibilities_html = "".join([f"<li>{resp}</li>" for resp in exp.responsibilities])
            experience_html += f"""
        <div class="twocolentry">
            <div class="left">{exp.dates}</div>
            <div class="right">{exp.job_title} & {exp.company}</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    {responsibilities_html}
                </ul>
            </div>
        </div>"""
        
        # Build leadership section
        leadership_html = ""
        for lead in resume_data.leadership:
            leadership_html += f"""
        <div class="twocolentry">
            <div class="left">{lead.dates}</div>
            <div class="right">{lead.role} & {lead.organization}</div>
        </div>"""
        
        # Build projects section
        projects_html = ""
        for proj in resume_data.projects:
            descriptions_html = "".join([f"<li>{desc}</li>" for desc in proj.descriptions])
            project_link = f'<a href="{proj.link}">{proj.title}</a>' if proj.link else proj.title
            projects_html += f"""
        <div class="twocolentry">
            <div class="left">{project_link}</div>
            <div class="right">{proj.title}</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    {descriptions_html}
                </ul>
            </div>
        </div>"""
        
        # Build certifications section
        certifications_html = ""
        for cert in resume_data.certifications:
            cert_link = f'<a href="{cert.link}">{cert.date}</a>' if cert.link else cert.date
            certifications_html += f"""
        <div class="twocolentry">
            <div class="left">{cert_link}</div>
            <div class="right">{cert.title} & {cert.issuer}</div>
        </div>"""
        
        languages = resume_data.languages
        skills = resume_data.skills
        volunteering = resume_data.volunteering
        interests = resume_data.interests
        
    else:
        # Fallback to placeholders
        name = "[Your Name]"
        location = "[Location]"
        email = "[email@example.com]"
        phone = "[+1234567890]"
        website = "[website-url]"
        linkedin = "[linkedin-url]"
        github = "[github-url]"
        about_me = "[Your about me description]"
        
        education_html = """
        <div class="twocolentry">
            <div class="left">[Dates]</div>
            <div class="right">[Institution & Degree]</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    <li>[Highlight 1]</li>
                    <li>[Highlight 2]</li>
                </ul>
            </div>
        </div>"""
        
        experience_html = """
        <div class="twocolentry">
            <div class="left">[Dates]</div>
            <div class="right">[Job Title & Company]</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    <li>[Responsibility 1]</li>
                    <li>[Responsibility 2]</li>
                </ul>
            </div>
        </div>"""
        
        leadership_html = """
        <div class="twocolentry">
            <div class="left">[Dates]</div>
            <div class="right">[Role & Organization]</div>
        </div>"""
        
        projects_html = """
        <div class="twocolentry">
            <div class="left"><a href="[project-url]">[Project Link]</a></div>
            <div class="right">[Project Title]</div>
        </div>
        <div class="onecolentry">
            <div class="highlights">
                <ul>
                    <li>[Description 1]</li>
                    <li>[Description 2]</li>
                </ul>
            </div>
        </div>"""
        
        certifications_html = """
        <div class="twocolentry">
            <div class="left"><a href="[certificate-url]">[Date]</a></div>
            <div class="right">[Certificate Title & Issuer]</div>
        </div>"""
        
        languages = "[Language details]"
        skills = "[Skill details]"
        volunteering = "[Volunteering details]"
        interests = "[Interests details]"
    
    return f"""
<script type="text/javascript">
        var gk_isXlsx = false;
        var gk_xlsxFileLookup = {{}};
        var gk_fileData = {{}};
        function filledCell(cell) {{
          return cell !== '' && cell != null;
        }}
        function loadFileData(filename) {{
        if (gk_isXlsx && gk_xlsxFileLookup[filename]) {{
            try {{
                var workbook = XLSX.read(gk_fileData[filename], {{ type: 'base64' }});
                var firstSheetName = workbook.SheetNames[0];
                var worksheet = workbook.Sheets[firstSheetName];

                // Convert sheet to JSON to filter blank rows
                var jsonData = XLSX.utils.sheet_to_json(worksheet, {{ header: 1, blankrows: false, defval: '' }});
                // Filter out blank rows (rows where all cells are empty, null, or undefined)
                var filteredData = jsonData.filter(row => row.some(filledCell));

                // Heuristic to find the header row by ignoring rows with fewer filled cells than the next row
                var headerRowIndex = filteredData.findIndex((row, index) =>
                  row.filter(filledCell).length >= filteredData[index + 1]?.filter(filledCell).length
                );
                // Fallback
                if (headerRowIndex === -1 || headerRowIndex > 25) {{
                  headerRowIndex = 0;
                }}

                // Convert filtered JSON back to CSV
                var csv = XLSX.utils.aoa_to_sheet(filteredData.slice(headerRowIndex)); // Create a new sheet from filtered array of arrays
                csv = XLSX.utils.sheet_to_csv(csv, {{ header: 1 }});
                return csv;
            }} catch (e) {{
                console.error(e);
                return "";
            }}
        }}
        return gk_fileData[filename] || "";
        }}
        </script><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume</title>
    <style>
        /* Page container to make it feel like a real resume sheet */
        .page {{
            background: #ffffff;
            border: 1px solid #d1d5db; /* light gray border */
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-radius: 6px;
            padding: 32px;
        }}
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2em;
            margin: 0;
            color: #2c3e50;
        }}
        .header .contact-info {{
            margin-top: 10px;
        }}
        .header .contact-info span {{
            margin-right: 15px;
        }}
        h2 {{
            font-size: 1.5em;
            padding-bottom: 0.2em;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #2c3e50;
        }}
        .section-content {{
            margin-left: 20px;
            padding: 1em 0;
            margin-bottom: 1em;
        }}
        .twocolentry {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .twocolentry .left {{
            font-weight: bold;
        }}
        .twocolentry .right {{
            text-align: right;
        }}
        ul {{
            list-style-type: disc;
            margin-left: 2em;
            margin-bottom: 1em;
        }}
        li {{
            margin-bottom: 0.5em;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .highlights {{
            margin-left: 20px;
        }}
        .footer {{
            text-align: right;
            font-size: 0.8em;
            color: #7f8c8d;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="page">
    <div class="header">
        <h1>{name}</h1>
        <div class="contact-info">
            <span>{location}</span>
            <span><a href="mailto:{email}">{email}</a></span>
            <span><a href="tel:{phone}">{phone}</a></span>
            <span><a href="{website}">Website</a></span>
            <span><a href="{linkedin}">LinkedIn</a></span>
            <span><a href="{github}">GitHub</a></span>
        </div>
    </div>

    <!-- About Me -->
    <h2>About Me</h2>
    <div class="section-content">
        <div class="onecolentry">
            {about_me}
        </div>
    </div>

    <!-- Education -->
    <h2>Education</h2>
    <div class="section-content">
        {education_html}
    </div>

    <!-- Experience -->
    <h2>Experience</h2>
    <div class="section-content">
        {experience_html}
    </div>

    <!-- Management and Leadership Skills -->
    <h2>Management and Leadership Skills</h2>
    <div class="section-content">
        {leadership_html}
    </div>

    <!-- Projects -->
    <h2>Projects</h2>
    <div class="section-content">
        {projects_html}
    </div>

    <!-- Languages -->
    <h2>Languages</h2>
    <div class="section-content">
        <div class="onecolentry">
            {languages}
        </div>
    </div>

    <!-- Technologies/Skills -->
    <h2>Technologies/Skills</h2>
    <div class="section-content">
        <div class="onecolentry">
            {skills}
        </div>
    </div>

    <!-- Volunteering -->
    <h2>Volunteering</h2>
    <div class="section-content">
        <div class="onecolentry">
            {volunteering}
        </div>
    </div>

    <!-- Certificates and Certifications -->
    <h2>Certificates and Certifications</h2>
    <div class="section-content">
        {certifications_html}
    </div>

    <!-- Extra-Curricular & Interests -->
    <h2>Extra-Curricular & Interests</h2>
    <div class="section-content">
        <div class="onecolentry">
            {interests}
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        [Last updated: e.g., {last_updated}]
    </div>
    </div><!-- /.page -->
</body>
</html>
        """

@resume_bp.route('/edit/<int:resume_id>', methods=['GET', 'POST'])
@login_required
def edit_resume(resume_id):
    """Edit resume text"""
    if request.method == 'POST':
        updates = {
            'title': request.form.get('title'),
            'original_text': request.form.get('resume_text')
        }
        db.update_resume(resume_id, current_user.id, updates)
        flash('Resume updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    resume = db.get_resume_by_id(resume_id, current_user.id)
    if not resume:
        flash('Resume not found', 'error')
        return redirect(url_for('dashboard'))

    # Parse dates to prevent strftime errors in template
    if resume.get('created_at') and isinstance(resume.get('created_at'), str):
        try:
            resume['created_at'] = parse_date(resume['created_at'])
        except (ValueError, TypeError):
            resume['created_at'] = None
    if resume.get('updated_at') and isinstance(resume.get('updated_at'), str):
        try:
            resume['updated_at'] = parse_date(resume['updated_at'])
        except (ValueError, TypeError):
            resume['updated_at'] = None

    return render_template('editor.html', resume=resume)
