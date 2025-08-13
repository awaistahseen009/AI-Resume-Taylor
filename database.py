import os
from supabase import create_client, Client
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

class SupabaseDB:
    """Supabase database client for Resume Tailor"""
    
    def __init__(self):
        url = os.environ.get('SUPABASE_URL')
        # Use service role key for database operations to bypass RLS
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client: Client = create_client(url, key)
        # Ensure all queries target the public schema explicitly
        try:
            self.client.postgrest.schema('public')
        except Exception:
            # Older clients may not expose schema(), safe to ignore
            pass
    
    # User operations
    def create_user(self, username: str, email: str, password_hash: str, 
                   first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Create a new user"""
        user_data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'first_name': first_name,
            'last_name': last_name,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.client.table('users').insert(user_data).execute()
        return result.data[0] if result.data else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        result = self.client.table('users').select('*').eq('email', email).execute()
        return result.data[0] if result.data else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        result = self.client.table('users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        updates['updated_at'] = datetime.utcnow().isoformat()
        result = self.client.table('users').update(updates).eq('id', user_id).execute()
        return result.data[0] if result.data else None
    
    # Resume operations
    def create_resume(self, user_id: int, title: str, original_text: str,
                     file_path: str = None, file_type: str = None) -> Dict[str, Any]:
        """Create a new resume"""
        resume_data = {
            'user_id': user_id,
            'title': title,
            'original_text': original_text,
            'file_path': file_path,
            'file_type': file_type,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_tailored': False
        }
        
        result = self.client.table('resumes').insert(resume_data).execute()

        if hasattr(result, 'error') and result.error:
            logging.error(f"Error creating resume in Supabase: {result.error}")
            return None

        return result.data[0] if result.data else None
    
    def get_user_resumes(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all resumes for a user"""
        result = self.client.table('resumes').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def get_resume_by_id(self, resume_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get resume by ID for specific user"""
        result = self.client.table('resumes').select('*').eq('id', resume_id).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def update_resume(self, resume_id: int, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update resume"""
        updates['updated_at'] = datetime.utcnow().isoformat()
        result = self.client.table('resumes').update(updates).eq('id', resume_id).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def delete_resume(self, resume_id: int, user_id: int) -> bool:
        """Delete resume"""
        result = self.client.table('resumes').delete().eq('id', resume_id).eq('user_id', user_id).execute()
        return len(result.data) > 0
    
    # Job description operations
    def create_job_description(self, user_id: int, title: str, company: str,
                              description_text: str, requirements: str = None,
                              keywords: List[str] = None, job_url: str = None,
                              location: str = None, salary_range: str = None) -> Dict[str, Any]:
        """Create a new job description"""
        job_data = {
            'user_id': user_id,
            'title': title,
            'company': company,
            'description_text': description_text,
            'requirements': requirements,
            'keywords': json.dumps(keywords) if keywords else None,
            'job_url': job_url,
            'location': location,
            'salary_range': salary_range,
            'created_at': datetime.utcnow().isoformat(),
            'is_target_job': True
        }
        
        result = self.client.table('job_descriptions').insert(job_data).execute()
        return result.data[0] if result.data else None
    
    def get_user_jobs(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all job descriptions for a user"""
        result = self.client.table('job_descriptions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data if result.data else []
    
    def get_job_by_id(self, job_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get job description by ID for specific user"""
        result = self.client.table('job_descriptions').select('*').eq('id', job_id).eq('user_id', user_id).execute()
        return result.data[0] if result.data else None
    
    def delete_job(self, job_id: int, user_id: int) -> bool:
        """Delete job description"""
        result = self.client.table('job_descriptions').delete().eq('id', job_id).eq('user_id', user_id).execute()
        return len(result.data) > 0
    
    # Related jobs operations
    def create_related_job(self, parent_job_id: int, title: str, company: str,
                          description_snippet: str, job_url: str = None,
                          location: str = None, similarity_score: float = None,
                          source: str = None) -> Dict[str, Any]:
        """Create a related job posting"""
        related_job_data = {
            'parent_job_id': parent_job_id,
            'title': title,
            'company': company,
            'description_snippet': description_snippet,
            'job_url': job_url,
            'location': location,
            'similarity_score': similarity_score,
            'source': source,
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = self.client.table('related_jobs').insert(related_job_data).execute()
        return result.data[0] if result.data else None
    
    def get_related_jobs(self, parent_job_id: int) -> List[Dict[str, Any]]:
        """Get related jobs for a parent job"""
        result = self.client.table('related_jobs').select('*').eq('parent_job_id', parent_job_id).execute()
        return result.data if result.data else []

# User class for Flask-Login compatibility
class User:
    """User class compatible with Flask-Login"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.first_name = user_data.get('first_name')
        self.last_name = user_data.get('last_name')
        self.created_at = user_data.get('created_at')
        self.updated_at = user_data.get('updated_at')
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash"""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @staticmethod
    def set_password(password: str) -> str:
        """Hash password"""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Initialize database instance
db = SupabaseDB()