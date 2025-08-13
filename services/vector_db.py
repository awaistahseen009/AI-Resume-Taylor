import os
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
import numpy as np
from typing import List, Dict, Any, Optional
import json

class PineconeVectorDB:
    """Pinecone vector database service for semantic search and embeddings"""
    
    def __init__(self):
        # Initialize Pinecone
        api_key = os.environ.get('PINECONE_API_KEY')
        environment = os.environ.get('PINECONE_ENVIRONMENT')
        index_name = os.environ.get('PINECONE_INDEX_NAME', 'resume-index')
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY must be set")
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Initialize Google AI embedding model
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY must be set for embeddings")
        
        genai.configure(api_key=google_api_key)
        self.embedding_model_name = os.environ.get('EMBEDDING_MODEL', 'models/embedding-001')
        self.vector_dimension = int(os.environ.get('VECTOR_DIMENSION', '768'))
        
        # Create or connect to index
        self.index_name = index_name
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if index_name not in existing_indexes:
            self.pc.create_index(
                name=index_name,
                dimension=self.vector_dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=environment or 'us-east-1'
                )
            )
        
        self.index = self.pc.Index(index_name)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Google AI"""
        try:
            result = genai.embed_content(
                model=self.embedding_model_name,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.vector_dimension
    
    def store_resume_embedding(self, resume_id: int, user_id: int, 
                              resume_text: str, metadata: Dict[str, Any] = None) -> bool:
        """Store resume embedding in Pinecone"""
        try:
            embedding = self.generate_embedding(resume_text)
            
            # Create unique ID for the resume
            vector_id = f"resume_{user_id}_{resume_id}"
            
            # Prepare metadata
            vector_metadata = {
                'type': 'resume',
                'resume_id': resume_id,
                'user_id': user_id,
                'text_preview': resume_text[:200],  # First 200 chars for preview
                **(metadata or {})
            }
            
            # Skip if text is empty or embedding is all zeros
            if not resume_text or not resume_text.strip():
                print("Skipping embedding upsert: resume_text is empty")
                return False
            if not any(abs(v) > 1e-12 for v in embedding):
                print(f"Skipping embedding upsert: embedding for {vector_id} is all zeros")
                return False

            # Upsert to Pinecone (dict format for v3 client)
            self.index.upsert(vectors=[{
                'id': vector_id,
                'values': embedding,
                'metadata': vector_metadata
            }])
            return True
            
        except Exception as e:
            import traceback
            print(f"Error storing resume embedding: {e}\n{traceback.format_exc()}")
            return False
    
    def store_job_embedding(self, job_id: int, user_id: int, 
                           job_text: str, metadata: Dict[str, Any] = None) -> bool:
        """Store job description embedding in Pinecone"""
        try:
            embedding = self.generate_embedding(job_text)
            
            # Create unique ID for the job
            vector_id = f"job_{user_id}_{job_id}"
            
            # Prepare metadata
            vector_metadata = {
                'type': 'job',
                'job_id': job_id,
                'user_id': user_id,
                'text_preview': job_text[:200],
                **(metadata or {})
            }
            
            # Skip if text is empty or embedding is all zeros
            if not job_text or not job_text.strip():
                print("Skipping job embedding upsert: job_text is empty")
                return False
            if not any(abs(v) > 1e-12 for v in embedding):
                print(f"Skipping job embedding upsert: embedding for {vector_id} is all zeros")
                return False

            # Upsert to Pinecone (dict format for v3 client)
            self.index.upsert(vectors=[{
                'id': vector_id,
                'values': embedding,
                'metadata': vector_metadata
            }])
            return True
            
        except Exception as e:
            import traceback
            print(f"Error storing job embedding: {e}\n{traceback.format_exc()}")
            return False
    
    def find_similar_resumes(self, query_text: str, user_id: int = None, 
                           top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar resumes based on query text"""
        try:
            query_embedding = self.generate_embedding(query_text)
            
            # Build filter for user-specific search
            filter_dict = {'type': 'resume'}
            if user_id:
                filter_dict['user_id'] = user_id
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            return [
                {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                }
                for match in results.matches
            ]
            
        except Exception as e:
            print(f"Error finding similar resumes: {e}")
            return []
    
    def find_similar_jobs(self, query_text: str, user_id: int = None, 
                         top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar job descriptions based on query text"""
        try:
            query_embedding = self.generate_embedding(query_text)
            
            # Build filter for user-specific search
            filter_dict = {'type': 'job'}
            if user_id:
                filter_dict['user_id'] = user_id
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            return [
                {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                }
                for match in results.matches
            ]
            
        except Exception as e:
            print(f"Error finding similar jobs: {e}")
            return []
    
    def find_matching_resumes_for_job(self, job_text: str, user_id: int, 
                                     top_k: int = 3) -> List[Dict[str, Any]]:
        """Find user's resumes that best match a job description"""
        try:
            job_embedding = self.generate_embedding(job_text)
            
            # Search only user's resumes
            results = self.index.query(
                vector=job_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={'type': 'resume', 'user_id': user_id}
            )
            
            return [
                {
                    'resume_id': match.metadata.get('resume_id'),
                    'similarity_score': match.score,
                    'text_preview': match.metadata.get('text_preview', ''),
                    'metadata': match.metadata
                }
                for match in results.matches
            ]
            
        except Exception as e:
            print(f"Error finding matching resumes: {e}")
            return []
    
    def delete_resume_embedding(self, resume_id: int, user_id: int) -> bool:
        """Delete resume embedding from Pinecone"""
        try:
            vector_id = f"resume_{user_id}_{resume_id}"
            self.index.delete(ids=[vector_id])
            return True
        except Exception as e:
            print(f"Error deleting resume embedding: {e}")
            return False
    
    def delete_job_embedding(self, job_id: int, user_id: int) -> bool:
        """Delete job embedding from Pinecone"""
        try:
            vector_id = f"job_{user_id}_{job_id}"
            self.index.delete(ids=[vector_id])
            return True
        except Exception as e:
            print(f"Error deleting job embedding: {e}")
            return False
    
    def get_user_embeddings_stats(self, user_id: int) -> Dict[str, int]:
        """Get statistics about user's embeddings"""
        try:
            # Query for user's resumes
            resume_results = self.index.query(
                vector=[0] * self.vector_dimension,  # Dummy vector
                top_k=1000,  # Large number to get all
                include_metadata=True,
                filter={'type': 'resume', 'user_id': user_id}
            )
            
            # Query for user's jobs
            job_results = self.index.query(
                vector=[0] * self.vector_dimension,  # Dummy vector
                top_k=1000,  # Large number to get all
                include_metadata=True,
                filter={'type': 'job', 'user_id': user_id}
            )
            
            return {
                'resumes': len(resume_results.matches),
                'jobs': len(job_results.matches)
            }
            
        except Exception as e:
            print(f"Error getting user embeddings stats: {e}")
            return {'resumes': 0, 'jobs': 0}
    
    def semantic_search(self, query: str, search_type: str = 'all', 
                       user_id: int = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search across resumes and/or jobs"""
        try:
            query_embedding = self.generate_embedding(query)
            
            # Build filter
            filter_dict = {}
            if search_type == 'resume':
                filter_dict['type'] = 'resume'
            elif search_type == 'job':
                filter_dict['type'] = 'job'
            # If search_type == 'all', no type filter
            
            if user_id:
                filter_dict['user_id'] = user_id
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            
            return [
                {
                    'id': match.id,
                    'type': match.metadata.get('type'),
                    'score': match.score,
                    'preview': match.metadata.get('text_preview', ''),
                    'metadata': match.metadata
                }
                for match in results.matches
            ]
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

# Initialize vector database instance
vector_db = PineconeVectorDB()
