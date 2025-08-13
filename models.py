from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile management"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', backref='user', lazy=True, cascade='all, delete-orphan')
    job_descriptions = db.relationship('JobDescription', backref='user', lazy=True, cascade='all, delete-orphan')
    outreach_messages = db.relationship('OutreachMessage', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Resume(db.Model):
    """Resume model for storing original and tailored resumes"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    tailored_text = db.Column(db.Text, nullable=True)
    latex_source = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_type = db.Column(db.String(10), nullable=True)  # pdf, docx, txt
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_tailored = db.Column(db.Boolean, default=False)
    
    # Relationship to job description used for tailoring
    job_description_id = db.Column(db.Integer, db.ForeignKey('job_description.id'), nullable=True)
    
    def __repr__(self):
        return f'<Resume {self.title}>'

class JobDescription(db.Model):
    """Job description model for storing target jobs and related postings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    description_text = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    keywords = db.Column(db.Text, nullable=True)  # JSON string of extracted keywords
    job_url = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    salary_range = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_target_job = db.Column(db.Boolean, default=True)  # True for main job, False for related jobs
    
    # Relationships
    resumes = db.relationship('Resume', backref='job_description', lazy=True)
    outreach_messages = db.relationship('OutreachMessage', backref='job_description', lazy=True)
    
    def __repr__(self):
        return f'<JobDescription {self.title} at {self.company}>'

class OutreachMessage(db.Model):
    """Outreach message model for storing generated hiring manager messages"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_description_id = db.Column(db.Integer, db.ForeignKey('job_description.id'), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # email, linkedin, pitch
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(50), nullable=True)  # formal, casual, enthusiastic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OutreachMessage {self.message_type} for {self.job_description.title}>'

class RelatedJob(db.Model):
    """Related job postings fetched from external APIs"""
    id = db.Column(db.Integer, primary_key=True)
    parent_job_id = db.Column(db.Integer, db.ForeignKey('job_description.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    description_snippet = db.Column(db.Text, nullable=True)
    job_url = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    similarity_score = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), nullable=True)  # indeed, linkedin, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RelatedJob {self.title} at {self.company}>'
