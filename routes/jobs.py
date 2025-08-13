from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db
from services.job_scraper import JobScraper
from services.keyword_extractor import KeywordExtractor

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/search', methods=['POST'])
@login_required
def search_related_jobs():
    """Search for related job postings"""
    data = request.get_json()
    job_title = data.get('job_title')
    location = data.get('location', '')
    
    if not job_title:
        return jsonify({'error': 'Job title is required'}), 400
    
    try:
        scraper = JobScraper()
        related_jobs = scraper.search_jobs(job_title, location)
        
        return jsonify({
            'success': True,
            'jobs': related_jobs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/save', methods=['POST'])
@login_required
def save_job_description():
    """Deprecated: job descriptions are now stored with resumes. Use tailoring flow."""
    return jsonify({'error': 'Deprecated: use resume tailoring to save job descriptions.'}), 410

@jobs_bp.route('/list')
@login_required
def list_jobs():
    """Redirect to new Supabase-backed jobs list under resume."""
    return redirect(url_for('resume.jobs_list'))

@jobs_bp.route('/view/<int:job_id>')
@login_required
def view_job(job_id):
    """Redirect to resume preview for the corresponding resume id (legacy)."""
    return redirect(url_for('resume.preview_resume', resume_id=job_id))

@jobs_bp.route('/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    """Deprecated: legacy job deletion not supported. Manage via resumes UI."""
    return jsonify({'error': 'Deprecated: manage jobs via resumes UI.'}), 410

@jobs_bp.route('/analyze/<int:job_id>')
@login_required
def analyze_job(job_id):
    """Deprecated legacy endpoint."""
    return jsonify({'error': 'Deprecated'}), 410
