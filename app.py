import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import tempfile
import subprocess
from datetime import datetime
from dateutil.parser import parse as parse_date

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import database and vector database
from database import db, User
from services.vector_db import vector_db

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(int(user_id))
    return User(user_data) if user_data else None

# Import and register blueprints
from routes.auth import auth_bp
from routes.resume import resume_bp
from routes.jobs import jobs_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(resume_bp, url_prefix='/resume')
app.register_blueprint(jobs_bp, url_prefix='/jobs')

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for logged-in users"""
    user_resumes = db.get_user_resumes(current_user.id)
    if user_resumes:
        for resume in user_resumes:
            if resume.get('created_at') and isinstance(resume.get('created_at'), str):
                try:
                    resume['created_at'] = parse_date(resume['created_at'])
                except (ValueError, TypeError):
                    # If parsing fails, set to None to avoid template errors
                    resume['created_at'] = None
            if resume.get('updated_at') and isinstance(resume.get('updated_at'), str):
                try:
                    resume['updated_at'] = parse_date(resume['updated_at'])
                except (ValueError, TypeError):
                    resume['updated_at'] = None
    return render_template('dashboard.html', resumes=user_resumes)

@app.route('/editor')
@login_required
def editor():
    """Resume editor view with side-by-side comparison"""
    resume_id = request.args.get('resume_id')
    if resume_id:
        resume = db.get_resume_by_id(int(resume_id), current_user.id)
        if resume:
            return render_template('editor.html', resume=resume)
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    """User profile and settings"""
    # Safely format 'Member Since' without relying on Jinja strftime
    member_since = 'N/A'
    try:
        created = getattr(current_user, 'created_at', None)
        if created:
            from datetime import datetime
            from dateutil import parser as dateparser
            if isinstance(created, str):
                dt = dateparser.parse(created)
            elif isinstance(created, datetime):
                dt = created
            else:
                dt = None
            if dt:
                member_since = dt.strftime('%B %Y')
    except Exception:
        member_since = 'N/A'
    return render_template('profile.html', member_since=member_since)

@app.route('/api/search')
@login_required
def semantic_search():
    """Semantic search API endpoint"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # 'resume', 'job', or 'all'
    
    if not query:
        return jsonify({'results': []})
    
    try:
        results = vector_db.semantic_search(
            query=query,
            search_type=search_type,
            user_id=current_user.id,
            top_k=10
        )
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile/stats')
@login_required
def profile_stats():
    """Get user profile statistics"""
    try:
        # Get resume statistics
        user_resumes = db.get_user_resumes(current_user.id)
        total_resumes = len(user_resumes)
        tailored_resumes = len([r for r in user_resumes if r.get('is_tailored', False)])
        
        # Get job statistics
        user_jobs = db.get_user_jobs(current_user.id)
        total_jobs = len(user_jobs)
        
        # Get vector database statistics
        vector_stats = vector_db.get_user_embeddings_stats(current_user.id)
        total_embeddings = vector_stats.get('resumes', 0) + vector_stats.get('jobs', 0)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_resumes': total_resumes,
                'tailored_resumes': tailored_resumes,
                'total_jobs': total_jobs,
                'total_embeddings': total_embeddings
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
